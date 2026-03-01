#!/usr/bin/env python3
"""
Batch query multiple stocks efficiently.

Usage:
    python batch_query.py 600519 000001 000333
    python batch_query.py 600519 000001 --field price

Arguments:
    codes           One or more stock codes
    --field         Field to extract: price, name, industry, all (default: all)

Output: JSON object with results for each stock
"""

import sys
import json
import argparse
import akshare as ak


def get_stock_basic(symbol: str) -> dict:
    """Get basic info for a single stock."""
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        info = {row['item']: row['value'] for _, row in df.iterrows()}
        return {
            "code": symbol,
            "name": info.get('股票简称', 'N/A'),
            "price": float(info.get('最新价', 0)) if info.get('最新价') else None,
            "industry": info.get('行业', 'N/A'),
            "market_cap": float(info.get('总市值', 0)) if info.get('总市值') else None,
            "success": True
        }
    except Exception as e:
        return {
            "code": symbol,
            "error": str(e),
            "success": False
        }


def main():
    parser = argparse.ArgumentParser(description='Batch query stock information')
    parser.add_argument('codes', nargs='+', help='Stock codes to query')
    parser.add_argument('--field', default='all', 
                       choices=['all', 'price', 'name', 'industry', 'market_cap'])
    
    args = parser.parse_args()
    
    results = []
    for code in args.codes:
        code = code.replace('sh', '').replace('sz', '').strip()
        info = get_stock_basic(code)
        
        # Filter fields if requested
        if args.field != 'all' and info.get('success'):
            filtered = {
                "code": info['code'],
                args.field: info.get(args.field, 'N/A')
            }
            results.append(filtered)
        else:
            results.append(info)
    
    output = {
        "query_count": len(args.codes),
        "success_count": sum(1 for r in results if r.get('success')),
        "results": results
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
