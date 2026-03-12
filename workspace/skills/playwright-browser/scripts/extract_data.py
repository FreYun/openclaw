#!/usr/bin/env python3
"""
Extract structured data from a webpage.

Usage:
    python extract_data.py https://news.ycombinator.com --selector ".titleline > a" --limit 10
    python extract_data.py https://example.com --selector ".product" --fields "name=.title,price=.price"

Arguments:
    url             Target URL
    --selector      CSS selector for elements to extract
    --fields        Comma-separated field mappings (format: name=selector)
    --limit         Maximum items to extract (default: all)
    --attribute     Extract attribute instead of text (e.g., 'href')
    --output        Output format: json, csv (default: json)
"""

import argparse
import json
import csv
import sys
from playwright.sync_api import sync_playwright


def extract_elements(page, selector, limit=None, attribute=None):
    """Extract data from elements matching selector."""
    elements = page.locator(selector).all()
    
    if limit:
        elements = elements[:limit]
    
    results = []
    for elem in elements:
        if attribute:
            value = elem.get_attribute(attribute)
        else:
            value = elem.inner_text()
        results.append(value.strip() if value else '')
    
    return results


def extract_structured(page, selector, field_map, limit=None):
    """Extract structured data with multiple fields per element."""
    elements = page.locator(selector).all()
    
    if limit:
        elements = elements[:limit]
    
    results = []
    for elem in elements:
        item = {}
        for field_name, field_selector in field_map.items():
            try:
                child = elem.locator(field_selector).first
                item[field_name] = child.inner_text().strip() if child.count() > 0 else ''
            except Exception:
                item[field_name] = ''
        results.append(item)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Extract web data')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('--selector', required=True, help='CSS selector')
    parser.add_argument('--fields', help='Field mappings (format: name=selector,name2=selector2)')
    parser.add_argument('--limit', type=int, help='Maximum items')
    parser.add_argument('--attribute', help='Extract attribute instead of text')
    parser.add_argument('--output', default='json', choices=['json', 'csv'])
    
    args = parser.parse_args()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Loading {args.url}...", file=sys.stderr)
        page.goto(args.url, wait_until='networkidle')
        
        # Parse field mappings if provided
        if args.fields:
            field_map = {}
            for mapping in args.fields.split(','):
                if '=' in mapping:
                    name, selector = mapping.split('=', 1)
                    field_map[name.strip()] = selector.strip()
            
            results = extract_structured(page, args.selector, field_map, args.limit)
        else:
            results = extract_elements(page, args.selector, args.limit, args.attribute)
            results = [{'text': r} for r in results]
        
        browser.close()
        
        # Output results
        if args.output == 'json':
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            if results:
                writer = csv.DictWriter(sys.stdout, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)


if __name__ == '__main__':
    main()
