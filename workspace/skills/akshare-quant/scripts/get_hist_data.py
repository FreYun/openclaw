#!/usr/bin/env python3
"""
Get historical stock data with automatic error handling.

Usage:
    python get_hist_data.py 600519 --days 30
    python get_hist_data.py 000001 --start 20250201 --end 20250227
    python get_hist_data.py 600519 --period weekly

Arguments:
    symbol          Stock code (e.g., 600519)
    --days N        Get last N days (default: 30)
    --start DATE    Start date (YYYYMMDD)
    --end DATE      End date (YYYYMMDD)
    --period        daily/weekly/monthly (default: daily)
    --adjust        qfq/hfq/none (default: qfq - 前复权)

Output: JSON array of OHLCV data
"""

import sys
import json
import argparse
from datetime import datetime, timedelta, date
import akshare as ak


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)


def get_hist_data(symbol: str, start_date: str, end_date: str, period: str = 'daily', adjust: str = 'qfq'):
    """Get historical data with error handling."""
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust
    )
    
    # Rename columns to English for easier processing
    column_map = {
        '日期': 'date',
        '股票代码': 'code',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change',
        '换手率': 'turnover'
    }
    
    df = df.rename(columns=column_map)
    
    # Convert to records
    records = df.to_dict(orient='records')
    return records


def main():
    parser = argparse.ArgumentParser(description='Get historical stock data')
    parser.add_argument('symbol', help='Stock code (e.g., 600519)')
    parser.add_argument('--days', type=int, default=30, help='Number of days to fetch')
    parser.add_argument('--start', help='Start date (YYYYMMDD)')
    parser.add_argument('--end', help='End date (YYYYMMDD)')
    parser.add_argument('--period', default='daily', choices=['daily', 'weekly', 'monthly'])
    parser.add_argument('--adjust', default='qfq', choices=['qfq', 'hfq', 'none'])
    
    args = parser.parse_args()
    
    symbol = args.symbol.replace('sh', '').replace('sz', '')
    
    # Calculate dates if not provided
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        end = datetime.now()
        start = end - timedelta(days=args.days)
        end_date = end.strftime('%Y%m%d')
        start_date = start.strftime('%Y%m%d')
    
    adjust_map = {'none': ''}
    adjust = adjust_map.get(args.adjust, args.adjust)
    
    try:
        data = get_hist_data(symbol, start_date, end_date, args.period, adjust)
        result = {
            "symbol": symbol,
            "period": args.period,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(data),
            "data": data
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, cls=DateEncoder))
    except Exception as e:
        error_msg = {"error": str(e), "symbol": symbol}
        print(json.dumps(error_msg, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
