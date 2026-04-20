#!/usr/bin/env python3
"""S5 战法所需外部数据的 cron 预热脚本 (self-contained).

职责:
  把 S5 select.py 会用到的"所有"外部数据灌进 market.db, 让 skill 运行时纯 DB read.

预热写入的表:
  1. limit_up_pool         — T 日涨停池 (akshare)
  2. hot_industries_daily  — top 3 热门行业 (从涨停池派生)
  3. s5_daily_universe     — S5 选股 universe (top 3 行业成分 + 涨停池)
  4. klines_cache          — universe 近 35 日 K 线 (research-mcp 批量)

说明:
  本脚本不依赖 s5 skill 内部模块 (data_fetcher 等), 走 akshare + research-mcp 直连,
  保持"写路径 self-contained, 读路径在 s5 skill"的分工.

用法:
  python3 s5-prewarm.py                 # 今天 (本地时区)
  python3 s5-prewarm.py --date 2026-04-16

cron 集成: daily-regime-pipeline.sh Step 3.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date as date_cls
from typing import Optional

import requests

# 共享 DB 模块 (lazy)
_STRATEGY_LIB_DIR = "/home/rooot/.openclaw/workspace/skills/strategy/_lib"
if _STRATEGY_LIB_DIR not in sys.path:
    sys.path.insert(0, _STRATEGY_LIB_DIR)
import db as market_db  # noqa: E402


# --------------------------------------------------------------------------- #
# akshare / research-mcp lazy import + HTTP 封装
# --------------------------------------------------------------------------- #

_ak_module = None


def _ak():
    global _ak_module
    if _ak_module is None:
        import akshare as ak
        _ak_module = ak
    return _ak_module


RESEARCH_MCP_URL = "http://research-mcp.jijinmima.cn/mcp"


def research_mcp_call(tool_name: str, arguments: dict, timeout: float = 60) -> dict:
    """直接 HTTP POST 到 research-mcp, 解析 SSE, 返回工具结果 dict."""
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1_000_000,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    r = requests.post(RESEARCH_MCP_URL, json=body, headers=headers, timeout=timeout)
    r.encoding = "utf-8"
    if r.status_code != 200:
        raise RuntimeError(f"research-mcp HTTP {r.status_code}: {r.text[:200]}")

    events = []
    for chunk in r.text.split("\n\n"):
        for line in chunk.split("\n"):
            if line.startswith("data: "):
                events.append(line[6:])
    if not events:
        raise RuntimeError(f"research-mcp 空响应: {r.text[:200]}")

    resp = json.loads(events[0])
    if "error" in resp:
        raise RuntimeError(f"research-mcp 错误: {resp['error']}")
    if "result" not in resp:
        raise RuntimeError(f"research-mcp 响应格式异常: {resp}")
    text = resp["result"]["content"][0]["text"]
    return json.loads(text)


# --------------------------------------------------------------------------- #
# Step 1: limit_up_pool
# --------------------------------------------------------------------------- #


def write_limit_up_pool(date_str: str, df) -> int:
    """T 日涨停池 → market.db.limit_up_pool."""
    conn = market_db.get_market_db()
    try:
        n = 0
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT OR REPLACE INTO limit_up_pool (
                    date, code, name, industry, pct_chg, streak,
                    close, amount, market_cap, turnover_rate,
                    seal_amount, first_seal_time, last_seal_time, blast_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date_str,
                    str(row.get("代码", "")).zfill(6),
                    row.get("名称"),
                    row.get("所属行业"),
                    float(row.get("涨跌幅", 0) or 0),
                    int(row.get("连板数", 0) or 0),
                    float(row.get("最新价", 0) or 0),
                    float(row.get("成交额", 0) or 0),
                    float(row.get("流通市值", 0) or 0),
                    float(row.get("换手率", 0) or 0),
                    float(row.get("封板资金", 0) or 0),
                    str(row.get("首次封板时间", "")),
                    str(row.get("最后封板时间", "")),
                    int(row.get("炸板次数", 0) or 0),
                ),
            )
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Step 2: hot_industries_daily
# --------------------------------------------------------------------------- #


def derive_hot_industries(df, top_n: int = 3) -> list:
    """从涨停池派生 top N 热门行业."""
    if df is None or df.empty:
        return []
    counts = df["所属行业"].fillna("未知").value_counts()
    return [
        {"name": name, "limit_count": int(cnt)}
        for name, cnt in counts.head(top_n).items()
    ]


def write_hot_industries(date_str: str, hot: list):
    """热门行业 → hot_industries_daily."""
    conn = market_db.get_market_db()
    try:
        conn.execute("DELETE FROM hot_industries_daily WHERE date = ?", (date_str,))
        for rank, h in enumerate(hot, start=1):
            conn.execute(
                """
                INSERT INTO hot_industries_daily (date, rank, industry, limit_count)
                VALUES (?, ?, ?, ?)
                """,
                (date_str, rank, h["name"], h["limit_count"]),
            )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Step 3: s5_daily_universe (top 3 行业成分 + 涨停池股)
# --------------------------------------------------------------------------- #


def fetch_industry_constituents(industry_name: str) -> list:
    try:
        df = _ak().stock_board_industry_cons_em(symbol=industry_name)
        if df is None or df.empty:
            return []
        return df["代码"].astype(str).str.zfill(6).tolist()
    except Exception as e:
        logging.warning(f"行业 {industry_name} 成分股拉取失败: {e}")
        return []


def write_universe(date_str: str, hot: list, zt_df) -> int:
    """计算 universe 并写 s5_daily_universe. 返回去重后的 code 数."""
    code_to_industry = {}

    # 热门行业成分
    for h in hot:
        cons = fetch_industry_constituents(h["name"])
        for c in cons:
            code_to_industry.setdefault(c, h["name"])

    # 涨停池本身
    for _, row in zt_df.iterrows():
        c = str(row["代码"]).zfill(6)
        code_to_industry.setdefault(c, row.get("所属行业", "未知"))

    conn = market_db.get_market_db()
    try:
        conn.execute("DELETE FROM s5_daily_universe WHERE date = ?", (date_str,))
        for code, industry in code_to_industry.items():
            conn.execute(
                "INSERT INTO s5_daily_universe (date, code, industry) VALUES (?, ?, ?)",
                (date_str, code, industry),
            )
        conn.commit()
    finally:
        conn.close()
    return len(code_to_industry)


# --------------------------------------------------------------------------- #
# Step 4: klines_cache
# --------------------------------------------------------------------------- #


def _parse_kline_row(row: list, cols: list) -> dict:
    def _g(name, default=None):
        if name in cols:
            return row[cols.index(name)]
        return default

    def _safe_float(v, default=0.0):
        try:
            f = float(v) if v is not None else default
            return default if f != f else f
        except (TypeError, ValueError):
            return default

    def _safe_int(v, default=0):
        try:
            f = float(v) if v is not None else default
            if f != f:
                return default
            return int(f)
        except (TypeError, ValueError):
            return default

    return {
        "date": str(_g("交易日期", "")),
        "open": _safe_float(_g("开盘", 0)),
        "high": _safe_float(_g("最高", 0)),
        "low": _safe_float(_g("最低", 0)),
        "close": _safe_float(_g("收盘", 0)),
        "pct_chg": _safe_float(_g("涨跌幅", 0)),
        "volume": _safe_float(_g("成交量", 0)),
        "amount": _safe_float(_g("成交额", 0)),
        "is_limit_up": _g("是否涨停") == "是",
        "is_limit_down": _g("是否跌停") == "是",
        "limit_up_streak": _safe_int(_g("连续涨停天数", 0)),
        "limit_down_streak": _safe_int(_g("连续跌停天数", 0)),
    }


def write_klines_cache(klines_map: dict) -> int:
    conn = market_db.get_market_db()
    try:
        n = 0
        for code, bars in klines_map.items():
            for b in bars:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO klines_cache (
                        code, date, open, high, low, close, pct_chg, volume, amount,
                        is_limit_up, is_limit_down, limit_up_streak, limit_down_streak
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code, b["date"],
                        b["open"], b["high"], b["low"], b["close"],
                        b["pct_chg"], b["volume"], b["amount"],
                        1 if b["is_limit_up"] else 0,
                        1 if b["is_limit_down"] else 0,
                        b["limit_up_streak"], b["limit_down_streak"],
                    ),
                )
                n += 1
        conn.commit()
        return n
    finally:
        conn.close()


def fetch_klines_batch(codes: list, start_yyyymmdd: str, end_yyyymmdd: str, batch_size: int = 200) -> dict:
    """批量拉 K 线 (research-mcp HTTP). 返回 {code: [bar]}."""
    result = {}
    codes = sorted(set(codes))
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        try:
            payload = research_mcp_call(
                "get_stock_daily_quote",
                {
                    "stock_code": ",".join(batch),
                    "start_date": start_yyyymmdd,
                    "end_date": end_yyyymmdd,
                },
                timeout=150,
            )
        except Exception as e:
            logging.warning(f"批量 K 线拉取失败 (batch {i//batch_size}): {e}")
            continue

        if not payload.get("success"):
            logging.warning(f"K 线 payload 不成功: {payload.get('message', '')[:200]}")
            continue

        for code, info in payload.get("data", {}).items():
            cols = info.get("columns", [])
            rows = info.get("data", [])
            bars = [_parse_kline_row(row, cols) for row in rows]
            bars.sort(key=lambda b: b["date"])
            result[code] = bars
    return result


# --------------------------------------------------------------------------- #
# 交易日历
# --------------------------------------------------------------------------- #


def shift_trading_days(date_str: str, n_days: int) -> str:
    """date_str ± n 交易日. akshare 日历."""
    from datetime import datetime, timedelta

    try:
        cal_df = _ak().tool_trade_date_hist_sina()
        cal = sorted(d.strftime("%Y-%m-%d") for d in cal_df["trade_date"])
        try:
            idx = cal.index(date_str)
        except ValueError:
            idx = 0
            for i, d in enumerate(cal):
                if d >= date_str:
                    idx = i
                    break
        target = idx + n_days
        if 0 <= target < len(cal):
            return cal[target]
    except Exception as e:
        logging.warning(f"交易日历失败 ({date_str} {n_days:+d}): {e}, 用日历日估算")

    # fallback
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d + timedelta(days=int(n_days * 1.4))).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #


def prewarm(date_str: str) -> int:
    market_db.init_market_db()

    logging.info(f"===== S5 prewarm t={date_str} =====")

    # 1. 涨停池 (akshare)
    try:
        df = _ak().stock_zt_pool_em(date=date_str.replace("-", ""))
    except Exception as e:
        logging.warning(f"涨停池拉取失败 ({date_str}): {e}")
        df = None
    if df is None or df.empty:
        logging.warning("T 日涨停池为空, prewarm 提前结束 (非交易日/极端市场)")
        return 0
    n = write_limit_up_pool(date_str, df)
    logging.info(f"[1/4] limit_up_pool: {n} 行")

    # 2. 派生热门行业
    hot = derive_hot_industries(df, top_n=3)
    if not hot:
        logging.warning("热门行业为空, 跳过 universe/K线 预热")
        return 0
    write_hot_industries(date_str, hot)
    logging.info(f"[2/4] hot_industries_daily: {[h['name'] for h in hot]}")

    # 3. 计算 + 写 universe
    universe_size = write_universe(date_str, hot, df)
    logging.info(f"[3/4] s5_daily_universe: {universe_size} 只")

    # 4. K 线批量
    start = shift_trading_days(date_str, -35).replace("-", "")
    end = date_str.replace("-", "")
    codes = [r["code"] for r in market_db.get_market_db().execute(
        "SELECT code FROM s5_daily_universe WHERE date = ?", (date_str,)
    ).fetchall()]
    logging.info(f"[4/4] K 线 {start}~{end}: {len(codes)} 只 → research-mcp")
    klines_map = fetch_klines_batch(codes, start, end)
    n_bars = write_klines_cache(klines_map)
    logging.info(f"  写 cache: {len(klines_map)} 只, 共 {n_bars} 行 (缺失 {len(codes) - len(klines_map)} 只, 回测时兜底或重跑)")

    logging.info("===== prewarm 完成 =====")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--date",
        default=date_cls.today().strftime("%Y-%m-%d"),
        help="T 日 YYYY-MM-DD, 默认本地今日",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return prewarm(args.date)


if __name__ == "__main__":
    sys.exit(main())
