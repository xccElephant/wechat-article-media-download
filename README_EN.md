# wechat-article-media-download

[中文](README.md) | English

Download **all videos and images** embedded in a WeChat Official Account article — no WeChat client, no login, no tokens required.

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## How It Works

At the end of a WeChat article page (`mp.weixin.qq.com/s/...`), the HTML source contains an inline JS data block that **already includes signed direct URLs for each video in 4 quality levels** (`mpvideo.qpic.cn`, with `dis_k` / `auth_key` signature parameters). This tool extracts those URLs straight from the source and downloads them:

- **Images**: public `mmbiz.qpic.cn` URLs found in `data-src` attributes — permanently valid
- **Videos**: signed direct URLs from the inline JS data block — **valid for ~7 days** after the page is fetched; downloaded in parallel
- Each video automatically selects the best quality (prefers `f10002` — 1080p H.264, best compatibility)

No WeChat API is called — the `videoplayer` API family now requires an authenticated session and returns nothing useful to anonymous callers, so that path is a dead end.

## Installation

The script is a **single Python file with zero third-party dependencies** (stdlib only). You just need Python 3.7+.

### 1. Install Python (skip if you already have it)

**macOS**
```bash
# Check first
python3 --version
# If missing, install via Homebrew
brew install python
```
Or download the installer from [python.org/downloads](https://www.python.org/downloads/).

**Windows**
- Download from [python.org/downloads](https://www.python.org/downloads/) and run the installer
- ⚠️ Check **"Add python.exe to PATH"** during installation
- Verify in PowerShell: `python --version`

**Linux (Debian/Ubuntu)**
```bash
sudo apt update && sudo apt install -y python3
```

### 2. Get the script

```bash
git clone https://github.com/xccElephant/wechat-article-media-download.git
cd wechat-article-media-download

# Or, without git: just download the single file
# curl -O https://raw.githubusercontent.com/xccElephant/wechat-article-media-download/main/scripts/download.py
```

That's it — no `pip install` needed.

## Usage

```bash
python3 scripts/download.py <article_url> [output_dir]

# Example
python3 scripts/download.py "https://mp.weixin.qq.com/s/ICb4P_FqTZVgaeMvZs_9dg" ./output
```

On Windows (PowerShell), use `python` instead of `python3`:
```powershell
python scripts/download.py "https://mp.weixin.qq.com/s/..." .\output
```

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
