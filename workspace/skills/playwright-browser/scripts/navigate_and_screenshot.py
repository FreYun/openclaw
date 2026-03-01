#!/usr/bin/env python3
"""
Navigate to a URL and take a screenshot.

Usage:
    python navigate_and_screenshot.py https://www.baidu.com
    python navigate_and_screenshot.py https://www.baidu.com --output baidu.png --full-page
    python navigate_and_screenshot.py https://www.baidu.com --wait-for "selector:.result"

Arguments:
    url             Target URL to navigate to
    --output        Screenshot filename (default: screenshot.png)
    --full-page     Capture full page (default: viewport only)
    --wait-for      Wait for element before screenshot (format: selector:<css> or time:<seconds>)
    --viewport      Viewport size (format: width,height, default: 1920,1080)
    --headless      Run in headless mode (default: False)
"""

import argparse
import sys
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description='Navigate and screenshot')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('--output', default='screenshot.png', help='Output filename')
    parser.add_argument('--full-page', action='store_true', help='Full page screenshot')
    parser.add_argument('--wait-for', help='Wait condition (selector:<css> or time:<seconds>)')
    parser.add_argument('--viewport', default='1920,1080', help='Viewport size (width,height)')
    parser.add_argument('--headless', action='store_true', help='Headless mode')
    
    args = parser.parse_args()
    
    # Parse viewport
    try:
        width, height = map(int, args.viewport.split(','))
    except ValueError:
        print("Error: Viewport must be in format 'width,height'", file=sys.stderr)
        sys.exit(1)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=args.headless)
        context = browser.new_context(viewport={'width': width, 'height': height})
        page = context.new_page()
        
        print(f"Navigating to {args.url}...")
        page.goto(args.url, wait_until='networkidle')
        print(f"Page loaded: {page.title()}")
        
        # Handle wait condition
        if args.wait_for:
            if args.wait_for.startswith('selector:'):
                selector = args.wait_for[9:]
                print(f"Waiting for element: {selector}")
                page.wait_for_selector(selector, timeout=10000)
            elif args.wait_for.startswith('time:'):
                seconds = float(args.wait_for[5:])
                print(f"Waiting {seconds} seconds...")
                page.wait_for_timeout(int(seconds * 1000))
        
        # Take screenshot
        print(f"Taking screenshot...")
        page.screenshot(path=args.output, full_page=args.full_page)
        print(f"Screenshot saved: {args.output}")
        
        browser.close()


if __name__ == '__main__':
    main()
