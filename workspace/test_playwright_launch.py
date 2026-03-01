#!/usr/bin/env python3
"""
Test script: Launch a new Chrome browser with Playwright and navigate to a page.

This is useful when you don't have an existing Chrome instance with CDP enabled.
"""

from playwright.sync_api import sync_playwright
import time


def launch_and_navigate():
    """Launch Chrome and navigate to a website."""
    with sync_playwright() as p:
        print("Launching Chrome...")
        
        # Launch Chrome browser
        # channel="chrome" uses the installed Google Chrome instead of Chromium
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,  # Set to True for headless mode
            args=['--start-maximized']
        )
        
        print(f"✅ Chrome launched!")
        print(f"   Version: {browser.version}")
        
        # Create a new context (browser profile)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create a new page
        page = context.new_page()
        
        # Navigate to a website
        url = "https://www.baidu.com"
        print(f"\nNavigating to {url}...")
        page.goto(url)
        
        print(f"✅ Page loaded: {page.title()}")
        print(f"   URL: {page.url}")
        
        # Example: Take a screenshot
        screenshot_path = "baidu_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved: {screenshot_path}")
        
        # Example: Get page content
        # content = page.content()
        # print(f"Page content length: {len(content)} chars")
        
        # Example: Find elements
        search_box = page.locator('input[name="wd"]')
        if search_box.count() > 0:
            print("✅ Found search box on Baidu")
        
        # Keep browser open for 5 seconds so you can see it
        print("\n⏳ Keeping browser open for 5 seconds...")
        time.sleep(5)
        
        # Close everything
        context.close()
        browser.close()
        print("\n✅ Browser closed")


if __name__ == "__main__":
    launch_and_navigate()
