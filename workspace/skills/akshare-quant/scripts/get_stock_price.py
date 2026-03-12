#!/usr/bin/env python3
"""
Get current stock price and basic info for a given stock code.

Usage:
    python get_stock_price.py 600519
    python get_stock_price.py 000001

Output format (JSON):
    {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1434.00,
        "industry": "白酒",
        "total_shares": 1252270215,
        "market_cap": 1839008901536.10
    }
"""

import sys
import json
import akshare as ak


def get_stock_info(symbol: str) -> dict:
    """Get basic stock information."""
    df = ak.stock_individual_info_em(symbol=symbol)
    
    # Convert to dict
    info = {}
    for _, row in df.iterrows():
        key = row['item']
        value = row['value']
        info[key] = value
    
    # Extract key fields
    result = {
        "code": symbol,
        "name": info.get('股票简称', 'N/A'),
        "price": float(info.get('最新价', 0)),
        "industry": info.get('行业', 'N/A'),
        "total_shares": float(info.get('总股本', 0)),
        "market_cap": float(info.get('总市值', 0))
    }
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python get_stock_price.py <stock_code>", file=sys.stderr)
        print("Example: python get_stock_price.py 600519", file=sys.stderr)
        sys.exit(1)
    
    symbol = sys.argv[1].strip()
    
    # Remove any exchange prefix if present
    symbol = symbol.replace('sh', '').replace('sz', '')
    
    try:
        info = get_stock_info(symbol)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e), "code": symbol}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
