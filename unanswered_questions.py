"""Find the viewer questions you never answered on your latest YouTube videos.

It reads the comments and replies on a channel's newest videos, keeps top-level
comments that ask something, drops the ones the channel already replied to,
and writes a Markdown checklist, most liked first, with a link to each comment.

Usage:
    export APIFY_TOKEN=...
    python unanswered_questions.py https://www.youtube.com/@yourchannel --videos 5
    python unanswered_questions.py @yourchannel --videos 3 --comments 300 --out questions.md

Pass single videos instead of a channel with --video (repeatable).
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

from apify_client import ApifyClient

ACTOR = "heyitsgautham/youtube-comments-scraper"
PRICE_PER_COMMENT = Decimal("0.00025")
QUESTION = re.compile(r"\?|^(how|what|why|when|where|which|who|can|could|does|do|is|are|will|would|should)\b", re.I)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("channel", nargs="?", help="channel URL or @handle")
    parser.add_argument("--video", action="append", default=[], help="a video URL or ID, instead of a channel")
    parser.add_argument("--videos", type=int, default=5, help="newest videos to read from the channel (default 5)")
    parser.add_argument("--comments", type=int, default=200, help="rows per video, replies included (default 200)")
    parser.add_argument("--out", default="questions.md")
    args = parser.parse_args()

    if not (args.channel or args.video):
        parser.error("give a channel, or one or more --video")
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first. Get one at https://console.apify.com/settings/integrations")

    run_input = {
        "videos": args.video,
        "channelsAndPlaylists": [args.channel] if args.channel else [],
        "maxVideosPerSource": args.videos,
        "maxComments": args.comments,
        "sort": "newest",
        "includeReplies": True,
        "maxRepliesPerComment": 0,
        "includeVideoInfo": True,
    }
    n_videos = len(args.video) + (args.videos if args.channel else 0)
    cap = PRICE_PER_COMMENT * args.comments * n_videos
    print(f"Reading up to {args.comments} comments on each of {n_videos} videos, at most ${cap:.3f}")

    client = ApifyClient(token)
    run = client.actor(ACTOR).call(run_input=run_input, max_total_charge_usd=cap, logger=None)
    if run is None or run.status != "SUCCEEDED":
        sys.exit(f"Run did not succeed: {run.status if run else 'no run'}")

    comments, owner_replied, titles = [], set(), {}
    for row in client.dataset(run.default_dataset_id).iterate_items():
        if "commentId" not in row:
            print(f"  skipped {row.get('videoId') or row.get('input')}: {row.get('status')}, {row.get('message')}")
            continue
        titles[row["videoId"]] = row.get("videoTitle") or row["videoId"]
        if row["isReply"] and row["authorIsChannelOwner"]:
            owner_replied.add(row["parentId"])
        elif not row["isReply"] and not row["authorIsChannelOwner"]:
            comments.append(row)

    questions = [c for c in comments if QUESTION.search(c["text"].strip())]
    open_q = [q for q in questions if q["commentId"] not in owner_replied]
    by_video = defaultdict(list)
    for q in sorted(open_q, key=lambda q: q["likeCount"], reverse=True):
        by_video[q["videoId"]].append(q)

    lines = [f"# Unanswered viewer questions\n",
             f"{len(comments)} top-level comments read, the channel replied in {len(owner_replied)} threads. "
             f"{len(questions)} questions, {len(questions) - len(open_q)} answered by the channel, {len(open_q)} open.\n"]
    for vid, qs in by_video.items():
        lines.append(f"\n## {titles[vid]}\n")
        for q in qs:
            text = " ".join(q["text"].split())
            text = text if len(text) <= 200 else text[:197] + "..."
            lines.append(f"- [ ] {q['likeCount']} likes, {q['replyCount']} replies, {q['publishedTimeText']}: "
                         f"{text} ([open]({q['commentUrl']}))")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(lines[1].strip())
    for vid, qs in by_video.items():
        print(f"  {len(qs):3} open on {titles[vid][:70]}")
    print(f"Checklist written to {args.out}")


if __name__ == "__main__":
    main()
