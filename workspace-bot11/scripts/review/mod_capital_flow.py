"""
模块：资金与流动性
- 北向资金净流入（tushare 为主，akshare 当日延迟故仅做备用）
- 国债收益率
"""

import logging
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_tushare_pro


def _fetch_northbound_ak(date_str):
    """akshare 获取北向资金 (沪股通+深股通)"""
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is None or df.empty:
            return None

        # 筛选目标日期的北向数据
        df["交易日"] = pd.to_datetime(df["交易日"]).dt.strftime("%Y-%m-%d")
        day_df = df[(df["交易日"] == date_str) & (df["资金方向"] == "北向")]

        if day_df.empty:
            logging.warning(f"akshare: 北向资金无 {date_str} 数据")
            return None

        # 沪股通 + 深股通 净买额合计
        net_flow = day_df["成交净买额"].sum()
        return {"net_flow": round(float(net_flow), 2), "source": "akshare"}
    except Exception as e:
        logging.warning(f"akshare 获取北向资金失败: {e}")
        return None


def _fetch_northbound_ts(date_str):
    """tushare 获取北向资金（交叉验证）"""
    try:
        pro = get_tushare_pro()
        date_fmt = date_str.replace("-", "")
        df = pro.moneyflow_hsgt(trade_date=date_fmt)
        if df is not None and len(df) > 0:
            r = df.iloc[0]
            # north_money 单位为万元
            north = float(r.get("north_money", 0)) / 10000  # 万→亿
            return {"net_flow": round(north, 2), "source": "tushare"}
        return None
    except Exception as e:
        logging.warning(f"tushare 获取北向资金失败: {e}")
        return None



def _fetch_bond_yield_ak(date_str):
    """akshare 获取国债收益率"""
    try:
        # bond_china_yield 需要日期区间不超过1年
        end_date = date_str.replace("-", "")
        start_dt = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=7)
        start_date = start_dt.strftime("%Y%m%d")

        df = ak.bond_china_yield(start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return None

        # 筛选10年期国债
        target = None
        for _, row in df.iterrows():
            curve_name = str(row.get("曲线名称", ""))
            if "国债" in curve_name and "10" in str(row.get("期限", "")):
                target = row
                break

        if target is None:
            # 尝试其他筛选方式
            cn_bond = df[df.apply(
                lambda r: "国债" in str(r.get("曲线名称", "")) if "曲线名称" in r.index else False,
                axis=1
            )]
            if not cn_bond.empty:
                target = cn_bond.iloc[-1]

        if target is not None:
            yield_10y = float(target.get("10年", target.get("收益率", 0)))
            return {"yield_10y": round(yield_10y, 4)}

        return None
    except Exception as e:
        logging.warning(f"akshare 获取国债收益率失败: {e}")
        return None


def fetch_capital_flow(date_str):
    """主函数：获取资金与流动性数据"""
    # 1. 北向资金
    northbound_ak = _fetch_northbound_ak(date_str)
    northbound_ts = _fetch_northbound_ts(date_str)

    # 选择主数据源（tushare 更可靠）
    northbound = northbound_ts or northbound_ak

    # 交叉验证
    nb_validation = None
    if northbound_ak and northbound_ts:
        ak_val = northbound_ak["net_flow"]
        ts_val = northbound_ts["net_flow"]
        if abs(ts_val) > 0.01:
            diff_pct = abs(ak_val - ts_val) / abs(ts_val) * 100
        else:
            diff_pct = 0
        nb_validation = {
            "akshare": ak_val,
            "tushare": ts_val,
            "diff_pct": round(diff_pct, 2),
            "ok": diff_pct < 5,
        }

    # 2. 国债收益率
    bond_yield = _fetch_bond_yield_ak(date_str)

    return {
        "northbound": northbound,
        "margin": None,
        "bond_yield": bond_yield,
        "_validation": {"northbound": nb_validation} if nb_validation else {},
    }
