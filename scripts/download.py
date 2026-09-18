#!/usr/bin/env python3
"""
wechat-article-media-download
Download all videos and images embedded in a WeChat official account article.

Works WITHOUT a WeChat client and WITHOUT mp.weixin.qq.com login:
video direct links (signed mpvideo.qpic.cn URLs) are extracted from the
inline JS data blocks of the article HTML itself.

Usage:
    python3 download.py <article_url> [output_dir]

Requires: Python 3.7+ (stdlib only)
"""

import html as htmllib
import json
import os
import re
import sys
import threading
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"}

# preferred video formats, best first (10002 = 超清 H.264)
FORMAT_PRIORITY = ["10002", "10102", "10004", "10104"]


def fetch(url, dest=None):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if dest:
        with open(dest, "wb") as f:
            f.write(data)
    return data


def unescape_js(html_text):
    """Undo the JS escaping used in article data blocks.

    Video URLs are stored like `url: 'http://mpvideo.qpic.cn/...\\x26amp;dis_t=...'`.
    Missing this step truncates every URL at its first `&`.
    """
    txt = htmllib.unescape(html_text)
    txt = txt.replace("\\x26amp;", "&").replace("\\x26;", "&").replace("\\x26", "&")
    return txt


def extract_images(html_text):
    seen, out = set(), []
    for u in re.findall(r'data-src="(https://mmbiz\.qpic\.cn/[^"]+)"', html_text):
        if u not in seen:
            seen.add(u)
            fmt_m = re.search(r"wx_fmt=(\w+)", u)
            out.append((u, fmt_m.group(1) if fmt_m else "png"))
    return out


def extract_videos(html_text):
    """Return an ordered list of (best_format, url) — one entry per article video.

    Each video appears as ~4 format variants sharing the same base path;
    order of first appearance matches article order.
    """
    txt = unescape_js(html_text)
    blocks = re.findall(
        r"format_id:\s*'(\d+)'\s*\*[^}]*?url:\s*'(http://mpvideo\.qpic\.cn/[^']+)'",
        txt,
        re.S,
    )
    groups, order = {}, []
    for fid, url in blocks:
        m = re.match(r"(http://mpvideo\.qpic\.cn/[a-z0-9]+)\.f\d+\.mp4", url)
        if not m:
            continue
        base = m.group(1)
        if base not in groups:
            groups[base] = {}
            order.append(base)
        groups[base][fid] = url
    plan = []
    for base in order:
        for fid in FORMAT_PRIORITY:
            if fid in groups[base]:
                plan.append((fid, groups[base][fid]))
                break
    return plan


def download_all(items, outdir, prefix, ext_default="bin"):
    """items: list of (name_hint, url, ext). Returns list of (path, size)."""
    os.makedirs(outdir, exist_ok=True)
    results, lock = [], threading.Lock()

    def work(i, url, ext):
        path = os.path.join(outdir, f"{prefix}_{i:02d}.{ext}")
        try:
            fetch(url, path)
            size = os.path.getsize(path)
        except Exception as e:  # noqa: BLE001
            size = 0
            with lock:
                print(f"  [FAIL] {path}: {e}")
        with lock:
            print(f"  [OK] {path} ({size / 1024:.0f} KB)" if size else f"  [FAIL] {path}")
            results.append((path, size))

    threads = [
        threading.Thread(target=work, args=(i, url, ext))
        for i, (url, ext) in enumerate(items, 1)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return sorted(results)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    article_url = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "output"

    print(f"[1/4] Fetching article: {article_url}")
    html_text = fetch(article_url).decode("utf-8", errors="ignore")

    title_m = re.search(r'<meta property="og:title" content="([^"]*)"', html_text)
    print(f"      Title: {title_m.group(1) if title_m else 'N/A'}")

    print("[2/4] Extracting media links ...")
    images = extract_images(html_text)
    videos = extract_videos(html_text)
    print(f"      Found {len(videos)} videos, {len(images)} images")

    print(f"[3/4] Downloading to {outdir}/ ...")
    vres = download_all([(u, "mp4") for _, u in videos], os.path.join(outdir, "videos"), "video")
    ires = download_all([(u, e) for u, e in images], os.path.join(outdir, "images"), "image")

    print("[4/4] Verification")
    ok_v = sum(1 for _, s in vres if s > 100_000)
    ok_i = sum(1 for _, s in ires if s > 0)
    print(f"      videos: {ok_v}/{len(vres)} valid (>100KB)")
    print(f"      images: {ok_i}/{len(ires)} valid")

    json.dump(
        {"article": article_url, "videos": [u for _, u in videos], "images": [u for u, _ in images]},
        open(os.path.join(outdir, "sources.json"), "w"),
        ensure_ascii=False,
        indent=1,
    )
    print("Done. Link sources saved to sources.json")


if __name__ == "__main__":
    main()
