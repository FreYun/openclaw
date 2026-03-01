#!/usr/bin/env python3
"""
Enhanced web fetch with fallback strategies and better error handling.

This script tries multiple methods to fetch a URL:
1. Direct HTTP request (requests library)
2. With different User-Agent headers
3. Via textise dot iitty service (for HTML pages)
4. Via textise dot iitty text extraction

Usage:
    python fetch_url.py https://example.com
    python fetch_url.py https://example.com --max-chars 5000
    python fetch_url.py https://example.com --output markdown

Arguments:
    url             URL to fetch
    --max-chars     Maximum characters to return (default: 10000)
    --output        Output format: markdown, text, json (default: markdown)
    --timeout       Request timeout in seconds (default: 30)
    --retries       Number of retries (default: 3)
"""

import argparse
import json
import sys
import time
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests/beautifulsoup4 not installed. Install with: pip install requests beautifulsoup4", file=sys.stderr)


def fetch_with_requests(url, timeout=30, headers=None):
    """Fetch URL using requests library."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not available")
    
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    if headers:
        default_headers.update(headers)
    
    response = requests.get(url, headers=default_headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    
    # Detect encoding from response
    if response.encoding == 'ISO-8859-1':
        # Try to detect from content
        response.encoding = response.apparent_encoding
    
    return response.text, response.status_code


def extract_text_from_html(html):
    """Extract readable text from HTML."""
    if not REQUESTS_AVAILABLE:
        return html
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


def fetch_with_fallback(url, max_chars=10000, timeout=30, retries=3):
    """Try multiple methods to fetch URL content."""
    errors = []
    
    # Method 1: Direct requests
    for attempt in range(retries):
        try:
            html, status = fetch_with_requests(url, timeout=timeout)
            text = extract_text_from_html(html)
            
            return {
                'success': True,
                'url': url,
                'status': status,
                'method': 'direct',
                'content': text[:max_chars],
                'truncated': len(text) > max_chars
            }
        except Exception as e:
            errors.append(f"Attempt {attempt + 1}: {str(e)}")
            if attempt < retries - 1:
                time.sleep(1)
    
    # Method 2: Try jina.ai summarizer service
    try:
        parsed = urlparse(url)
        jina_url = f"https://r.jina.ai/http://{parsed.netloc}{parsed.path}"
        
        response = requests.get(jina_url, timeout=timeout)
        response.raise_for_status()
        
        return {
            'success': True,
            'url': url,
            'status': response.status_code,
            'method': 'r.jina.ai',
            'content': response.text[:max_chars],
            'truncated': len(response.text) > max_chars
        }
    except Exception as e:
        errors.append(f"r.jina.ai failed: {str(e)}")
    
    # All methods failed
    return {
        'success': False,
        'url': url,
        'errors': errors
    }


def save_to_file(content, filename):
    """Save content to file with proper encoding."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return filename


def main():
    parser = argparse.ArgumentParser(description='Enhanced web fetch')
    parser.add_argument('url', help='URL to fetch')
    parser.add_argument('--max-chars', type=int, default=10000, help='Maximum characters')
    parser.add_argument('--output', default='json', choices=['json', 'markdown', 'text'])
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries')
    parser.add_argument('--save', help='Save content to file instead of stdout')
    
    args = parser.parse_args()
    
    result = fetch_with_fallback(args.url, args.max_chars, args.timeout, args.retries)
    
    # Prepare output
    if args.output == 'json':
        output = json.dumps(result, ensure_ascii=False, indent=2)
    elif args.output == 'markdown':
        if result['success']:
            lines = [f"# Content from {result['url']}\n", result['content']]
            if result.get('truncated'):
                lines.append("\n... (truncated)")
            output = '\n'.join(lines)
        else:
            lines = [f"# Failed to fetch {args.url}\n"]
            for error in result['errors']:
                lines.append(f"- {error}")
            output = '\n'.join(lines)
    else:  # text
        if result['success']:
            output = result['content']
        else:
            output = f"Failed: {'; '.join(result['errors'])}"
    
    # Save to file or print
    if args.save:
        filepath = save_to_file(output, args.save)
        print(json.dumps({
            'success': result['success'],
            'saved_to': filepath,
            'url': args.url
        }))
    else:
        # For non-JSON output, always save to temp file and return path
        # to avoid console encoding issues
        if args.output != 'json':
            temp_file = 'fetch_output.txt'
            filepath = save_to_file(output, temp_file)
            print(json.dumps({
                'success': result['success'],
                'output_file': filepath,
                'url': args.url,
                'preview': result.get('content', '')[:200] + '...' if result.get('content') else ''
            }))
        else:
            print(output)


if __name__ == '__main__':
    main()
