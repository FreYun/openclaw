#!/usr/bin/env python3
"""
从小红书笔记图片中提取文字（OCR），供无 Vision 能力的 Agent 学习图文笔记内容。

典型场景：博主如「钞级马力」将核心内容放在图片里（一图了解、大白话、抄作业等），
get_feed_detail 只返回标题和 imageList，需用本脚本提取图片文字才能完整学习。

用法:
  # 从 get_feed_detail 的 JSON 中提取图片 URL 并 OCR
  python3 extract_image_text.py --from-json /path/to/feed_detail.json

  # 直接传入图片 URL
  python3 extract_image_text.py --urls "https://..." "https://..."

  # 从本地图片文件 OCR
  python3 extract_image_text.py --paths /path/to/1.png /path/to/2.jpg

Requires: pytesseract, Pillow, requests
  pip install pytesseract Pillow requests
  # 系统需安装 tesseract + 中文语言包: apt install tesseract-ocr tesseract-ocr-chi-sim
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

try:
    import requests
    from PIL import Image
    import pytesseract
except ImportError as e:
    print(f"Install: pip install pytesseract Pillow requests\n{e}", file=sys.stderr)
    sys.exit(1)

SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_LANGS = "chi_sim+eng"


def build_image_url(item: dict) -> str | None:
    """从 get_feed_detail 的 imageList 项构建完整图片 URL。"""
    url_pre = item.get("urlPre") or item.get("url_pre") or ""
    url_default = item.get("urlDefault") or item.get("url_default") or ""
    if not url_default:
        return None
    if url_default.startswith("http"):
        return url_default
    return (url_pre or "").rstrip("/") + "/" + url_default.lstrip("/")


def extract_urls_from_feed_json(data: dict) -> list[str]:
    """从 get_feed_detail 返回的 JSON 中提取图片 URL 列表。"""
    urls = []
    note = data.get("note") or data.get("Note") if isinstance(data, dict) else None
    if not note:
        return urls
    image_list = note.get("imageList") or note.get("image_list") or []
    for item in image_list:
        if isinstance(item, dict):
            u = build_image_url(item)
            if u:
                urls.append(u)
        elif isinstance(item, str):
            urls.append(item)
    return urls


def download_image(url: str, dest_dir: Path) -> Path | None:
    """下载图片到临时目录，返回本地路径。"""
    try:
        r = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
                "Referer": "https://www.xiaohongshu.com/",
            },
        )
        r.raise_for_status()
        ext = "jpg"
        ct = r.headers.get("Content-Type", "")
        if "png" in ct:
            ext = "png"
        elif "webp" in ct:
            ext = "webp"
        path = dest_dir / f"img_{hash(url) % 10**8}.{ext}"
        path.write_bytes(r.content)
        return path
    except Exception as e:
        print(f"⚠ 下载失败 {url[:60]}...: {e}", file=sys.stderr)
        return None


def ocr_image(path: Path, langs: str = DEFAULT_LANGS) -> str:
    """对单张图片进行 OCR，返回提取的文字。"""
    try:
        img = Image.open(path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img, lang=langs)
        return (text or "").strip()
    except Exception as e:
        return f"[OCR 失败: {e}]"


def extract_from_urls(urls: list[str], langs: str = DEFAULT_LANGS) -> str:
    """从 URL 列表下载并 OCR，返回合并后的文字。"""
    if not urls:
        return ""
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        for i, url in enumerate(urls):
            local = download_image(url, dest)
            if local:
                t = ocr_image(local, langs)
                if t:
                    parts.append(f"--- 图片 {i+1} ---\n{t}")
    return "\n\n".join(parts) if parts else ""


def extract_from_paths(paths: list[Path], langs: str = DEFAULT_LANGS) -> str:
    """从本地路径列表 OCR，返回合并后的文字。"""
    parts = []
    for i, p in enumerate(paths):
        if p.exists():
            t = ocr_image(p, langs)
            if t:
                parts.append(f"--- 图片 {i+1} ---\n{t}")
    return "\n\n".join(parts) if parts else ""


def main():
    parser = argparse.ArgumentParser(
        description="从小红书笔记图片中提取文字（OCR），供无 Vision 的 Agent 学习图文内容"
    )
    parser.add_argument(
        "--from-json",
        metavar="FILE",
        help="get_feed_detail 返回的 JSON 文件路径，自动提取 imageList 中的图片 URL",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        metavar="URL",
        help="直接传入图片 URL 列表",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        metavar="PATH",
        help="本地图片文件路径列表",
    )
    parser.add_argument(
        "--langs",
        default=DEFAULT_LANGS,
        help=f"Tesseract 语言（默认: {DEFAULT_LANGS}）",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="将提取结果写入文件，不填则输出到 stdout",
    )
    args = parser.parse_args()

    text = ""
    if args.from_json:
        p = Path(args.from_json)
        if not p.exists():
            print(f"❌ 文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))
        urls = extract_urls_from_feed_json(data)
        if not urls:
            print("⚠ JSON 中未找到 imageList 或图片 URL", file=sys.stderr)
        else:
            text = extract_from_urls(urls, args.langs)
    elif args.urls:
        text = extract_from_urls(args.urls, args.langs)
    elif args.paths:
        paths = [Path(x) for x in args.paths]
        text = extract_from_paths(paths, args.langs)
    else:
        parser.print_help()
        print("\n示例:", file=sys.stderr)
        print("  python3 extract_image_text.py --from-json feed_detail.json", file=sys.stderr)
        print("  python3 extract_image_text.py --urls 'https://...' 'https://...'", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"✅ 已写入: {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
