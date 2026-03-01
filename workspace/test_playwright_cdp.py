#!/usr/bin/env python3
"""
Test script: Connect to existing Chrome via CDP (Chrome DevTools Protocol)

Prerequisites:
1. Chrome must be started with remote debugging enabled:
   chrome.exe --remote-debugging-port=9222

2. Or use an already running Chrome instance with OpenClaw's browser relay

This script demonstrates how to connect Playwright to an existing Chrome.
"""

from playwright.sync_api import sync_playwright
import json
import sys


def connect_to_chrome(cdp_url: str = "http://localhost:9222"):
    """
    Connect to existing Chrome via CDP.
    
    Args:
        cdp_url: Chrome DevTools Protocol endpoint URL
                 Default: http://localhost:9222
    """
    with sync_playwright() as p:
        # Connect to existing Chrome browser via CDP
        print(f"Connecting to Chrome at {cdp_url}...")
        
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            print(f"✅ Connected successfully!")
            print(f"   Browser version: {browser.version}")
            print(f"   Contexts: {len(browser.contexts)}")
            
            # List all pages/tabs
            for i, context in enumerate(browser.contexts):
                print(f"\n   Context {i+1}:")
                for j, page in enumerate(context.pages):
                    print(f"     Page {j+1}: {page.url[:80]}...")
                    
            # Get the first page and take a screenshot
            if browser.contexts and browser.contexts[0].pages:
                page = browser.contexts[0].pages[0]
                print(f"\n   Active page title: {page.title()}")
                
                # Example: Navigate to a new URL
                # page.goto("https://www.google.com")
                
                # Example: Take screenshot
                # page.screenshot(path="screenshot.png")
                
            browser.close()
            print("\n✅ Connection closed")
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure Chrome is running with --remote-debugging-port=9222")
            print("2. Check if the port is correct")
            print("3. Try accessing http://localhost:9222/json/version in your browser")
            return False
            
    return True


def main():
    # Default CDP endpoint
    cdp_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9222"
    connect_to_chrome(cdp_url)


if __name__ == "__main__":
    main()
