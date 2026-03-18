"""
模块：股债收益比 (Equity Risk Premium)
- 沪深300 PE → 盈利收益率 (1/PE)
- 10年期国债收益率
- ERP = 盈利收益率 - 国债收益率
- tushare 获取 PE / akshare 获取国债收益率
"""

import logging
import time
import json
import os
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_tushare_pro

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "erp_cache.json")


def _fetch_index_pe_ts(date_str):
    """tushare 获取沪深300 PE"""
    try:
        pro = get_tushare_pro()
        date_fmt = date_str.replace("-", "")
        df = pro.index_dailybasic(
            ts_code="000300.SH",
            start_date=date_fmt,
            end_date=date_fmt,
            fields="ts_code,trade_date,pe,pe_ttm,turnover_rate",
        )
        if df is not None and len(df) > 0:
            r = df.iloc[0]
            pe_ttm = float(r.get("pe_ttm", 0))
            return {
                "pe_ttm": round(pe_ttm, 2),
                "earnings_yield": round(1 / pe_ttm * 100, 4) if pe_ttm > 0 else 0,
            }
        return None
    except Exception as e:
        logging.warning(f"tushare 获取沪深300 PE 失败: {e}")
        return None


def _fetch_bond_yield(date_str):
    """获取10年期国债收益率"""
    try:
        end_date = date_str.replace("-", "")
        start_dt = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=7)
        start_date = start_dt.strftime("%Y%m%d")

        df = ak.bond_china_yield(start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return None

        # 筛选国债到期收益率
        for _, row in df.iterrows():
            curve = str(row.get("曲线名称", ""))
            if "国债" in curve:
                val = row.get("10年", None)
                if val is not None:
                    return float(val)
        return None
    except Exception as e:
        logging.warning(f"获取国债收益率失败: {e}")
        return None


def _load_erp_history():
    """加载 ERP 历史缓存"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_erp_history(data):
    """保存 ERP 历史缓存"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _calc_percentile(current, history_values):
    """计算当前值在历史中的分位"""
    if not history_values or current is None:
        return None
    below = sum(1 for v in history_values if v <= current)
    return round(below / len(history_values) * 100, 1)


def _fetch_erp_history_ts(date_str, days=750):
    """获取 ERP 历史数据用于分位计算"""
    cache = _load_erp_history()

    # 如果缓存数据足够新（距今 < 3天），直接使用
    if cache.get("last_update"):
        last = datetime.strptime(cache["last_update"], "%Y-%m-%d")
        now = datetime.strptime(date_str, "%Y-%m-%d")
        if (now - last).days < 3 and len(cache.get("erp_values", [])) > 100:
            return cache.get("erp_values", [])

    # 否则拉取历史数据
    try:
        pro = get_tushare_pro()
        end_fmt = date_str.replace("-", "")
        start_dt = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=days * 1.5)
        start_fmt = start_dt.strftime("%Y%m%d")

        logging.info(f"拉取 ERP 历史数据 {start_fmt} ~ {end_fmt}")
        df = pro.index_dailybasic(
            ts_code="000300.SH",
            start_date=start_fmt,
            end_date=end_fmt,
            fields="trade_date,pe_ttm",
        )
        time.sleep(0.15)

        if df is None or df.empty:
            return cache.get("erp_values", [])

        # 计算盈利收益率
        df = df[df["pe_ttm"] > 0].copy()
        df["earnings_yield"] = 1 / df["pe_ttm"] * 100

        erp_values = df["earnings_yield"].tolist()

        # 保存缓存
        cache["erp_values"] = erp_values
        cache["last_update"] = date_str
        _save_erp_history(cache)

        return erp_values
    except Exception as e:
        logging.warning(f"获取 ERP 历史失败: {e}")
        return cache.get("erp_values", [])


def fetch_erp(date_str):
    """主函数：计算股债收益比"""
    # 1. 沪深300 PE
    pe_data = _fetch_index_pe_ts(date_str)

    # 2. 国债收益率
    bond_yield_10y = _fetch_bond_yield(date_str)

    # 3. 计算 ERP
    erp = None
    if pe_data and pe_data.get("earnings_yield") and bond_yield_10y:
        erp = round(pe_data["earnings_yield"] - bond_yield_10y, 4)

    # 4. 历史分位
    erp_history = _fetch_erp_history_ts(date_str)
    percentile = None
    if erp is not None:
        percentile = _calc_percentile(erp, erp_history)

    return {
        "csi300_pe": pe_data,
        "bond_yield_10y": bond_yield_10y,
        "erp": erp,
        "erp_percentile": percentile,
    }
