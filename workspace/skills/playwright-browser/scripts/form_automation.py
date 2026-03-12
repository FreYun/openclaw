#!/usr/bin/env python3
"""
Automate form filling and submission.

Usage:
    python form_automation.py https://example.com/login \
        --field username=myuser \
        --field password=mypass \
        --submit "button[type='submit']"
    
    python form_automation.py https://example.com/search \
        --field "q=search term" \
        --submit "input[type='submit']" \
        --wait-for selector:.results

Arguments:
    url             Target URL with form
    --field         Field values (format: selector=value or name=value)
    --submit        Submit button selector
    --wait-for      Wait condition after submit (selector:<css> or time:<seconds>)
    --screenshot    Save screenshot after submission
    --headless      Run in headless mode
"""

import argparse
import sys
from playwright.sync_api import sync_playwright


def parse_field(field_str):
    """Parse field string into (selector, value)."""
    if '=' in field_str:
        key, value = field_str.split('=', 1)
        return key.strip(), value.strip()
    return None, None


def main():
    parser = argparse.ArgumentParser(description='Form automation')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('--field', action='append', required=True, help='Field values (can be used multiple times)')
    parser.add_argument('--submit', help='Submit button selector')
    parser.add_argument('--wait-for', help='Wait condition after submit')
    parser.add_argument('--screenshot', help='Save screenshot to this path')
    parser.add_argument('--headless', action='store_true', help='Headless mode')
    
    args = parser.parse_args()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Loading {args.url}...")
        page.goto(args.url, wait_until='networkidle')
        
        # Fill form fields
        for field_str in args.field:
            selector, value = parse_field(field_str)
            if not selector:
                print(f"Invalid field format: {field_str}", file=sys.stderr)
                continue
            
            # If selector doesn't start with common prefixes, assume it's a name attribute
            if not any(selector.startswith(p) for p in ['#', '.', '[', 'input', 'textarea', 'select']):
                selector = f"[name='{selector}']"
            
            print(f"Filling {selector} with '{value}'...")
            page.fill(selector, value)
        
        # Submit form
        if args.submit:
            print(f"Clicking submit button: {args.submit}")
            page.click(args.submit)
        else:
            # Try to find and click first submit button
            submit_btn = page.locator("button[type='submit'], input[type='submit']").first
            if submit_btn.count() > 0:
                print("Clicking first submit button...")
                submit_btn.click()
        
        # Wait for condition
        if args.wait_for:
            if args.wait_for.startswith('selector:'):
                sel = args.wait_for[9:]
                print(f"Waiting for element: {sel}")
                page.wait_for_selector(sel, timeout=10000)
            elif args.wait_for.startswith('time:'):
                secs = float(args.wait_for[5:])
                print(f"Waiting {secs} seconds...")
                page.wait_for_timeout(int(secs * 1000))
            elif args.wait_for.startswith('url:'):
                expected_url = args.wait_for[4:]
                print(f"Waiting for URL containing: {expected_url}")
                page.wait_for_url(f"*{expected_url}*", timeout=10000)
        else:
            # Default: wait for navigation to complete
            page.wait_for_load_state('networkidle')
        
        print(f"Current URL: {page.url}")
        print(f"Page title: {page.title()}")
        
        # Take screenshot if requested
        if args.screenshot:
            page.screenshot(path=args.screenshot, full_page=True)
            print(f"Screenshot saved: {args.screenshot}")
        
        browser.close()
        print("Done!")


if __name__ == '__main__':
    main()
