# YouTube comments scraper

Export YouTube comments and replies from Python or curl, without a YouTube Data API key or its daily quota.
The script in this repo turns them into something a creator can act on, a checklist of viewer questions nobody answered yet.

It runs on my [YouTube Video & Shorts Comments Scraper with Replies](https://apify.com/heyitsgautham/youtube-comments-scraper) on Apify.
I built it, and it's paid per result, $0.25 per 1,000 comments, with replies counted as comments.
Videos with comments turned off, deleted videos and failed fetches cost nothing.

## Unanswered viewer questions

`unanswered_questions.py` reads the comments and replies on a channel's newest videos.
It keeps the top-level comments that ask something, either with a `?` or by starting with a word like "how" or "can".
Then it drops every thread where the channel itself replied, using the scraper's `authorIsChannelOwner` flag, and writes the rest to `questions.md`, most liked first.

```bash
pip install -r requirements.txt
export APIFY_TOKEN=your_token_here
python unanswered_questions.py https://www.youtube.com/@ArjanCodes --videos 2 --comments 100
```

I ran it on 26 Oct 2026 on the two newest videos of ArjanCodes, a Python channel I watch.

```
Reading up to 100 comments on each of 2 videos, at most $0.050
58 top-level comments read, the channel replied in 3 threads. 9 questions, 0 answered by the channel, 9 open.
    8 open on 7 Python Features That Make Your Code Worse
    1 open on The Visitor Pattern in Python (And Better Alternatives)
Checklist written to questions.md
```

The top of `questions.md`:

```markdown
## 7 Python Features That Make Your Code Worse

- [ ] 0 likes, 0 replies, 5 days ago: Where/what is this "domain" package of which you speak? Could not find in Python documentation (but I am a horrible coder) ([open](https://www.youtube.com/watch?v=RHCyTWaRZSk&lc=Ugx_tapK-RBhyAGinrV4AaABAg))
- [ ] 0 likes, 0 replies, 7 days ago: 14:48 there any “use slots” similar parameter under pydantic ? ([open](https://www.youtube.com/watch?v=RHCyTWaRZSk&lc=Ugy0JLLR-I-ZBvCEOzB4AaABAg))
```

Each `open` link jumps straight to that comment on the video.
The checklist leaves out commenters' names, since you only need the link to reply.

A few things I'd tune for a big channel.
Raise `--comments` to read deeper, because the script reads newest first and stops at that many rows per video, replies included.
The question test is a regular expression at the top of the file, so add words for your language.
The run's charge is capped at `--comments` times the number of videos times $0.00025.

You can also pass videos one by one with `--video URL`, repeated.

## A reply row

Every comment and reply is one row.
This is one of the channel's own replies from the run above, with the commenter fields removed.

```json
{
  "videoId": "45MgUX_ih0s",
  "videoTitle": "The Visitor Pattern in Python (And Better Alternatives)",
  "videoViewCount": 22820,
  "videoCommentCount": 33,
  "commentId": "UgxLiwKEUgPlXREjylp4AaABAg.AcKMzpKpTNFAcLJvmOEtER",
  "text": "Of course 😅",
  "authorIsVerified": true,
  "authorIsChannelOwner": true,
  "likeCount": 1,
  "replyCount": 0,
  "publishedTimeText": "1 day ago",
  "publishedAtApprox": "2026-10-24T20:06:31Z",
  "isEdited": false,
  "isReply": true,
  "parentId": "UgxLiwKEUgPlXREjylp4AaABAg",
  "isPinned": false,
  "isHearted": false,
  "commentUrl": "https://www.youtube.com/watch?v=45MgUX_ih0s&lc=UgxLiwKEUgPlXREjylp4AaABAg.AcKMzpKpTNFAcLJvmOEtER"
}
```

Rows also carry `authorName` and `authorChannelId`, the commenter's public handle and channel ID.
Rows from a channel, playlist or search start with `input`, `sourceType`, `sourceId`, `sourceTitle` and `position`.

## curl

The top 3 comments on "Me at the zoo":

```bash
curl -X POST "https://api.apify.com/v2/acts/heyitsgautham~youtube-comments-scraper/run-sync-get-dataset-items?fields=videoId,text,likeCount,replyCount,publishedTimeText,isPinned" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"videos": ["https://www.youtube.com/watch?v=jNQXAC9IVRw"], "maxComments": 3, "sort": "top"}'
```

```json
[{
  "videoId": "jNQXAC9IVRw",
  "text": "We're so honored that the first ever YouTube video was filmed here!",
  "likeCount": 4800000,
  "replyCount": 986,
  "publishedTimeText": "6 years ago",
  "isPinned": true
},
{
  "videoId": "jNQXAC9IVRw",
  "text": "Hello",
  "likeCount": 309000,
  "replyCount": 997,
  "publishedTimeText": "6 months ago",
  "isPinned": false
},
{
  "videoId": "jNQXAC9IVRw",
  "text": "This guys is the only person who has the rights to say \"first\" on youtube.",
  "likeCount": 419000,
  "replyCount": 851,
  "publishedTimeText": "5 years ago",
  "isPinned": false
}]
```

`likeCount` is rounded the way YouTube shows it, so 4.8M comes back as `4800000`.

## Python

```python
import os
from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("heyitsgautham/youtube-comments-scraper").call(run_input={
    "videos": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/shorts/4z8Hi_uQOkE"],
    "maxComments": 50,
    "sort": "top",
    "includeReplies": True,
    "maxRepliesPerComment": 10,
})
for c in client.dataset(run.default_dataset_id).iterate_items():
    if "commentId" in c:
        print("  " * c["isReply"] + c["text"][:80])
```

## Inputs

| Input | Default | What it does |
|---|---|---|
| `videos` | | Watch, youtu.be, Shorts, embed and live links, or bare IDs |
| `channelsAndPlaylists` | empty | Channels or playlists, each giving its latest videos |
| `searchQueries` | empty | YouTube searches, each giving its top videos |
| `maxVideosPerSource` | 10 | Videos per channel, playlist or search |
| `maxComments` | 100 | Rows per video, replies included. `0` means every comment |
| `sort` | `top` | `top` or `newest` |
| `includeReplies`, `maxRepliesPerComment` | off, 10 | Replies after each parent, with a cap per thread. `0` means all |
| `includeVideoInfo` | off | Adds the video's title, view count and comment count to each row, free |
| `onlyNewSinceLastRun`, `publishedAfter` | off | For a scheduled feed of new comments |

## Price

| Apify tier | Per 1,000 comments or replies |
|---|---|
| No discount | $0.25 |
| Bronze | $0.225 |
| Silver | $0.20 |
| Gold | $0.175 |

No start fee.
In the final test on 80 videos, all 68 that had comments returned them, 4,366 rows in 4.5 minutes.

## Limits

- Like counts of 1,000 and up are rounded by YouTube.
- `replyCount` can be a bit higher than the replies you get, because YouTube counts held and deleted replies.
- `publishedAtApprox` comes from YouTube's "2 days ago" text, so it can be up to a day early.
- Rows from several videos can interleave in the dataset, so group by `videoId`.
- Mixes (`list=RD...`) can't be listed.

## License

MIT for the code in this repo.
