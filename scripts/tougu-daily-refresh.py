#!/usr/bin/env python3
"""
投顾数据每日定时刷新脚本

Phase A: 刷新 5 张公共表（tougu_info, tougu_nav, tougu_performance, tougu_portfolio, tougu_equity_analysis）
Phase D: 为有持仓的 bot 记录收益快照（record_daily_snapshot）

定时: 每天 03:00 (cron)
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
from datetime import datetime, date
from pathlib import Path

import requests

# ── 配置 ──
RESEARCH_MCP_URL = "http://research-mcp.jijinmima.cn/mcp"
TOUGU_MCP_URL = "http://localhost:18070/mcp"
DB_PATH = "/home/rooot/.openclaw/data/tougu.db"
LOG_PATH = "/home/rooot/.openclaw/logs/tougu-daily-refresh.log"
BATCH_SIZE = 25
BATCH_INTERVAL = 2  # 秒
MCP_TIMEOUT = 120   # 秒

OPENCLAW_BIN = shutil.which("openclaw") or "/home/rooot/.npm-global/bin/openclaw"
BOT_TIMEOUT = 900  # 单个 bot 执行全链路的超时（秒）

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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════
# MCP 调用
# ═══════════════════════════════════════

def mcp_call(url: str, tool_name: str, arguments: dict, timeout: int = MCP_TIMEOUT) -> dict:
    """调用 MCP tool，返回解析后的 JSON 结果"""
    body = {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = requests.post(url, json=body, headers=MCP_HEADERS, timeout=timeout)
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


def mcp_init(url: str):
    """初始化 MCP session"""
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tougu-daily-refresh", "version": "1.0"},
        },
    }
    try:
        requests.post(url, json=body, headers=MCP_HEADERS, timeout=10)
    except Exception as e:
        log.warning(f"MCP init {url} 失败（可能无状态，继续）: {e}")


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

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        batch_ids = strategy_ids[start:start + BATCH_SIZE]
        batch_str = ",".join(batch_ids)

        try:
            result = mcp_call(RESEARCH_MCP_URL, tool_name, {"strategy": batch_str})
            if not result.get("success"):
                log.warning(f"  批次 {batch_idx+1}/{total_batches} 失败: {result.get('message', 'unknown')}")
                failed_batches.append(batch_ids)
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

        except Exception as e:
            log.error(f"  批次 {batch_idx+1}/{total_batches} 异常: {e}")
            failed_batches.append(batch_ids)

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


def refresh_equity_analysis(conn: sqlite3.Connection, strategy_ids: list[str]) -> int:
    """Step 5: 刷新 tougu_equity_analysis（宽表转长表）"""
    log.info(f"[5/5] 刷新 tougu_equity_analysis (分批 {BATCH_SIZE}/次) ...")

    total_count = 0
    total_batches = (len(strategy_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    failed_batches = []

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        batch_ids = strategy_ids[start:start + BATCH_SIZE]
        batch_str = ",".join(batch_ids)

        try:
            result = mcp_call(RESEARCH_MCP_URL, "get_strategy_equity_analysis", {"strategy": batch_str})
            if not result.get("success"):
                log.warning(f"  批次 {batch_idx+1}/{total_batches} 失败: {result.get('message', 'unknown')}")
                failed_batches.append(batch_ids)
                time.sleep(BATCH_INTERVAL)
                continue

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = result.get("data", {})

            for _key, block in data.items():
                columns = block.get("columns", [])
                for row_data in block.get("data", []):
                    # 前 3 列: 策略ID, 策略名称, 持仓日期
                    if len(columns) < 3 or len(row_data) < 3:
                        continue
                    sid = row_data[0]
                    sname = row_data[1]
                    nav_date = row_data[2]

                    # 先删旧数据
                    conn.execute(
                        "DELETE FROM tougu_equity_analysis WHERE strategy_id=? AND nav_date=?",
                        (sid, nav_date)
                    )

                    # 第 4+ 列: 动态主题名 → 长表行
                    for i in range(3, len(columns)):
                        sector = columns[i]
                        pct = row_data[i] if i < len(row_data) else None
                        if pct is None or pct == "" or pct == 0:
                            continue
                        conn.execute(
                            "INSERT INTO tougu_equity_analysis "
                            "(strategy_id, strategy_name, nav_date, sector, sector_pct_in_equity, updated_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (sid, sname, nav_date, sector, pct, now)
                        )
                        total_count += 1

            conn.commit()

        except Exception as e:
            log.error(f"  批次 {batch_idx+1}/{total_batches} 异常: {e}")
            failed_batches.append(batch_ids)

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_INTERVAL)

        if (batch_idx + 1) % 10 == 0:
            log.info(f"  进度: {batch_idx+1}/{total_batches}, 累计 {total_count} 行")

    # 重试失败批次（简化：跳过宽表转长表的重试，直接记录）
    if failed_batches:
        log.warning(f"  {len(failed_batches)} 个批次失败，未重试（equity_analysis 宽转长较复杂）")

    log.info(f"  tougu_equity_analysis: {total_count} 行写入")
    return total_count


def phase_a() -> dict:
    """Phase A: 刷新 5 张公共表"""
    log.info("=" * 60)
    log.info("Phase A: 开始刷新公共表")

    mcp_init(RESEARCH_MCP_URL)
    conn = get_conn()
    report = {}

    try:
        # Step 1: tougu_info（全量）
        report["tougu_info"] = refresh_info(conn)

        # Step 2: tougu_nav（全量）
        report["tougu_nav"] = refresh_nav(conn)

        # 获取全部 strategy_id 用于分批
        strategy_ids = get_all_strategy_ids(conn)
        log.info(f"获取到 {len(strategy_ids)} 个产品 ID 用于分批刷新")

        if not strategy_ids:
            log.error("tougu_info 为空，无法分批刷新后续 3 张表")
            return report

        # Step 3: tougu_performance（分批）
        report["tougu_performance"] = refresh_batched(
            conn, "get_strategy_performance", "tougu_performance",
            PERF_COL_MAP, strategy_ids, "[3/5]"
        )

        # Step 4: tougu_portfolio（分批，先删后插）
        report["tougu_portfolio"] = refresh_batched(
            conn, "get_strategy_portfolio", "tougu_portfolio",
            PORT_COL_MAP, strategy_ids, "[4/5]", delete_insert=True
        )

        # Step 5: tougu_equity_analysis（分批，宽表转长表）
        report["tougu_equity_analysis"] = refresh_equity_analysis(conn, strategy_ids)

    except Exception as e:
        log.error(f"Phase A 异常: {e}")
    finally:
        conn.close()

    log.info("Phase A 完成:")
    for table, count in report.items():
        log.info(f"  {table}: {count} 行")
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
    """Phase B+C: 各 bot 按编号顺序串行执行选品 + 巡检全链路"""
    log.info("=" * 60)
    log.info("Phase B+C: 各 bot 串行执行投顾全链路")

    bot_ids = get_active_bot_ids()
    if not bot_ids:
        log.info("  无活跃 bot，跳过")
        return

    log.info(f"  执行顺序: {' → '.join(bot_ids)}")

    results = {}
    for bot_id in bot_ids:
        success = run_bot_pipeline(bot_id)
        results[bot_id] = "成功" if success else "失败"
        if not success:
            log.warning(f"  [{bot_id}] 失败，继续下一个 bot")

    log.info("Phase B+C 完成:")
    for bot_id, status in results.items():
        log.info(f"  {bot_id}: {status}")


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
    today = date.today().strftime("%Y-%m-%d")

    mcp_init(TOUGU_MCP_URL)

    for bot_id in bot_ids:
        try:
            result = mcp_call(
                TOUGU_MCP_URL, "record_daily_snapshot",
                {"bot_id": bot_id, "trade_date": today},
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

    # Phase A: 刷新 5 张公共表
    phase_a()

    # Phase B+C: 各 bot 串行执行选品 + 巡检（含调仓写库）
    phase_bc()

    # Phase D: 收益快照兜底（portfolio-review 正常时已执行，这里确保不遗漏）
    phase_d()

    elapsed = time.time() - start
    log.info(f"全部完成，耗时 {elapsed:.1f} 秒")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
