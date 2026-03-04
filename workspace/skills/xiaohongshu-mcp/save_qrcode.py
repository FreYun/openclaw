#!/usr/bin/env python3
"""
Fetch Xiaohongshu login QR code from MCP server and save to this skill folder.
Run this script when you need to log in: open the saved qrcode.png and scan with Xiaohongshu app.

Usage:
  python save_qrcode.py
  python save_qrcode.py --url http://localhost:18060

Requires: requests (pip install requests)
"""

import argparse
import base64
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

DEFAULT_URL = "http://localhost:18060"
QRCODE_FILENAME = "qrcode.png"


def main():
    parser = argparse.ArgumentParser(description="Save Xiaohongshu login QR code to workspace")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"MCP server base URL (default: {DEFAULT_URL})")
    parser.add_argument("-o", "--output", default=None, help=f"Output path (default: same dir as script, {QRCODE_FILENAME})")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    out_path = Path(args.output) if args.output else script_dir / QRCODE_FILENAME

    url = f"{args.url.rstrip('/')}/api/v1/login/qrcode"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(e.response.text[:500], file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not data.get("success"):
        print(f"API error: {data.get('message', data)}", file=sys.stderr)
        sys.exit(1)

    payload = data.get("data") or {}
    if payload.get("is_logged_in"):
        print("Already logged in. No QR code needed.")
        sys.exit(0)

    img_b64 = payload.get("img") or ""
    if not img_b64:
        print("No image in response.", file=sys.stderr)
        sys.exit(1)

    if img_b64.startswith("data:image/png;base64,"):
        img_b64 = img_b64.split(",", 1)[1]
    raw = base64.b64decode(img_b64)
    out_path.write_bytes(raw)

    try:
        display_path = out_path.relative_to(Path.cwd())
    except ValueError:
        display_path = out_path
    print(f"QR code saved: {display_path}")
    print("Open this file and scan with the Xiaohongshu app, then confirm login on your phone.")


if __name__ == "__main__":
    main()
