"""
连续一字跌停股票扫描

用法:
    python limit_down_scan.py [start_date] [end_date] [min_days]

参数:
    start_date  起始日期 YYYYMMDD，默认 30 天前
    end_date    截止日期 YYYYMMDD，默认今天
    min_days    最少连续跌停天数，默认 2
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_tushare_pro

from datetime import datetime, timedelta
import time


def is_limit_down(row):
    """判断是否为一字跌停：开盘=收盘=最高=最低 且 跌幅达到板级阈值"""
    code = row["ts_code"]
    pct = row["pct_chg"]
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]

    # 开高低收必须相等（一字板）
    if not (o == h == l == c):
        return False

    prefix = code[:3]
    # 创业板 30xxxx / 科创板 68xxxx → 20% 涨跌幅
    if prefix.startswith("30") or prefix.startswith("68"):
        return pct <= -19.8
    # 北交所 8xxxxx / 4xxxxx → 30% 涨跌幅
    if prefix.startswith("8") or prefix.startswith("4"):
        return pct <= -29.8
    # 主板 / 中小板 → 10% 涨跌幅
    return pct <= -9.8


def code_to_tscode(code_6):
    """6 位纯数字代码 → Tushare 格式 (如 '600036' → '600036.SH')"""
    if code_6.startswith("6"):
        return f"{code_6}.SH"
    elif code_6.startswith(("0", "1", "2", "3")):
        return f"{code_6}.SZ"
    elif code_6.startswith(("4", "8")):
        return f"{code_6}.BJ"
    return f"{code_6}.SZ"


def get_realtime_limit_down():
    """用 akshare 实时行情判断当日一字跌停股票，返回 (跌停集合, 涨跌幅映射)"""
    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    ld_set = set()
    pct_map = {}

    for _, row in df.iterrows():
        code_6 = str(row["代码"])
        ts_code = code_to_tscode(code_6)
        pct = row["涨跌幅"]
        o, h, l, c = row["今开"], row["最高"], row["最低"], row["最新价"]

        # 跳过停牌（价格为 0）
        if c == 0 or o == 0:
            continue

        # 一字板判定：开高低收相等
        if not (o == h == l == c):
            continue

        prefix = code_6[:3]
        if prefix.startswith("30") or prefix.startswith("68"):
            threshold = -19.8
        elif prefix.startswith("8") or prefix.startswith("4"):
            threshold = -29.8
        else:
            threshold = -9.8

        if pct <= threshold:
            ld_set.add(ts_code)
            pct_map[ts_code] = pct

    return ld_set, pct_map


def scan_consecutive_limit_down(start_date, end_date, min_days=2):
    """扫描时间区间内连续一字跌停的股票"""
    pro = get_tushare_pro()
    today_str = datetime.now().strftime("%Y%m%d")
    includes_today = end_date >= today_str

    # 获取交易日历
    cal = pro.trade_cal(
        exchange="SSE", start_date=start_date, end_date=end_date, is_open="1"
    )
    trade_dates = sorted(cal["cal_date"].tolist())

    if not trade_dates:
        print("指定区间内没有交易日")
        return []

    # 如果包含今天且今天是交易日，单独用实时数据处理
    use_realtime_today = includes_today and today_str in trade_dates
    if use_realtime_today:
        trade_dates = [d for d in trade_dates if d != today_str]

    hist_count = len(trade_dates)
    total_count = hist_count + (1 if use_realtime_today else 0)
    print(
        f"扫描区间: {start_date} ~ {end_date}，共 {total_count} 个交易日"
        + (" (含今日实时)" if use_realtime_today else "")
    )

    # 追踪每只股票的连续跌停状态
    # key: ts_code, value: {"start": date, "days": int, "pct_sum": float}
    tracking = {}
    # 已结束的连续跌停记录
    results = []

    for i, date in enumerate(trade_dates):
        print(
            f"\r  拉取 {date} ({i+1}/{total_count})...", end="", flush=True
        )

        try:
            df = pro.daily(trade_date=date)
        except Exception as e:
            print(f"\n  [警告] {date} 拉取失败: {str(e)[:60]}，跳过")
            continue

        if df is None or df.empty:
            continue

        # 当日一字跌停股票集合
        today_ld = set()
        pct_map = {}
        for _, row in df.iterrows():
            if is_limit_down(row):
                today_ld.add(row["ts_code"])
                pct_map[row["ts_code"]] = row["pct_chg"]

        # 更新追踪状态
        # 1) 不在今天跌停列表中的 → 结束追踪，记录结果
        ended = [code for code in tracking if code not in today_ld]
        for code in ended:
            info = tracking.pop(code)
            if info["days"] >= min_days:
                results.append(
                    {
                        "ts_code": code,
                        "days": info["days"],
                        "start_date": info["start"],
                        "end_date": info["last_date"],
                        "total_pct": info["pct_sum"],
                    }
                )

        # 2) 在今天跌停列表中的 → 继续或新增
        for code in today_ld:
            if code in tracking:
                tracking[code]["days"] += 1
                tracking[code]["pct_sum"] += pct_map[code]
                tracking[code]["last_date"] = date
            else:
                tracking[code] = {
                    "start": date,
                    "last_date": date,
                    "days": 1,
                    "pct_sum": pct_map[code],
                }

        # Tushare 限流：每分钟 500 次，保守间隔
        time.sleep(0.15)

    # 如果包含今天，用实时数据做最后一轮判定
    if use_realtime_today:
        print(
            f"\r  拉取实时行情 ({total_count}/{total_count})...",
            end="",
            flush=True,
        )
        try:
            today_ld, pct_map = get_realtime_limit_down()

            # 结束不再跌停的
            ended = [code for code in tracking if code not in today_ld]
            for code in ended:
                info = tracking.pop(code)
                if info["days"] >= min_days:
                    results.append(
                        {
                            "ts_code": code,
                            "days": info["days"],
                            "start_date": info["start"],
                            "end_date": info["last_date"],
                            "total_pct": info["pct_sum"],
                        }
                    )

            # 继续或新增今日仍跌停的
            for code in today_ld:
                if code in tracking:
                    tracking[code]["days"] += 1
                    tracking[code]["pct_sum"] += pct_map[code]
                    tracking[code]["last_date"] = today_str
                else:
                    tracking[code] = {
                        "start": today_str,
                        "last_date": today_str,
                        "days": 1,
                        "pct_sum": pct_map[code],
                    }
        except Exception as e:
            print(f"\n  [警告] 实时行情拉取失败: {str(e)[:60]}，跳过今日")

    # 扫描结束，处理仍在追踪中的（截止日仍在跌停的）
    for code, info in tracking.items():
        if info["days"] >= min_days:
            results.append(
                {
                    "ts_code": code,
                    "days": info["days"],
                    "start_date": info["start"],
                    "end_date": info["last_date"],
                    "total_pct": info["pct_sum"],
                }
            )

    print()  # 换行

    # 按连续天数降序排列
    results.sort(key=lambda x: x["days"], reverse=True)

    # 补充股票名称
    if results:
        try:
            basics = pro.stock_basic(
                exchange="", list_status="L", fields="ts_code,name"
            )
            # 也拉取退市/暂停上市的
            basics_d = pro.stock_basic(
                exchange="", list_status="D", fields="ts_code,name"
            )
            basics_p = pro.stock_basic(
                exchange="", list_status="P", fields="ts_code,name"
            )
            import pandas as pd

            all_basics = pd.concat([basics, basics_d, basics_p], ignore_index=True)
            name_map = dict(zip(all_basics["ts_code"], all_basics["name"]))
        except Exception:
            name_map = {}

        for r in results:
            r["name"] = name_map.get(r["ts_code"], "")

    return results


def format_date(d):
    """YYYYMMDD → YYYY-MM-DD"""
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def main():
    today = datetime.now().strftime("%Y%m%d")
    default_start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    start_date = sys.argv[1] if len(sys.argv) > 1 else default_start
    end_date = sys.argv[2] if len(sys.argv) > 2 else today
    min_days = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    print("=" * 70)
    print("  连续一字跌停扫描")
    print(f"  时间区间: {format_date(start_date)} ~ {format_date(end_date)}")
    print(f"  最低连续天数: {min_days}")
    print("=" * 70)

    results = scan_consecutive_limit_down(start_date, end_date, min_days)

    if not results:
        print(f"\n未发现连续 {min_days} 天以上一字跌停的股票")
        return

    print(f"\n共发现 {len(results)} 条连续一字跌停记录:\n")
    print(
        f"{'股票代码':<12}{'股票名称':<10}{'连续天数':>8}{'起始日期':>14}{'截止日期':>14}{'累计跌幅':>10}"
    )
    print("-" * 70)

    for r in results:
        print(
            f"{r['ts_code']:<12}{r.get('name',''):<10}{r['days']:>6}天"
            f"    {format_date(r['start_date'])}    {format_date(r['end_date'])}"
            f"    {r['total_pct']:>+.2f}%"
        )

    print("-" * 70)
    print(f"共 {len(results)} 条记录")


if __name__ == "__main__":
    main()
