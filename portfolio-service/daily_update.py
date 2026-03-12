#!/usr/bin/env python3
"""
盘后自动更新脚本：
1. 获取所有账户的持仓股票
2. 通过 Tushare 获取最新收盘价
3. 更新持仓价格
4. 记录每日快照
"""

import sqlite3
import sys
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── 配置 ──
DB_PATH = Path(__file__).resolve().parent / "data" / "portfolio.db"
TUSHARE_TOKEN = "ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4"

LOG_PATH = Path(__file__).resolve().parent / "data" / "daily_update.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_all_positions_with_quantity(conn: sqlite3.Connection) -> list[dict]:
    """获取所有有持仓的记录"""
    rows = conn.execute(
        "SELECT DISTINCT ts_code FROM positions WHERE quantity > 0"
    ).fetchall()
    return [dict(r) for r in rows]


def _ts_code_to_raw(ts_code: str) -> str:
    """将 tushare 格式 (600519.SH) 转为纯数字代码 (600519)"""
    return ts_code.split(".")[0]


def fetch_latest_prices(ts_codes: list[str]) -> dict[str, float]:
    """通过 Tushare 实时行情接口获取最新价格，返回 {ts_code: close_price}"""
    try:
        import tushare as ts
    except ImportError:
        log.error("tushare 未安装，请运���: pip install tushare")
        sys.exit(1)

    prices = {}

    # 使用实时行情接口（收盘后立即可用，无需等日线数据入库）
    try:
        raw_codes = [_ts_code_to_raw(c) for c in ts_codes]
        raw_to_ts = {raw: tsc for raw, tsc in zip(raw_codes, ts_codes)}

        df = ts.get_realtime_quotes(raw_codes)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code = row["code"]
                tsc = raw_to_ts.get(code, code)
                price = float(row["price"]) if row["price"] else 0
                if price > 0:
                    prices[tsc] = price
                    log.info(f"  {tsc}: {price}")
                else:
                    log.warning(f"  {tsc}: 实时价格为0，跳过")
        else:
            log.warning("实时行情接口返回空数据")
    except Exception as e:
        log.error(f"实时行情获取失败: {e}")

    # 回退：对未获取到的代码，尝试日线接口
    missing = [c for c in ts_codes if c not in prices]
    if missing:
        log.info(f"回退到日线接口获取: {missing}")
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        today = date.today().strftime("%Y%m%d")
        for code in missing:
            try:
                pure_code = code.split(".")[0]
                is_fund = pure_code.startswith(("51", "15", "16", "50", "52", "56", "58", "11", "12"))
                if is_fund:
                    df = pro.fund_daily(ts_code=code, end_date=today, start_date=today)
                    if df.empty:
                        df = pro.fund_daily(ts_code=code, end_date=today, limit=1)
                else:
                    df = pro.daily(ts_code=code, end_date=today, limit=1)
                if not df.empty:
                    prices[code] = float(df.iloc[0]["close"])
                    log.info(f"  {code}: {prices[code]} (日线)")
                else:
                    log.warning(f"  {code}: 无数据（可能非交易日）")
            except Exception as e:
                log.error(f"  {code}: 获取失败 - {e}")

    return prices


def update_prices(conn: sqlite3.Connection, prices: dict[str, float]):
    """更新持仓表中的 current_price"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ts_code, price in prices.items():
        conn.execute(
            "UPDATE positions SET current_price=?, updated_at=? WHERE ts_code=? AND quantity > 0",
            (price, now, ts_code),
        )
    conn.commit()
    log.info(f"已更新 {len(prices)} 只股票价格")


def record_snapshots(conn: sqlite3.Connection, snap_date: str):
    """为所有账户记录每日快照"""
    accounts = conn.execute("SELECT * FROM accounts").fetchall()

    for acct in accounts:
        acct = dict(acct)
        account_id = acct["id"]

        # 计算持仓市值
        positions = conn.execute(
            "SELECT * FROM positions WHERE account_id=? AND quantity > 0",
            (account_id,),
        ).fetchall()

        stock_value = sum(r["current_price"] * r["quantity"] for r in positions)
        cash = acct["cash"]
        total_value = cash + stock_value

        # 如果没有持仓也没有现金变动（空账户），跳过
        if total_value == 0 and acct["initial_capital"] == 0:
            continue

        # 获取前一天快照计算日收益
        prev = conn.execute(
            "SELECT * FROM daily_snapshots WHERE account_id=? AND date<? ORDER BY date DESC LIMIT 1",
            (account_id, snap_date),
        ).fetchone()

        daily_return: Optional[float] = None
        if prev and prev["total_value"] > 0:
            daily_return = (total_value - prev["total_value"]) / prev["total_value"] * 100

        cumulative_return: Optional[float] = None
        if acct["initial_capital"] > 0:
            cumulative_return = (total_value - acct["initial_capital"]) / acct["initial_capital"] * 100

        # 写入快照（UPSERT）
        conn.execute(
            """
            INSERT INTO daily_snapshots (account_id, date, total_value, cash, stock_value, daily_return, cumulative_return)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, date) DO UPDATE SET
                total_value=excluded.total_value,
                cash=excluded.cash,
                stock_value=excluded.stock_value,
                daily_return=excluded.daily_return,
                cumulative_return=excluded.cumulative_return
            """,
            (account_id, snap_date, total_value, cash, stock_value, daily_return, cumulative_return),
        )

        log.info(
            f"  账户[{acct['user_id']}/{acct['name']}]: "
            f"总资产={total_value:.2f}, 现金={cash:.2f}, 持仓市值={stock_value:.2f}, "
            f"日收益={f'{daily_return:.2f}%' if daily_return is not None else 'N/A'}, "
            f"累计收益={f'{cumulative_return:.2f}%' if cumulative_return is not None else 'N/A'}"
        )

    conn.commit()


def main():
    log.info("=" * 50)
    log.info("开始盘后自动更新")

    if not DB_PATH.exists():
        log.error(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    conn = get_conn()

    # 1. 获取所有需要更新价格的股票代码
    positions = get_all_positions_with_quantity(conn)
    if not positions:
        log.info("无持仓，跳过更新")
        conn.close()
        return

    ts_codes = [p["ts_code"] for p in positions]
    log.info(f"需要更新的股票: {ts_codes}")

    # 2. 获取最新收盘价
    prices = fetch_latest_prices(ts_codes)
    if not prices:
        log.warning("未获取到任何价格数据，跳过本次更新")
        conn.close()
        return

    # 3. 更新持仓价格
    update_prices(conn, prices)

    # 4. 记录快照
    snap_date = date.today().strftime("%Y-%m-%d")
    log.info(f"记录快照: {snap_date}")
    record_snapshots(conn, snap_date)

    conn.close()
    log.info("盘后更新完成")


if __name__ == "__main__":
    main()
