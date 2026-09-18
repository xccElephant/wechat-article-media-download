---
name: wechat-article-media-download
description: Download all videos and images embedded in a WeChat official account (mp.weixin.qq.com) article. Trigger when the user gives an mp.weixin.qq.com/s/... link and asks to 下载/保存 文章里的 视频/图片/素材. Works without WeChat client or MP platform login by extracting signed mpvideo CDN URLs from the article HTML.
description_zh: 下载微信公众号文章内的全部视频和图片
description_en: Download videos and images from a WeChat article
disable: false
agent_created: true
---

# wechat-article-media-download

## When to use
- User provides a `https://mp.weixin.qq.com/s/...` link and wants the article's videos and/or images downloaded locally.

## Steps

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

## Pitfalls
- Do NOT bother with `mp/videoplayer?action=get_video_info` or `get_mp_video_play_url` APIs — they now return `no session` / omit `url_info` anonymously. The signed CDN URLs in the article HTML are the reliable path.
- `dis_t` in URLs is an expiry timestamp (usually ~1 week after page fetch) — download promptly after fetching the HTML.
- The video iframes have empty `src` in desktop browsers and the player template requires WeixinJSBridge — browser automation does NOT help; skip it.
- URL regex must exclude backslash-safe: extract only AFTER replacing `\\x26amp;`/`\\x26`, otherwise every URL is truncated at its first `&` (returns empty 0-byte files).
- Regex group bug to avoid: base path grouping must strip `.f\d+` (e.g. `xxx.f10002.mp4`), otherwise each format becomes its own "video" (36 groups instead of 9).

## Verification
- Count of video groups should equal the count of `vid=wxv_*` iframes in the HTML.
- Every downloaded MP4 passes `file` check as ISO Media; every image has nonzero size and matches its declared format.
