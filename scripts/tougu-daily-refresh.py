#!/usr/bin/env python3
"""
投顾数据每日定时刷新脚本

Phase A: 刷新 5 张公共表（tougu_info, tougu_nav, tougu_performance, tougu_portfolio, tougu_equity_analysis）
Phase B+C: 各 bot 并行执行投顾巡检全链路（openclaw agent + tougu-portfolio-mcp）
Phase D: 为有持仓的 bot 记录收益快照（record_daily_snapshot）

定时: 每天 09:15 (cron) — 对齐远端数据源 09:00 更新后 15 分钟缓冲
数据源: research-mcp (http://research-mcp.jijinmima.cn/mcp)
目标库: /home/rooot/.openclaw/data/tougu.db
"""

import json
import logging
import shutil
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

# ── 配置 ──
RESEARCH_MCP_URL = "http://research-mcp.jijinmima.cn/mcp"
TOUGU_MCP_URL = "http://localhost:18070/mcp"
DB_PATH = "/home/rooot/.openclaw/data/tougu.db"
LOG_PATH = "/home/rooot/.openclaw/logs/tougu-daily-refresh.log"
BATCH_SIZE = 25
BATCH_INTERVAL = 2          # 秒
MCP_TIMEOUT = 120            # 秒
CIRCUIT_BREAKER_THRESHOLD = 3  # 连续失败 N 批后熔断，跳过剩余批次直接进入重试

OPENCLAW_BIN = shutil.which("openclaw") or "/home/rooot/.npm-global/bin/openclaw"
BOT_TIMEOUT = 900          # 单个 bot 执行全链路的超时（秒）
MAX_PARALLEL_BOTS = 2      # Phase B+C 最大并行 bot 数

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 中文列 → SQLite 列名映射
INFO_COL_MAP = {
    "策略ID": "strategy_id", "策略名称": "strategy_name", "管理人": "manager",
    "最大申购限额": "max_deposit", "最小申购限额": "min_deposit",
    "策略介绍": "introduction", "策略简介": "resume",
    "管理费率": "strategy_rate", "业绩基准": "benchmark",
    "目标年化收益率": "target_annual_yield", "申购状态": "buy_status",
}

NAV_COL_MAP = {
    "策略ID": "strategy_id", "策略名称": "strategy_name",
    "净值日期": "nav_date", "净值": "nav",
}

PERF_COL_MAP = {
    "策略ID": "strategy_id", "策略名称": "strategy_name",
    "截止日期": "as_of_date", "区间": "period",
    "收益率": "return_pct", "最大回撤": "max_drawdown_pct",
    "波动率": "volatility_pct", "夏普比率": "sharpe_ratio", "卡玛比率": "calmar_ratio",
}

PORT_COL_MAP = {
    "策略ID": "strategy_id", "策略名称": "strategy_name",
    "持仓日期": "nav_date", "基金代码": "fund_code", "基金名称": "fund_name",
    "基金类型": "fund_type", "持仓比例": "weight_pct",
    "标签日期": "label_date",
    "主题1": "theme_1", "主题1占比": "theme_1_pct",
    "主题2": "theme_2", "主题2占比": "theme_2_pct",
}

# ── 日志 ──
Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("tougu-daily-refresh")
log.setLevel(logging.INFO)
if not log.handlers:
    _fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    _fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _fh.setFormatter(_fmt)
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    log.handlers = [_fh, _sh]
    log.propagate = False


# ═══════════════════════════════════════
# MCP 调用
# ═══════════════════════════════════════

# 存储每个 MCP url 的 session_id
_MCP_SESSIONS: dict[str, str] = {}


def mcp_call(url: str, tool_name: str, arguments: dict, timeout: int = MCP_TIMEOUT) -> dict:
    """调用 MCP tool，返回解析后的 JSON 结果"""
    body = {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    headers = dict(MCP_HEADERS)
    session_id = _MCP_SESSIONS.get(url, "")
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    # 解析 SSE 响应
    for line in resp.text.split("\n"):
        if line.startswith("data: "):
            data = json.loads(line[6:])
            content = data.get("result", {}).get("content", [])
            if content:
                text = content[0].get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw_text": text}

    # 尝试直接解析为 JSON-RPC 响应（非 SSE）
    try:
        data = resp.json()
        content = data.get("result", {}).get("content", [])
        if content:
            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_text": text}
    except (json.JSONDecodeError, AttributeError):
        pass

    raise ValueError(f"无法解析 MCP 响应: {resp.text[:500]}")


def mcp_init(url: str) -> bool:
    """初始化 MCP session，保存 session_id 供后续 mcp_call 使用。返回是否成功。"""
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tougu-daily-refresh", "version": "1.0"},
        },
    }
    try:
        resp = requests.post(url, json=body, headers=MCP_HEADERS, timeout=10)
        resp.raise_for_status()
        session_id = resp.headers.get("mcp-session-id", "")
        if session_id:
            _MCP_SESSIONS[url] = session_id
            log.info(f"MCP session ok: {url} → {session_id[:16]}...")
        else:
            log.info(f"MCP {url} 无 session（无状态模式）")
        return True
    except Exception as e:
        log.warning(f"MCP init {url} 失败: {e}")
        return False


# ═══════════════════════════════════════
# SQLite 操作
# ═══════════════════════════════════════

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def parse_rows(result: dict, col_map: dict) -> list[dict]:
    """从 MCP 返回的 {data: {id: {columns, data}}} 格式解析为 dict 列表"""
    rows = []
    data = result.get("data", {})
    if isinstance(data, dict):
        for _key, block in data.items():
            columns = block.get("columns", [])
            mapped_cols = [col_map.get(c, c) for c in columns]
            for row in block.get("data", []):
                rows.append(dict(zip(mapped_cols, row)))
    elif isinstance(data, list):
        # 部分工具可能直接返回列表
        for item in data:
            if isinstance(item, dict):
                mapped = {col_map.get(k, k): v for k, v in item.items()}
                rows.append(mapped)
    return rows


def get_all_strategy_ids(conn: sqlite3.Connection) -> list[str]:
    """从 tougu_info 获取全部 strategy_id"""
    rows = conn.execute("SELECT strategy_id FROM tougu_info").fetchall()
    return [r["strategy_id"] for r in rows]


# ═══════════════════════════════════════
# Phase A: 刷新 5 张公共表
# ═══════════════════════════════════════

def refresh_info(conn: sqlite3.Connection) -> int:
    """Step 1: 刷新 tougu_info（全量单次）"""
    log.info("[1/5] 刷新 tougu_info ...")
    result = mcp_call(RESEARCH_MCP_URL, "get_strategy_info", {})
    if not result.get("success"):
        log.error(f"get_strategy_info 失败: {result.get('message')}")
        return 0

    rows = parse_rows(result, INFO_COL_MAP)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for r in rows:
        r["updated_at"] = now
        cols = list(r.keys())
        placeholders = ", ".join(["?"] * len(cols))
        upsert = f"INSERT OR REPLACE INTO tougu_info ({', '.join(cols)}) VALUES ({placeholders})"
        conn.execute(upsert, list(r.values()))
        count += 1
    conn.commit()
    log.info(f"  tougu_info: {count} 行写入")
    return count


def refresh_nav(conn: sqlite3.Connection) -> int:
    """Step 2: 刷新 tougu_nav（全量单次）"""
    log.info("[2/5] 刷新 tougu_nav ...")
    result = mcp_call(RESEARCH_MCP_URL, "get_strategy_nav", {})
    if not result.get("success"):
        log.error(f"get_strategy_nav 失败: {result.get('message')}")
        return 0

    rows = parse_rows(result, NAV_COL_MAP)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for r in rows:
        r["updated_at"] = now
        cols = list(r.keys())
        placeholders = ", ".join(["?"] * len(cols))
        upsert = f"INSERT OR REPLACE INTO tougu_nav ({', '.join(cols)}) VALUES ({placeholders})"
        conn.execute(upsert, list(r.values()))
        count += 1
    conn.commit()
    log.info(f"  tougu_nav: {count} 行写入")
    return count


def refresh_batched(conn: sqlite3.Connection, tool_name: str, table: str,
                    col_map: dict, strategy_ids: list[str],
                    step_label: str, delete_insert: bool = False) -> int:
    """通用分批刷新逻辑"""
    log.info(f"{step_label} 刷新 {table} (分批 {BATCH_SIZE}/次, 共 {len(strategy_ids)} 产品) ...")

    total_count = 0
    total_batches = (len(strategy_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    failed_batches = []
    consecutive_failures = 0

    for batch_idx in range(total_batches):
        # 熔断：连续失败超过阈值，跳过剩余批次
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            remaining = total_batches - batch_idx
            log.warning(f"  连续 {consecutive_failures} 批失败，熔断跳过剩余 {remaining} 批，等待重试阶段")
            for skip_idx in range(batch_idx, total_batches):
                s = skip_idx * BATCH_SIZE
                failed_batches.append(strategy_ids[s:s + BATCH_SIZE])
            break

        start = batch_idx * BATCH_SIZE
        batch_ids = strategy_ids[start:start + BATCH_SIZE]
        batch_str = ",".join(batch_ids)

        try:
            result = mcp_call(RESEARCH_MCP_URL, tool_name, {"strategy": batch_str})
            if not result.get("success"):
                log.warning(f"  批次 {batch_idx+1}/{total_batches} 失败: {result.get('message', 'unknown')}")
                failed_batches.append(batch_ids)
                consecutive_failures += 1
                time.sleep(BATCH_INTERVAL)
                continue

            rows = parse_rows(result, col_map)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if delete_insert:
                # 先删后插（portfolio / equity_analysis）
                seen_keys = set()
                for r in rows:
                    sid = r.get("strategy_id", "")
                    nd = r.get("nav_date", "")
                    key = (sid, nd)
                    if key not in seen_keys:
                        conn.execute(f"DELETE FROM {table} WHERE strategy_id=? AND nav_date=?", (sid, nd))
                        seen_keys.add(key)

            for r in rows:
                r["updated_at"] = now
                cols = list(r.keys())
                placeholders = ", ".join(["?"] * len(cols))
                sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
                conn.execute(sql, list(r.values()))
                total_count += 1

            conn.commit()
            consecutive_failures = 0  # 成功则重置

        except Exception as e:
            log.error(f"  批次 {batch_idx+1}/{total_batches} 异常: {e}")
            failed_batches.append(batch_ids)
            consecutive_failures += 1

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

        if (batch_idx + 1) % 10 == 0:
            log.info(f"  进度: {batch_idx+1}/{total_batches}, 累计 {total_count} 行")

    # 重试失败批次
    if failed_batches:
        log.info(f"  重试 {len(failed_batches)} 个失败批次 ...")
        for batch_ids in failed_batches:
            batch_str = ",".join(batch_ids)
            try:
                result = mcp_call(RESEARCH_MCP_URL, tool_name, {"strategy": batch_str})
                if result.get("success"):
                    rows = parse_rows(result, col_map)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if delete_insert:
                        seen_keys = set()
                        for r in rows:
                            key = (r.get("strategy_id", ""), r.get("nav_date", ""))
                            if key not in seen_keys:
                                conn.execute(f"DELETE FROM {table} WHERE strategy_id=? AND nav_date=?",
                                             (key[0], key[1]))
                                seen_keys.add(key)
                    for r in rows:
                        r["updated_at"] = now
                        cols = list(r.keys())
                        placeholders = ", ".join(["?"] * len(cols))
                        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
                        conn.execute(sql, list(r.values()))
                        total_count += 1
                    conn.commit()
                    log.info(f"  重试成功: {len(batch_ids)} 个产品")
                else:
                    log.error(f"  重试仍失败: {result.get('message')}")
            except Exception as e:
                log.error(f"  重试异常: {e}")
            time.sleep(BATCH_INTERVAL)

    log.info(f"  {table}: {total_count} 行写入")
    return total_count


def recent_two_quarter_ends(today: date | None = None) -> tuple[str, str]:
    """
    返回最近两个季末 (q_new, q_old)，格式 YYYY-MM-DD。

    上游 equity_analysis 按"基金最后披露的那个季末"存储，不是按季度全量维护：
    快的基金停在最新季末、慢的基金还停在前一个季末。所以查最近两个季末并合并，
    同一产品两个时点都有则取最新，只有一个就取那个。

    例: today=2026-04-14 → ("2026-03-31", "2025-12-31")
        today=2026-07-10 → ("2026-06-30", "2026-03-31")
        today=2026-01-05 → ("2025-12-31", "2025-09-30")
    """
    if today is None:
        today = date.today()
    y = today.year
    candidates = sorted(
        [
            date(y, 12, 31),
            date(y, 9, 30),
            date(y, 6, 30),
            date(y, 3, 31),
            date(y - 1, 12, 31),
            date(y - 1, 9, 30),
        ],
        reverse=True,
    )
    le_today = [q for q in candidates if q <= today]
    q_new, q_old = le_today[0], le_today[1]
    return q_new.strftime("%Y-%m-%d"), q_old.strftime("%Y-%m-%d")


def refresh_equity_analysis(conn: sqlite3.Connection, strategy_ids: list[str]) -> int:
    """Step 5: 刷新 tougu_equity_analysis（宽表转长表）

    数据源是基金定期报告，上游按"基金最后披露的季末"存储，不做季度全量维护。
    策略：查最近两个季末 (q_new, q_old)，按产品合并 —— 两个时点都有则取 q_new，
    只有一个就取那个，都没有就放弃。每只产品在本表中只保留一个 nav_date 的数据。
    """
    q_new, q_old = recent_two_quarter_ends()
    log.info(
        f"[5/5] 刷新 tougu_equity_analysis (最近两季末 {q_new} / {q_old}, 分批 {BATCH_SIZE}/次) ..."
    )

    def fetch_batch(batch_ids: list[str], as_of_date: str) -> dict | None:
        """返回 {strategy_id: (sname, nav_date, columns, row)}；异常或 success=False 时返回 None。"""
        try:
            result = mcp_call(
                RESEARCH_MCP_URL,
                "get_strategy_equity_analysis",
                {"strategy": ",".join(batch_ids), "as_of_date": as_of_date},
            )
        except Exception as e:
            log.error(f"  fetch 异常 (as_of_date={as_of_date}): {e}")
            return None
        if not result.get("success"):
            return None
        out: dict = {}
        for _k, block in (result.get("data") or {}).items():
            columns = block.get("columns", [])
            for row_data in block.get("data", []):
                if len(columns) < 3 or len(row_data) < 3:
                    continue
                sid = row_data[0]
                out[sid] = (row_data[1], row_data[2], columns, row_data)
        return out

    def write_strategy(sid: str, sname: str, nav_date: str,
                        columns: list, row_data: list, now: str) -> int:
        """先清掉该 strategy 在长表中的所有旧行（任何 nav_date），再写入本次选中的季末数据。"""
        conn.execute("DELETE FROM tougu_equity_analysis WHERE strategy_id=?", (sid,))
        n = 0
        for i in range(3, len(columns)):
            sector = columns[i]
            pct = row_data[i] if i < len(row_data) else None
            if pct is None or pct == "" or pct == 0:
                continue
            conn.execute(
                "INSERT INTO tougu_equity_analysis "
                "(strategy_id, strategy_name, nav_date, sector, sector_pct_in_equity, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sid, sname, nav_date, sector, pct, now),
            )
            n += 1
        return n

    def process_batch(batch_ids: list[str]) -> tuple[int, bool]:
        """对一批产品做 new + old 合并写库。返回 (新增行数, 是否两次查询都失败)."""
        new_map = fetch_batch(batch_ids, q_new)
        old_map = fetch_batch(batch_ids, q_old)
        if new_map is None and old_map is None:
            return 0, True
        new_map = new_map or {}
        old_map = old_map or {}
        # 合并：先放 old，再用 new 覆盖 —— 同产品两个时点都有 → 取 q_new
        merged = dict(old_map)
        merged.update(new_map)
        if not merged:
            return 0, False
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added = 0
        try:
            for sid, (sname, nav_date, cols, row) in merged.items():
                added += write_strategy(sid, sname, nav_date, cols, row, now)
            conn.commit()
        except Exception as e:
            log.error(f"  批次写库异常: {e}")
            return added, False
        return added, False

    total_count = 0
    total_batches = (len(strategy_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    failed_batches: list[list[str]] = []
    consecutive_failures = 0

    for batch_idx in range(total_batches):
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            remaining = total_batches - batch_idx
            log.warning(f"  连续 {consecutive_failures} 批失败，熔断跳过剩余 {remaining} 批，等待重试阶段")
            for skip_idx in range(batch_idx, total_batches):
                s = skip_idx * BATCH_SIZE
                failed_batches.append(strategy_ids[s:s + BATCH_SIZE])
            break

        start = batch_idx * BATCH_SIZE
        batch_ids = strategy_ids[start:start + BATCH_SIZE]
        added, both_failed = process_batch(batch_ids)
        total_count += added
        if both_failed:
            log.warning(f"  批次 {batch_idx+1}/{total_batches} 两次季末查询均失败")
            failed_batches.append(batch_ids)
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

        if (batch_idx + 1) % 10 == 0:
            log.info(f"  进度: {batch_idx+1}/{total_batches}, 累计 {total_count} 行")

    # 重试失败批次，最多一轮
    if failed_batches:
        log.info(f"  重试 {len(failed_batches)} 个失败批次 ...")
        still_failed = []
        for retry_ids in failed_batches:
            added, both_failed = process_batch(retry_ids)
            total_count += added
            if both_failed:
                still_failed.append(retry_ids)
            else:
                log.info(f"  重试成功: {len(retry_ids)} 个产品，新增 {added} 行")
            time.sleep(BATCH_INTERVAL)
        if still_failed:
            log.warning(f"  仍有 {len(still_failed)} 个批次重试后失败")

    log.info(f"  tougu_equity_analysis: {total_count} 行写入")
    return total_count


def phase_a() -> dict:
    """Phase A: 刷新 5 张公共表

    每个 step 独立 try/except，单步失败不影响后续 step。
    Step 3/4/5 依赖 strategy_ids，从已有 tougu_info 表读取（即使 step 1 失败也能用旧列表兜底）。
    """
    log.info("=" * 60)
    log.info("Phase A: 开始刷新公共表")

    if not mcp_init(RESEARCH_MCP_URL):
        log.error("Phase A: 远程 MCP 不可达（健康检查失败），跳过全部公共表刷新")
        return {"_mcp_unreachable": True}

    conn = get_conn()
    report: dict = {}
    errors: list[str] = []

    def run_step(name: str, fn):
        try:
            report[name] = fn()
        except Exception as e:
            log.error(f"  {name} 异常: {e}")
            errors.append(name)
            report[name] = f"FAILED: {e}"

    try:
        # Step 1: tougu_info（全量）
        run_step("tougu_info", lambda: refresh_info(conn))

        # Step 2: tougu_nav（全量）—— 与 info 完全独立，info 挂掉不能拖累 nav
        run_step("tougu_nav", lambda: refresh_nav(conn))

        # 获取全部 strategy_id 用于分批：用 db 现有 tougu_info（即使 step 1 异常也能用旧列表兜底）
        try:
            strategy_ids = get_all_strategy_ids(conn)
            log.info(f"获取到 {len(strategy_ids)} 个产品 ID 用于分批刷新")
        except Exception as e:
            log.error(f"  读取 strategy_ids 异常: {e}")
            strategy_ids = []

        if not strategy_ids:
            log.error("tougu_info 为空，跳过分批刷新后续 3 张表")
        else:
            # Step 3: tougu_performance（分批）
            run_step(
                "tougu_performance",
                lambda: refresh_batched(
                    conn, "get_strategy_performance", "tougu_performance",
                    PERF_COL_MAP, strategy_ids, "[3/5]"
                ),
            )

            # Step 4: tougu_portfolio（分批，先删后插）
            run_step(
                "tougu_portfolio",
                lambda: refresh_batched(
                    conn, "get_strategy_portfolio", "tougu_portfolio",
                    PORT_COL_MAP, strategy_ids, "[4/5]", delete_insert=True
                ),
            )

            # Step 5: tougu_equity_analysis（分批，宽表转长表）
            run_step(
                "tougu_equity_analysis",
                lambda: refresh_equity_analysis(conn, strategy_ids),
            )

        # MCP 恢复后针对性补跑 info/nav：
        # Phase A 前段 MCP 在恢复期时，info/nav 因无重试一次超时即放弃。
        # 若 performance/portfolio 最终写入成功，说明 MCP 后来已恢复，此时补跑一次 info/nav。
        perf_ok = isinstance(report.get("tougu_performance"), int) and report["tougu_performance"] > 0
        port_ok = isinstance(report.get("tougu_portfolio"), int) and report["tougu_portfolio"] > 0
        if perf_ok or port_ok:
            if report.get("tougu_info") == 0:
                log.info("检测到 MCP 已恢复但 tougu_info 为空，补跑 refresh_info")
                try:
                    report["tougu_info"] = refresh_info(conn)
                except Exception as e:
                    log.error(f"  补跑 refresh_info 异常: {e}")
            if report.get("tougu_nav") == 0:
                log.info("检测到 MCP 已恢复但 tougu_nav 为空，补跑 refresh_nav")
                try:
                    report["tougu_nav"] = refresh_nav(conn)
                except Exception as e:
                    log.error(f"  补跑 refresh_nav 异常: {e}")
    finally:
        conn.close()

    log.info("Phase A 完成:")
    for table, count in report.items():
        log.info(f"  {table}: {count} 行" if isinstance(count, int) else f"  {table}: {count}")
    if errors:
        log.warning(f"Phase A 共 {len(errors)} 个 step 失败: {', '.join(errors)}")
    return report


# ═══════════════════════════════════════
# Phase B+C: 各 bot 串行执行选品 + 巡检
# ═══════════════════════════════════════

BOT_PIPELINE_PROMPT = (
    "执行 /tougu-portfolio-review（今日定时巡检）。"
    "产品池数据已在凌晨更新完毕。"
    "完整流程：重新选品 → 对比持仓 → 决定是否调仓 → 写回数据库 → 记录收益快照。"
)


def run_bot_pipeline(bot_id: str) -> bool:
    """通过 openclaw agent CLI 触发单个 bot 执行投顾全链路，阻塞等待完成"""
    log.info(f"  [{bot_id}] 开始执行全链路 ...")
    t0 = time.time()

    cmd = [
        OPENCLAW_BIN, "agent",
        "--agent", bot_id,
        "--message", BOT_PIPELINE_PROMPT,
        "--thinking", "medium",
        "--timeout", str(BOT_TIMEOUT),
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=BOT_TIMEOUT + 60,  # 给 CLI 本身多留 60s 余量
        )
        elapsed = time.time() - t0

        if result.returncode == 0:
            log.info(f"  [{bot_id}] 完成，耗时 {elapsed:.0f}s")
            # 尝试解析 JSON 输出摘要
            try:
                output = json.loads(result.stdout)
                summary = output.get("summary", output.get("text", ""))[:200]
                if summary:
                    log.info(f"  [{bot_id}] 摘要: {summary}")
            except (json.JSONDecodeError, AttributeError):
                if result.stdout:
                    log.info(f"  [{bot_id}] 输出: {result.stdout[:200]}")
            return True
        else:
            log.error(f"  [{bot_id}] 失败 (exit={result.returncode}, {elapsed:.0f}s)")
            if result.stderr:
                log.error(f"  [{bot_id}] stderr: {result.stderr[:300]}")
            return False

    except subprocess.TimeoutExpired:
        log.error(f"  [{bot_id}] 超时 ({BOT_TIMEOUT}s)")
        return False
    except FileNotFoundError:
        log.error(f"  openclaw CLI 不存在: {OPENCLAW_BIN}")
        return False
    except Exception as e:
        log.error(f"  [{bot_id}] 异常: {e}")
        return False


def phase_bc():
    """Phase B+C: 各 bot 并行执行选品 + 巡检全链路（最大并发 MAX_PARALLEL_BOTS）"""
    log.info("=" * 60)
    log.info(f"Phase B+C: 各 bot 并行执行投顾全链路（并发={MAX_PARALLEL_BOTS}）")

    bot_ids = get_active_bot_ids()
    if not bot_ids:
        log.info("  无活跃 bot，跳过")
        return

    log.info(f"  执行列表: {', '.join(bot_ids)}")

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_BOTS) as pool:
        futures = {pool.submit(run_bot_pipeline, bid): bid for bid in bot_ids}
        for future in as_completed(futures):
            bot_id = futures[future]
            try:
                success = future.result()
            except Exception as e:
                log.error(f"  [{bot_id}] 异常: {e}")
                success = False
            results[bot_id] = "成功" if success else "失败"
            if not success:
                log.warning(f"  [{bot_id}] 失败")

    log.info("Phase B+C 完成:")
    for bot_id in bot_ids:
        log.info(f"  {bot_id}: {results.get(bot_id, '未执行')}")


# ═══════════════════════════════════════
# Phase D: Bot 收益快照（兜底）
# ═══════════════════════════════════════

def get_active_bot_ids() -> list[str]:
    """从数据库获取有 active 持仓的 bot 列表，按编号升序（bot1, bot2, ..., bot10）"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT bot_id FROM bot_holdings WHERE status='active' "
        "ORDER BY CAST(SUBSTR(bot_id, 4) AS INTEGER)"
    ).fetchall()
    conn.close()
    return [r["bot_id"] for r in rows]


def phase_d():
    """Phase D: 为有持仓的 bot 记录收益快照"""
    log.info("=" * 60)
    log.info("Phase D: 更新 bot 收益快照")

    bot_ids = get_active_bot_ids()
    if not bot_ids:
        log.info("  无活跃 bot，跳过")
        return

    log.info(f"  活跃 bot: {bot_ids}")

    # 用 tougu_nav 中最新的 nav_date 作为快照日期（而非脚本执行日期）
    # 因为脚本在 T+1 凌晨执行，nav 数据是 T 日的
    conn = get_conn()
    latest_nav_date_row = conn.execute("SELECT MAX(nav_date) as d FROM tougu_nav").fetchone()
    latest_snap_date_row = conn.execute("SELECT MAX(trade_date) as d FROM bot_daily_snapshots").fetchone()
    conn.close()
    if not latest_nav_date_row or not latest_nav_date_row["d"]:
        log.warning("  tougu_nav 无数据，跳过快照")
        return
    snapshot_date = latest_nav_date_row["d"]
    latest_snap_date = latest_snap_date_row["d"] if latest_snap_date_row else None
    log.info(f"  快照日期: {snapshot_date}（tougu_nav 最新 nav_date）")
    log.info(f"  已存在最新快照日期: {latest_snap_date}")

    # 若 tougu_nav 没有新日期（Phase A 失败等场景），跳过以免反复覆盖旧快照
    if latest_snap_date and snapshot_date <= latest_snap_date:
        log.warning(
            f"  tougu_nav 最新 nav_date ({snapshot_date}) 不晚于已存在快照 ({latest_snap_date})，"
            f"跳过 Phase D 避免覆盖旧数据"
        )
        return

    mcp_init(TOUGU_MCP_URL)

    for bot_id in bot_ids:
        try:
            result = mcp_call(
                TOUGU_MCP_URL, "record_daily_snapshot",
                {"bot_id": bot_id, "trade_date": snapshot_date},
                timeout=30,
            )
            success = result.get("success", False)
            if success:
                net_value = result.get("net_value", "?")
                total_value = result.get("total_value", "?")
                log.info(f"  {bot_id}: 快照成功 (净值={net_value}, 总资产={total_value})")
            else:
                log.warning(f"  {bot_id}: {result.get('message', '未知错误')}")
        except Exception as e:
            log.error(f"  {bot_id}: 快照失败 - {e}")


# ═══════════════════════════════════════
# 入口
# ═══════════════════════════════════════

def main():
    start = time.time()
    log.info("=" * 60)
    log.info(f"投顾每日刷新开始 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    # 检查数据库存在
    if not Path(DB_PATH).exists():
        log.error(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    # Phase A 前：记录 tougu_nav 当前最新 nav_date（用于判断 Phase A 是否带来新数据）
    conn_pre = get_conn()
    row = conn_pre.execute("SELECT MAX(nav_date) AS d FROM tougu_nav").fetchone()
    nav_date_before = row["d"] if row else None
    row = conn_pre.execute("SELECT MAX(trade_date) AS d FROM bot_daily_snapshots").fetchone()
    snap_date_before = row["d"] if row else None
    conn_pre.close()
    log.info(f"Phase A 前: tougu_nav 最新 nav_date = {nav_date_before}, bot_daily_snapshots 最新 = {snap_date_before}")

    # Phase A: 刷新 5 张公共表
    report = phase_a()

    # Phase A 后：检查 nav_date 是否推进了
    conn_post = get_conn()
    row = conn_post.execute("SELECT MAX(nav_date) AS d FROM tougu_nav").fetchone()
    nav_date_after = row["d"] if row else None
    conn_post.close()
    log.info(f"Phase A 后: tougu_nav 最新 nav_date = {nav_date_after}")

    mcp_down = report.get("_mcp_unreachable", False)

    # ── 关键 guard：决定是否跑 Phase B+C+D ──
    # 触发跳过的任一条件：
    #   1. MCP 不可达（Phase A 完全失败）
    #   2. tougu_nav 没有新日期（周末/节假日/上游未更新）
    #   3. tougu_nav 新日期已经有快照（之前已经跑过这一天）
    skip_reason = None
    if mcp_down:
        skip_reason = "MCP 不可达（Phase A 完全失败）"
    elif not nav_date_after:
        skip_reason = "tougu_nav 无任何数据"
    elif nav_date_before and nav_date_after <= nav_date_before:
        skip_reason = f"tougu_nav 没有新数据（仍为 {nav_date_after}，周末/节假日/上游未更新）"
    elif snap_date_before and nav_date_after <= snap_date_before:
        skip_reason = f"tougu_nav 最新 ({nav_date_after}) 不晚于已存在快照 ({snap_date_before})，无可生成的新快照"

    if skip_reason:
        log.warning(f"跳过 Phase B+C+D: {skip_reason}")
        log.info("本次 cron 仅完成 Phase A 数据刷新，各 bot 巡检和快照未执行")
    else:
        log.info(f"nav_date 从 {nav_date_before} 推进到 {nav_date_after}，继续执行 Phase B+C+D")
        # Phase B+C: 各 bot 并行执行选品 + 巡检（含调仓写库）
        phase_bc()
        # Phase D: 收益快照兜底（portfolio-review 正常时已执行，这里确保不遗漏）
        phase_d()

    elapsed = time.time() - start
    log.info(f"全部完成，耗时 {elapsed:.1f} 秒")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
