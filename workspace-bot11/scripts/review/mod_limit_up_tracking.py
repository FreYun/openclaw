"""
模块：连板 & 题材前瞻
- 今日涨停股列表
- 连板高度统计（tushare limit_list_d）
- 按题材/行业分组
"""

import logging
import time
import akshare as ak
import pandas as pd
from collections import Counter

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_tushare_pro


def _get_limit_up_threshold(code):
    """根据代码判断涨停阈值"""
    if code.startswith(("30", "68")):
        return 19.8  # 创业板/科创板 20%
    elif code.startswith(("8", "4")):
        return 29.8  # 北交所 30%
    else:
        return 9.8   # 主板 10%


def _fetch_limit_up_ak():
    """akshare 实时行情筛选涨停股"""
    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return []

        limit_ups = []
        for _, row in df.iterrows():
            code = str(row["代码"])
            pct = row["涨跌幅"]
            price = row["最新价"]

            if price == 0:
                continue

            threshold = _get_limit_up_threshold(code)
            if pct >= threshold:
                limit_ups.append({
                    "code": code,
                    "name": row.get("名称", ""),
                    "pct_chg": float(pct),
                    "amount": float(row.get("成交额", 0)) / 1e8,  # 亿
                    "price": float(price),
                })

        return limit_ups
    except Exception as e:
        logging.warning(f"akshare 获取涨停列表失败: {e}")
        return []


def _fetch_limit_list_ts(date_str):
    """tushare 获取涨停列表（含连板信息）"""
    try:
        pro = get_tushare_pro()
        date_fmt = date_str.replace("-", "")

        df = pro.limit_list_d(
            trade_date=date_fmt,
            limit_type="U",  # U=涨停
        )
        time.sleep(0.15)

        if df is None or df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            code = str(row.get("ts_code", ""))
            # up_stat 格式: "连板天数/区间涨停次数" 如 "3/5"
            up_stat = str(row.get("up_stat", "1/1"))
            try:
                consecutive = int(up_stat.split("/")[0])
            except (ValueError, IndexError):
                consecutive = 1

            results.append({
                "ts_code": code,
                "name": row.get("name", ""),
                "close": float(row.get("close", 0)),
                "pct_chg": float(row.get("pct_chg", 0)),
                "fd_amount": float(row.get("fd_amount", 0)),  # 封单金额（万）
                "first_time": str(row.get("first_time", "")),
                "last_time": str(row.get("last_time", "")),
                "open_times": int(row.get("open_times", 0)),  # 打开次数
                "consecutive": consecutive,
                "up_stat": up_stat,
            })

        # 按连板天数降序
        results.sort(key=lambda x: x["consecutive"], reverse=True)
        return results
    except Exception as e:
        logging.warning(f"tushare 获取涨停列表失败: {e}")
        return []


def _analyze_themes(limit_list_ts):
    """分析涨停股的题材分布（简化版：使用行业分类）"""
    if not limit_list_ts:
        return {}

    try:
        pro = get_tushare_pro()
        codes = [item["ts_code"] for item in limit_list_ts]

        # 获取股票行业信息
        basics = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,name,industry",
        )
        time.sleep(0.15)

        if basics is None or basics.empty:
            return {}

        industry_map = dict(zip(basics["ts_code"], basics["industry"]))

        # 统计各行业涨停数
        industries = [industry_map.get(code, "未知") for code in codes]
        counter = Counter(industries)

        return dict(counter.most_common(10))
    except Exception as e:
        logging.warning(f"涨停题材分析失败: {e}")
        return {}


def fetch_limit_up_data(date_str):
    """主函数：获取连板 & 题材前瞻"""
    from datetime import datetime

    # 1. tushare 涨停列表（含连板信息，更丰富）
    limit_list_ts = _fetch_limit_list_ts(date_str)

    # 2. akshare 涨停列表（实时快照，仅当天有效）
    today = datetime.now().strftime("%Y-%m-%d")
    if date_str == today:
        limit_list_ak = _fetch_limit_up_ak()
    else:
        limit_list_ak = []

    # 3. 连板高度统计
    max_consecutive = 0
    consecutive_dist = {}  # {板数: 数量}
    if limit_list_ts:
        for item in limit_list_ts:
            c = item["consecutive"]
            if c > max_consecutive:
                max_consecutive = c
            consecutive_dist[c] = consecutive_dist.get(c, 0) + 1

    # 4. 题材分布
    theme_dist = _analyze_themes(limit_list_ts)

    return {
        "limit_up_count_ak": len(limit_list_ak),
        "limit_up_count_ts": len(limit_list_ts),
        "max_consecutive": max_consecutive,
        "consecutive_dist": consecutive_dist,  # {1: 30, 2: 5, 3: 2, ...}
        "theme_dist": theme_dist,  # {"半导体": 5, "医药": 3, ...}
        "top_consecutive": limit_list_ts[:10] if limit_list_ts else [],  # 连板最高的前10
        "total_limit_up": max(len(limit_list_ak), len(limit_list_ts)),
    }
