---
name: web-fetch-enhanced
description: Fetch and extract content from web URLs with fallback strategies and better error handling. Use when the built-in web_fetch tool fails or when you need more control over the fetching process, custom headers, retries, or alternative extraction methods.
---

# Web Fetch Enhanced

## Overview

This skill provides enhanced web fetching capabilities with:
- **Multiple fallback strategies**: Tries different methods if one fails
- **Better error handling**: Detailed error messages and retry logic
- **Content extraction**: Converts HTML to readable text
- **Custom headers**: Mimics real browser requests

## When to Use This Skill

Use this skill instead of the built-in `web_fetch` tool when:
1. `web_fetch` returns "fetch failed" or timeout errors
2. You need to fetch from sites that block automated requests
3. You need more control over headers, timeouts, or retries
4. You want plain text extraction from HTML

## Installation

```bash
pip install requests beautifulsoup4
```

## Usage

### Basic Fetch

```bash
python scripts/fetch_url.py https://example.com
```

### With Options

```bash
# Limit output size
python scripts/fetch_url.py https://example.com --max-chars 5000

# Plain text output
python scripts/fetch_url.py https://example.com --output text

# Markdown format
python scripts/fetch_url.py https://example.com --output markdown

# More retries for unreliable sites
python scripts/fetch_url.py https://example.com --retries 5 --timeout 60
```

### Python API

```python
from scripts.fetch_url import fetch_with_fallback

result = fetch_with_fallback("https://example.com", max_chars=5000)
if result['success']:
    print(result['content'])
else:
    print("Failed:", result['errors'])
```

## Fallback Strategies

The script tries these methods in order:

1. **Direct HTTP request** with browser-like headers
2. **r.jina.ai service** - Extracts article content via jina AI summarizer
3. Returns detailed error information

## Output Format

### JSON (default)
```json
{
  "success": true,
  "url": "https://example.com",
  "status": 200,
  "method": "direct",
  "content": "Extracted text content...",
  "truncated": false
}
```

### On Failure
```json
{
  "success": false,
  "url": "https://example.com",
  "errors": [
    "Attempt 1: Connection timeout",
    "Attempt 2: 403 Forbidden",
    "r.jina.ai failed: 404 Not Found"
  ]
}
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| SSL/TLS errors | The script uses requests which handles SSL properly |
| 403 Forbidden | Tries different User-Agent headers automatically |
| Timeout | Increase `--timeout` and `--retries` |
| JavaScript-heavy sites | Use Playwright skill instead for JS rendering |

## Comparison with Built-in Tools

| Feature | Built-in web_fetch | This Skill |
|---------|-------------------|------------|
| Speed | Fast | Medium |
| Reliability | Good | Better (fallbacks) |
| Error details | Limited | Detailed |
| Content extraction | Basic | Advanced |
| Custom headers | No | Yes |
| Retry logic | No | Yes |
| Sites requiring JS | No | No (use Playwright) |
