"""S5 数据拉取层 — 混合 akshare + research-mcp HTTP

数据源分工:
  - akshare:    涨停池 (确定 T 日热门行业)、行业成分股、盘中分时
  - research-mcp HTTP:  批量 K 线 (一次 200 只股 35 天 ≈ 3 秒)

缓存层 (market.db):
  - limit_up_pool:  涨停池 (akshare 2-3 周窗口过期后的永久存档)
  - klines_cache:   K 线 (按 code+date 缓存, 避免重复拉)
  - hot_industries_daily: 热门行业 (从涨停池聚合)

研究结果详见 references/strategy.md.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Optional

import requests

# akshare 在使用时 lazy import (启动 1-2 秒)
_ak_module = None

# 共享 db 模块 (按需 import, 避免单元测试时强制依赖)
_db_module = None


def _db():
    global _db_module
    if _db_module is None:
        _here = os.path.dirname(os.path.abspath(__file__))
        _strategy_root = os.path.dirname(os.path.dirname(_here))
        _lib_dir = os.path.join(_strategy_root, "_lib")
        if _lib_dir not in sys.path:
            sys.path.insert(0, _lib_dir)
        import db as _d
        _db_module = _d
        # 首次使用时确保 schema 存在
        _d.init_market_db()
    return _db_module


def _ak():
    global _ak_module
    if _ak_module is None:
        import akshare as ak
        _ak_module = ak
    return _ak_module


# --------------------------------------------------------------------------- #
# research-mcp HTTP 客户端 (无状态, 一次性 tools/call)
# --------------------------------------------------------------------------- #


RESEARCH_MCP_URL = "http://research-mcp.jijinmima.cn/mcp"


def _research_mcp_call(tool_name: str, arguments: dict, timeout: float = 60) -> dict:
    """直接 HTTP POST 到 research-mcp, 解析 SSE, 返回工具结果 dict。

    绕开 mcporter CLI 的 ~60KB 输出截断。

    Returns:
        工具返回的 payload (已 JSON 解析). 失败抛 RuntimeError。
    """
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

    # 解析 SSE: 每帧以 'data: ' 开头, 帧之间用空行分隔
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
# 1. 涨停池 (akshare)
# --------------------------------------------------------------------------- #


def fetch_zt_pool(date_str: str, use_cache: bool = True):
    """T 日涨停股池, 返回 DataFrame。失败/空返 None。

    date_str: 'YYYY-MM-DD'

    缓存路径:
      1. 先查 market.db.limit_up_pool, 命中直接返
      2. miss → 调 akshare → 写 cache → 返
    """
    if use_cache:
        cached_df = _read_zt_pool_cache(date_str)
        if cached_df is not None:
            logging.debug(f"涨停池命中 cache: {date_str} ({len(cached_df)} 行)")
            return cached_df

    try:
        date_fmt = date_str.replace("-", "")
        df = _ak().stock_zt_pool_em(date=date_fmt)
        if df is None or df.empty:
            return None
    except Exception as e:
        logging.warning(f"涨停池拉取失败 ({date_str}): {e}")
        return None

    if use_cache:
        _write_zt_pool_cache(date_str, df)
    return df


def _read_zt_pool_cache(date_str: str):
    """从 market.db.limit_up_pool 读, 返回 DataFrame 或 None。"""
    try:
        import pandas as pd
        conn = _db().get_market_db()
        try:
            rows = conn.execute(
                """
                SELECT code AS 代码, name AS 名称, industry AS 所属行业,
                       pct_chg AS 涨跌幅, streak AS 连板数,
                       close AS 最新价, amount AS 成交额,
                       market_cap AS 流通市值, turnover_rate AS 换手率,
                       seal_amount AS 封板资金, first_seal_time AS 首次封板时间,
                       last_seal_time AS 最后封板时间, blast_count AS 炸板次数
                FROM limit_up_pool WHERE date = ?
                ORDER BY streak DESC, code
                """,
                (date_str,),
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            return None
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        logging.warning(f"涨停池 cache 读失败 ({date_str}): {e}")
        return None


def _write_zt_pool_cache(date_str: str, df):
    """写 market.db.limit_up_pool。"""
    try:
        conn = _db().get_market_db()
        try:
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
            conn.commit()
        finally:
            conn.close()
        logging.info(f"涨停池写 cache: {date_str} ({len(df)} 行)")
    except Exception as e:
        logging.warning(f"涨停池 cache 写失败 ({date_str}): {e}")


def derive_hot_industries(zt_df, top_n: int = 3) -> list:
    """从涨停池聚合 T 日热门行业。

    返回: [{"name": str, "limit_count": int}], 按涨停家数降序, 取 top_n
    """
    if zt_df is None or zt_df.empty:
        return []
    counts = zt_df["所属行业"].fillna("未知").value_counts()
    return [
        {"name": name, "limit_count": int(cnt)}
        for name, cnt in counts.head(top_n).items()
    ]


# --------------------------------------------------------------------------- #
# 2. 行业成分股 (akshare)
# --------------------------------------------------------------------------- #


def fetch_industry_constituents(industry_name: str) -> list:
    """拉某东财行业的成分股代码列表。

    Args:
        industry_name: 如 "电池", "光伏设备"

    Returns:
        股票 6 位代码列表, 失败返 []
    """
    try:
        df = _ak().stock_board_industry_cons_em(symbol=industry_name)
        if df is None or df.empty:
            return []
        # akshare 返回字段: 序号 代码 名称 ...
        codes = df["代码"].astype(str).str.zfill(6).tolist()
        return codes
    except Exception as e:
        logging.warning(f"行业 {industry_name} 成分股拉取失败: {e}")
        return []


# --------------------------------------------------------------------------- #
# 3. K 线批量 (research-mcp HTTP)
# --------------------------------------------------------------------------- #


def fetch_klines_batch(
    codes: list,
    start_date: str,
    end_date: str,
    batch_size: int = 200,
    use_cache: bool = True,
) -> dict:
    """批量拉 K 线, 返回 {code: [bar, ...]}。

    每个 bar 字段: {date, open, high, low, close, pct_chg, volume, amount,
                   is_limit_up, is_limit_down, limit_up_streak, limit_down_streak}

    缓存策略:
      1. 先查 market.db.klines_cache 看 (code, date) 范围
      2. 对每个 code, 若已 cache 数据覆盖了请求的全部交易日, 跳过 fetch
      3. 否则把 missing codes 发给 research-mcp, 写回 cache

    判断"覆盖完整"是基于 date 范围内的 bar 数量是否等于该日期段内的 cache 行数。
    简化版: 如果 cache 中有 (code, start..end) 范围内任意一行, 视为该 code 已 cache,
    否则归入 missing。这个简化对"按日重跑同一日期"完全足够;
    对跨日期范围的扩展查询会有 false-cache, 但 v1 不处理。

    Args:
        codes: 6 位代码列表
        start_date, end_date: YYYYMMDD (内部转 YYYY-MM-DD 与 cache 对齐)
        batch_size: research-mcp 一次最多 200 只
        use_cache: 关掉则强制全部走网络
    """
    result = {}
    if not codes:
        return result

    # 去重
    codes = sorted(set(codes))

    # 1. 查缓存
    if use_cache:
        cached = _read_klines_cache(codes, start_date, end_date)
        for code, bars in cached.items():
            result[code] = bars
        missing = [c for c in codes if c not in cached]
        if missing:
            logging.info(
                f"K 线 cache: {len(cached)}/{len(codes)} 命中, {len(missing)} 走网络"
            )
        else:
            logging.info(f"K 线 cache 全部命中 ({len(codes)} 只)")
            return result
    else:
        missing = list(codes)

    # 2. 走网络拉 missing
    fresh = {}
    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        try:
            payload = _research_mcp_call(
                "get_stock_daily_quote",
                {
                    "stock_code": ",".join(batch),
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        except Exception as e:
            logging.warning(f"批量 K 线拉取失败 (batch {i//batch_size}): {e}")
            continue

        if not payload.get("success"):
            logging.warning(f"K 线 payload 不成功: {payload.get('message', '')[:200]}")
            continue

        data = payload.get("data", {})
        for code, info in data.items():
            cols = info.get("columns", [])
            rows = info.get("data", [])
            bars = [_parse_kline_row(row, cols) for row in rows]
            bars.sort(key=lambda b: b["date"])
            fresh[code] = bars

    # 3. 写 cache
    if use_cache and fresh:
        _write_klines_cache(fresh)

    result.update(fresh)
    return result


def _read_klines_cache(codes: list, start_date_yyyymmdd: str, end_date_yyyymmdd: str) -> dict:
    """从 market.db.klines_cache 读, 返回 {code: [bar, ...]}。

    只返回有 cache 数据的 code, 没数据的 code 不在返回 dict 中。
    """
    try:
        conn = _db().get_market_db()
        try:
            # date 列存储格式: YYYY-MM-DD
            start_iso = f"{start_date_yyyymmdd[:4]}-{start_date_yyyymmdd[4:6]}-{start_date_yyyymmdd[6:8]}"
            end_iso = f"{end_date_yyyymmdd[:4]}-{end_date_yyyymmdd[4:6]}-{end_date_yyyymmdd[6:8]}"
            placeholders = ",".join("?" * len(codes))
            rows = conn.execute(
                f"""
                SELECT code, date, open, high, low, close, pct_chg, volume, amount,
                       is_limit_up, is_limit_down, limit_up_streak, limit_down_streak
                FROM klines_cache
                WHERE code IN ({placeholders}) AND date >= ? AND date <= ?
                ORDER BY code, date
                """,
                (*codes, start_iso, end_iso),
            ).fetchall()
        finally:
            conn.close()
        result = {}
        for r in rows:
            code = r["code"]
            bar = {
                "date": r["date"],
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "pct_chg": r["pct_chg"],
                "volume": r["volume"],
                "amount": r["amount"],
                "is_limit_up": bool(r["is_limit_up"]),
                "is_limit_down": bool(r["is_limit_down"]),
                "limit_up_streak": r["limit_up_streak"] or 0,
                "limit_down_streak": r["limit_down_streak"] or 0,
            }
            result.setdefault(code, []).append(bar)
        return result
    except Exception as e:
        logging.warning(f"K 线 cache 读失败: {e}")
        return {}


def _write_klines_cache(klines_map: dict):
    """写 market.db.klines_cache。"""
    try:
        conn = _db().get_market_db()
        try:
            count = 0
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
                            code,
                            b["date"],
                            b["open"], b["high"], b["low"], b["close"],
                            b["pct_chg"], b["volume"], b["amount"],
                            1 if b["is_limit_up"] else 0,
                            1 if b["is_limit_down"] else 0,
                            b["limit_up_streak"], b["limit_down_streak"],
                        ),
                    )
                    count += 1
            conn.commit()
            logging.info(f"K 线写 cache: {count} 行 ({len(klines_map)} 只)")
        finally:
            conn.close()
    except Exception as e:
        logging.warning(f"K 线 cache 写失败: {e}")


def _parse_kline_row(row: list, cols: list) -> dict:
    """把 research-mcp 返回的一行 K 线转成标准 bar dict。"""
    def _g(name, default=None):
        if name in cols:
            return row[cols.index(name)]
        return default

    def _safe_float(v, default=0.0):
        try:
            f = float(v) if v is not None else default
            # NaN 检测
            return default if f != f else f
        except (TypeError, ValueError):
            return default

    def _safe_int(v, default=0):
        try:
            f = float(v) if v is not None else default
            if f != f:  # NaN
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


# --------------------------------------------------------------------------- #
# 4. 从 K 线提取历史连板记录
# --------------------------------------------------------------------------- #


def extract_streaks_from_klines(klines: list, end_date: str) -> list:
    """扫描 K 线, 提取每段连板的"峰值"作为 historical_streaks 输入。

    一段连板 = 若干连续日 limit_up_streak 单调递增, 终止于下一日 streak < 当前
    或 不再涨停。取段内最高那天作为这段连板的代表。

    Args:
        klines: 时序从老到新的 K 线
        end_date: T 日 'YYYY-MM-DD', 只取严格在 T 日之前的连板 (T 日本身不算历史)

    Returns:
        [{"date": str, "max_streak": int, "close": float}, ...]
    """
    streaks = []
    in_streak = False
    cur_max = 0
    cur_peak_idx = -1

    for i, bar in enumerate(klines):
        if bar["date"] >= end_date:
            break  # T 日及之后不算历史
        s = bar["limit_up_streak"]
        if s > 0:
            if not in_streak:
                in_streak = True
                cur_max = s
                cur_peak_idx = i
            else:
                if s > cur_max:
                    cur_max = s
                    cur_peak_idx = i
        else:
            if in_streak:
                # 段结束, 落账
                peak = klines[cur_peak_idx]
                streaks.append({
                    "date": peak["date"],
                    "max_streak": cur_max,
                    "close": peak["close"],
                })
                in_streak = False
                cur_max = 0
                cur_peak_idx = -1

    # 收尾: 如果到末尾仍在连板段内, 也要落账
    if in_streak and cur_peak_idx >= 0:
        peak = klines[cur_peak_idx]
        streaks.append({
            "date": peak["date"],
            "max_streak": cur_max,
            "close": peak["close"],
        })

    return streaks


# --------------------------------------------------------------------------- #
# 5. 盘中分时 (akshare, T+1 验证用)
# --------------------------------------------------------------------------- #


def fetch_intraday(code: str):
    """T+1 盘中分时, 返回 DataFrame。失败返 None。

    Args:
        code: 6 位代码
    """
    try:
        df = _ak().stock_intraday_em(symbol=code)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        logging.warning(f"分时数据拉取失败 ({code}): {e}")
        return None


# --------------------------------------------------------------------------- #
# 6. 交易日历助手
# --------------------------------------------------------------------------- #


def shift_trading_days(date_str: str, n_days: int) -> str:
    """从 date_str 往前/往后 N 个交易日, 返回 'YYYY-MM-DD'。

    n_days < 0 = 往前; n_days > 0 = 往后。
    使用 akshare 交易日历, 失败时退化为日历日 (按 5 个工作日 ≈ 7 自然日 估算)。
    """
    from datetime import datetime, timedelta

    try:
        cal_df = _ak().tool_trade_date_hist_sina()
        cal = sorted(d.strftime("%Y-%m-%d") for d in cal_df["trade_date"])
        # 找 date_str 的索引
        try:
            idx = cal.index(date_str)
        except ValueError:
            # date_str 不在交易日历中, 找最近的
            for i, d in enumerate(cal):
                if d >= date_str:
                    idx = i
                    break
            else:
                idx = len(cal) - 1
        new_idx = max(0, min(len(cal) - 1, idx + n_days))
        return cal[new_idx]
    except Exception as e:
        logging.warning(f"交易日历查询失败 ({date_str}, {n_days}): {e}, 退化估算")
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # 自然日近似: |n_days| 个交易日 ≈ |n_days| * 7/5 自然日
        delta_natural = int(n_days * 1.4)
        return (dt + timedelta(days=delta_natural)).strftime("%Y-%m-%d")
