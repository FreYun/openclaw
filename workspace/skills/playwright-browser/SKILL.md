---
name: playwright-browser
description: Control web browsers using Playwright for web automation, scraping, and testing. Use when the user needs to automate browser actions like navigating websites, clicking elements, filling forms, taking screenshots, or extracting web data programmatically.
---

# Playwright Browser Automation

## Overview

Playwright is a Python library for automating web browsers (Chrome, Firefox, Safari). It provides:
- **Cross-browser support**: Chrome, Firefox, WebKit
- **Headless mode**: Run without visible UI
- **Auto-wait**: Automatically waits for elements
- **Screenshots & PDFs**: Capture page content
- **Mobile emulation**: Test responsive designs

## Installation

```bash
pip install playwright
playwright install chromium  # Install browser binaries
```

## Quick Start

### Launch a Browser

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch Chrome
    browser = p.chromium.launch(channel="chrome", headless=False)
    
    # Create context and page
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate
    page.goto("https://www.google.com")
    
    # Close
    browser.close()
```

### Connect to Existing Chrome (CDP)

If Chrome is already running with remote debugging:

```python
# Chrome must be started with: --remote-debugging-port=9222
browser = p.chromium.connect_over_cdp("http://localhost:9222")
```

## Common Operations

### Navigation

```python
page.goto("https://example.com")           # Go to URL
page.go_back()                             # Back button
page.go_forward()                          # Forward button
page.reload()                              # Refresh
```

### Element Interaction

```python
# Click
page.click("button#submit")
page.locator("button#submit").click()

# Fill input
page.fill("input[name='username']", "myuser")
page.locator("input[name='username']").fill("myuser")

# Type with delay (simulates human typing)
page.type("input[name='search']", "hello world", delay=100)

# Press keys
page.press("input", "Enter")
```

### Extract Data

```python
# Get text
text = page.inner_text("h1")

# Get attribute
href = page.get_attribute("a.link", "href")

# Find multiple elements
items = page.query_selector_all(".item")
for item in items:
    title = item.inner_text()
    print(title)

# Using locators (recommended)
locator = page.locator(".product-title")
count = locator.count()
titles = locator.all_inner_texts()
```

### Screenshots

```python
# Full page
page.screenshot(path="full.png", full_page=True)

# Specific element
element = page.locator(".chart")
element.screenshot(path="chart.png")

# As bytes (for further processing)
screenshot_bytes = page.screenshot()
```

### Waiting

```python
# Wait for element
page.wait_for_selector(".result", timeout=5000)

# Wait for navigation
page.wait_for_load_state("networkidle")

# Wait for specific condition
page.wait_for_function("() => document.title.includes('Success')")
```

## Scripts

The `scripts/` directory contains ready-to-use automation scripts:

### navigate_and_screenshot.py
Navigate to a URL and take a screenshot.

```bash
python scripts/navigate_and_screenshot.py https://www.baidu.com --output baidu.png
```

### extract_data.py
Extract structured data from a webpage.

```bash
python scripts/extract_data.py https://news.ycombinator.com --selector ".titleline > a"
```

### form_automation.py
Fill and submit forms.

```bash
python scripts/form_automation.py https://example.com/login \
    --field username=myuser \
    --field password=mypass \
    --submit "button[type='submit']"
```

## Best Practices

### Always Use Context Managers

```python
# Good - auto cleanup
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    # ... do work ...
    browser.close()
```

### Handle Timeouts

```python
from playwright.sync_api import TimeoutError as PlaywrightTimeout

try:
    page.click(".slow-loading-button", timeout=10000)
except PlaywrightTimeout:
    print("Element didn't appear in time")
```

### Use Locators (Modern API)

```python
# Old way (still works)
page.click("button.submit")

# New way (recommended)
page.locator("button.submit").click()

# Chain filters
page.locator(".product").filter(has_text="Sale").click()
```

## Headless vs Headed

```python
# Headless - no UI, faster, for servers
browser = p.chromium.launch(headless=True)

# Headed - visible browser window
browser = p.chromium.launch(headless=False)
```

## Mobile Emulation

```python
iphone = p.devices['iPhone 14 Pro Max']
context = browser.new_context(**iphone)
page = context.new_page()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Executable doesn't exist` | Run `playwright install chromium` |
| Element not found | Increase timeout, check selector |
| Connection refused (CDP) | Ensure Chrome started with `--remote-debugging-port=9222` |
| Anti-bot detection | Use stealth plugins or slow down actions |
