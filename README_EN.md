# wechat-article-media-download

[中文](README.md) | English

Download **all videos and images** embedded in a WeChat Official Account article, or extract audio/transcripts from **WeChat Channels short links (`weixin.qq.com/sph/...`)** — no WeChat client, no login, no tokens required.

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## How It Works

### 1. WeChat Official Account Articles (`mp.weixin.qq.com/s/...`)
At the end of a WeChat article page (`mp.weixin.qq.com/s/...`), the HTML source contains an inline JS data block that **already includes signed direct URLs for each video in 4 quality levels** (`mpvideo.qpic.cn`, with `dis_k` / `auth_key` signature parameters). This tool extracts those URLs straight from the source and downloads them:

- **Images**: public `mmbiz.qpic.cn` URLs found in `data-src` attributes — permanently valid
- **Videos**: signed direct URLs from the inline JS data block — **valid for ~7 days** after the page is fetched; downloaded in parallel
- Each video automatically selects the best quality (prefers `f10002` — 1080p H.264, best compatibility)

No WeChat API is called — the `videoplayer` API family now requires an authenticated session and returns nothing useful to anonymous callers, so that path is a dead end.

### 2. WeChat Channels Short Links (`weixin.qq.com/sph/...`)
Outside the WeChat client, `weixin.qq.com/sph/<shortUri>` redirects to `channels.weixin.qq.com/finder-preview/pages/sph?id=<shortUri>` and only displays a QR code without exposing `h264Url`/`h265Url` (and raw `curl` calls to `get_feed_info` fail with `permission verification failed` due to missing frontend request signatures). Following **Scenario B** in `SKILL.md`, the agent:

1. **Extracts signed metadata in-page via CDP**: Calls the page's `merlin.*.js` `getFeedInfo` client (or reads the rendered DOM) to retrieve `authorInfo.nickname`, `feedInfo.description`, `createtime`, and `coverUrl` without login.
2. **Resolves cross-platform identical sources**: Uses the exact author name and description to locate the creator's identical upload on Bilibili / Douyin.
3. **Downloads the audio stream via parallel `Range` requests**: Prevents mid-stream CDN truncation on long videos and verifies full duration via `ffprobe`.
4. **Transcribes locally on Apple Silicon GPU (`mlx_whisper`)**: Splits audio into 300s chunks with domain proper nouns injected into `initial_prompt` to produce a complete timestamped transcript.

## Installation

### Option 1: Install as an AI-agent skill (recommended)

This repo follows the standard [Agent Skill](SKILL.md) format (`SKILL.md` with frontmatter). **Just send this GitHub repo link to any skill-capable agent** (WorkBuddy, Claude Code, etc.) and say "install this skill into your skills directory" — the agent will fetch and set it up automatically.

Manual installation — clone the repo (or just copy `SKILL.md`) into the right directory:

```bash
# WorkBuddy
git clone https://github.com/xccElephant/wechat-article-media-download.git ~/.workbuddy/skills/wechat-article-media-download

# Claude Code
git clone https://github.com/xccElephant/wechat-article-media-download.git ~/.claude/skills/wechat-article-media-download
```

Once installed, send the agent an `mp.weixin.qq.com/s/...` link and ask it to download the videos/images — it will follow the SKILL.md workflow.

### Option 2: Run the script directly

`scripts/download.py` is a single-file, zero-dependency script (pure Python 3.7+ stdlib). Clone or download it, then run:

```bash
git clone https://github.com/xccElephant/wechat-article-media-download.git
cd wechat-article-media-download
python3 scripts/download.py "https://mp.weixin.qq.com/s/ICb4P_FqTZVgaeMvZs_9dg" ./output
```

On Windows (PowerShell), use `python` instead of `python3`.

Output structure:

```
output/
├── videos/          # video_01.mp4 ... numbered in article order
├── images/          # image_01.png ... format (png/jpeg/gif) auto-detected
└── sources.json     # all original URLs (for traceability / re-download)
```

## Requirements & Limitations

| Requirement | Notes |
|------|------|
| Publicly accessible article | No login needed; any browser must be able to open it |
| Signature validity | Video direct URLs expire ~1 week after the page is fetched — just re-run to refresh |
| `Referer` header | Already sent by the script automatically |

**Not supported:**

1. Deleted / paid / followers-only articles → the data block is not in the page
2. Videos from **Channels (视频号)** rather than the article itself → no mpvideo URLs in the source; packet sniffing required
3. Audio clips (voice) → not yet supported; audio uses a different endpoint (`res.wx.qq.com/voice/getvoice?mediaid=`)

## Known Pitfalls (for contributors)

- Direct URLs are escaped in the source as `\x26amp;` — **you must restore them to `&` before regex extraction**, otherwise the URL is truncated at the first `&` and you get 0-byte files
- When grouping, strip the `.f\d+` suffix from the base path (e.g. `xxx.f10002.mp4`), otherwise each quality variant is treated as a separate video (9 videos become 36 groups)
- The player iframe has an empty `src` in desktop browsers, and the player template page requires the WeChat JSBridge — browser automation does **not** work here; don't waste time on it

## Project Structure

```
├── scripts/download.py   # standalone runnable script (zero dependencies)
├── SKILL.md              # AI-agent skill file (WorkBuddy / Claude Code format)
├── README.md             # 中文说明
└── README_EN.md          # this file
```

## Disclaimer

For personal study and archival use only. Please respect the original authors' copyright; do not use for commercial purposes or redistribution.

## License

[MIT](LICENSE)
