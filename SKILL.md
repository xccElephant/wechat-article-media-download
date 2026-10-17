---
name: wechat-article-media-download
description: Download videos, images, and transcripts from WeChat links, including Official Account articles (mp.weixin.qq.com/s/...) and WeChat Channels short links (weixin.qq.com/sph/... or channels.weixin.qq.com). Trigger when the user gives a WeChat article or WeChat Channels (视频号) link and asks to 下载/保存/提取 视频/图片/素材/访谈记录/逐字稿/字幕.
description_zh: 下载微信公众号文章内的视频图片，或提取微信视频号链接的音视频与文字实录
description_en: Download videos, images, and transcripts from WeChat articles and WeChat Channels links
disable: false
agent_created: true
---

# wechat-article-media-download

## When to use
- **Scenario A (公众号图文)**：User provides a `https://mp.weixin.qq.com/s/...` link and wants the article's videos and/or images downloaded locally.
- **Scenario B (微信视频号短链)**：User provides a `https://weixin.qq.com/sph/...` or `https://channels.weixin.qq.com/finder-preview/pages/sph?id=...` link and wants the video downloaded or its speech/interview transcript (访谈记录/逐字稿) extracted.

---

## Scenario A: 微信公众号文章 (`mp.weixin.qq.com/s/...`)

### Steps

1. Fetch the article HTML (must use a browser-like UA; plain curl works):
   ```bash
   curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0" "<article_url>" -o article.html
   ```
2. Extract images: regex `data-src="(https://mmbiz\.qpic\.cn/[^"]+)"`, dedupe preserving order, extension from `wx_fmt=` param. Download with `-H "Referer: https://mp.weixin.qq.com/"` (required for some CDNs).
3. Extract videos (vidtype=2 / wxv_ iframes):
   - First unescape the HTML: `html.unescape`, then replace `\\x26amp;` → `&`, `\\x26` → `&` (video URLs are JS-escaped; missing this truncates every URL).
   - The raw HTML **already contains signed direct URLs** on `mpvideo.qpic.cn` (inside inline `format_id:` / `url:` JS data blocks near the end of the page). Extract with:
     ```python
     re.findall(r"format_id:\s*'(\d+)'\s*\*[^}]*?url:\s*'(http://mpvideo\.qpic\.cn/[^']+)'", txt, re.S)
     ```
   - Group by base path: `re.match(r'(http://mpvideo\.qpic\.cn/[a-z0-9]+)\.f\d+\.mp4', url)` — each article video appears as ~4 formats. Pick `10002` first (超清 H.264), fallback `10102`, `10004`, `10104`.
   - Expect groups = number of videos; order of appearance matches article order.
   - Download: `curl -sL -A "Mozilla/5.0" -H "Referer: https://mp.weixin.qq.com/" -o video_NN.mp4 "<url>"`.
4. Verify every file: `file *.mp4` must say `ISO Media, MP4`; sizes should be > 100 KB.

### Pitfalls (Scenario A)
- Do NOT bother with `mp/videoplayer?action=get_video_info` or `get_mp_video_play_url` APIs — they now return `no session` / omit `url_info` anonymously. The signed CDN URLs in the article HTML are the reliable path.
- `dis_t` in URLs is an expiry timestamp (usually ~1 week after page fetch) — download promptly after fetching the HTML.
- The video iframes have empty `src` in desktop browsers and the player template requires WeixinJSBridge — browser automation does NOT help; skip it.
- URL regex must exclude backslash-safe: extract only AFTER replacing `\\x26amp;`/`\\x26`, otherwise every URL is truncated at its first `&` (returns empty 0-byte files).
- Regex group bug to avoid: base path grouping must strip `.f\d+` (e.g. `xxx.f10002.mp4`), otherwise each format becomes its own "video" (36 groups instead of 9).

### Verification (Scenario A)
- Count of video groups should equal the count of `vid=wxv_*` iframes in the HTML.
- Every downloaded MP4 passes `file` check as ISO Media; every image has nonzero size and matches its declared format.

---

## Scenario B: 微信视频号短链 (`weixin.qq.com/sph/...`) 提取视频与转写实录

### Platform Mechanics & Constraints
- `https://weixin.qq.com/sph/<shortUri>` 301-redirects to `https://channels.weixin.qq.com/finder-preview/pages/sph?id=<shortUri>`.
- Outside the WeChat built-in client (no `WeixinJSBridge` / `generalToken`), the page only renders a QR code ("可扫码前往微信观看此内容") and `get_feed_info` with `exportId` returns `errMsg.type = 2` ("此内容暂时无法播放") without `h264Url`/`h265Url`.
- Calling `POST https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info` via raw `curl` fails with `{"errCode": -1, "errMsg": "permission verification failed"}` because the frontend `merlin.*.js` bundle attaches a request signature transformer.
- **However**, opening the `/sph?id=<shortUri>` page in a real browser (via `web-access` CDP) allows extracting the full metadata (`authorInfo.nickname`, `feedInfo.description`, `feedInfo.createtime`, `feedInfo.coverUrl`).

### Steps

1. **Extract WeChat Channels Metadata in Browser (CDP)**:
   - Open `https://weixin.qq.com/sph/<shortUri>` via `web-access` proxy (`http://localhost:3456/new?url=...`).
   - Run `/eval` on the tab to read `document.body.innerText` or invoke the signed `merlin` client directly:
     ```javascript
     (async () => {
       const merlinUrl = Array.from(document.querySelectorAll('link[rel="modulepreload"]'))
         .map(l => l.href)
         .find(h => h.includes('/merlin.'));
       const mod = await import(merlinUrl);
       const shortUri = new URLSearchParams(location.search).get('id');
       const res = await mod.f.getFeedInfo({ baseReq: { generalToken: '' }, shortUri });
       return JSON.stringify(res.data, null, 2);
     })()
     ```
   - This returns `authorInfo.nickname` (作者昵称), `feedInfo.description` (完整视频文案与话题标签), `feedInfo.createtime` (发布时间戳), and `feedInfo.coverUrl` (封面图 URL).

2. **Cross-Platform Source Resolution (Bilibili / Douyin)**:
   - Medium/long-form WeChat Channels creators almost always multi-publish the exact same video to **Bilibili** or **Douyin (`jingxuan.douyin.com`)**.
   - Search using `authorInfo.nickname` + exact phrases from `feedInfo.description` to locate the matching Bilibili `bvid` (verify that the description, publish date, and cover image match).
   - Check `https://api.bilibili.com/x/web-interface/view?bvid=<BVID>` for `cid`, `duration`, and `subtitle.list`. If `subtitle.list` is non-empty, fetch the subtitle JSON directly and finish.

3. **Multi-Threaded `Range` Audio Stream Download (When No Subtitles Exist)**:
   - Query `https://api.bilibili.com/x/player/playurl?bvid=<BVID>&cid=<CID>&fnval=16` (with `Referer: https://www.bilibili.com/video/<BVID>/`).
   - Pick `data.dash.audio[0].baseUrl` (66 kbps `.m4s` audio stream — ~23 MB for a 47-min video, avoiding downloading hundreds of MBs of video).
   - **Download using parallel `Range` requests** (`Range: bytes=0-0` to get total size from `Content-Range`, then 2 MB chunks with `ThreadPoolExecutor`):
     ```python
     # Always verify final file size == Content-Range total and check ffprobe duration!
     ```
   - Verify with `ffprobe -v error -show_entries format=duration,size <audio.m4a>` that `duration` matches `data.duration` from the view API.

4. **Chunked Local GPU Transcription (`mlx_whisper`)**:
   - Split the verified audio into 300-second mono 16 kHz MP3 segments:
     ```bash
     ffmpeg -y -i /tmp/audio_full.m4a -f segment -segment_time 300 -c:a libmp3lame -b:a 32k -ar 16000 -ac 1 /tmp/chunks/chunk_%02d.mp3
     ```
   - Transcribe each chunk using `mlx_whisper` on Apple Silicon GPU (~10 seconds per 5-minute chunk):
     ```python
     res = mlx_whisper.transcribe(
         chunk_path,
         path_or_hf_repo="mlx-community/whisper-small-mlx",
         language="zh",
         condition_on_previous_text=False,
         initial_prompt="以下是...的深度访谈对话，涉及<从简介提取的人名与专有名词>，请使用简体中文。"
     )
     ```
   - Add `idx * 300.0` to each segment's `start`/`end` timestamps and assemble the full transcript.

### Pitfalls (Scenario B)
- **Single-connection CDN truncation**: Do NOT download long `.m4s` streams from `bilivideo.com` in a single sequential `urlopen` read — the CDN frequently drops the connection mid-stream (e.g., at ~8.8 MB / 18 mins of a 47-min file) without raising an HTTP error, resulting in an incomplete transcript. Always verify `ffprobe` duration against video metadata and use `Range` chunked downloads.
- **Whisper repetition loops on long audio**: Always pass `condition_on_previous_text=False` and segment the audio into 300s chunks; otherwise a single noisy phrase can cause Whisper to get stuck repeating or skipping lines.
- **Homophone errors on domain terms**: Pass key proper nouns extracted from `feedInfo.description` into `initial_prompt` (e.g., speaker names, company/project names) and perform a post-processing pass on the raw transcript to fix remaining phonetic typos.
