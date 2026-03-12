"""
SQLite 数据持久层 —— 管理账户、持仓、交易、每日快照。

数据库文件默认存放在 ~/.openclaw/workspace/portfolio-mcp/data/ 目录下。
"""

import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

_DB_DIR = Path(os.environ.get("PORTFOLIO_DB_DIR",
               str(Path(__file__).resolve().parent.parent / "data")))
_DB_PATH = _DB_DIR / "portfolio.db"


def _conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT    NOT NULL,
        name        TEXT    NOT NULL DEFAULT '默认账户',
        initial_capital REAL NOT NULL DEFAULT 0,
        cash        REAL    NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, name)
    );

    CREATE TABLE IF NOT EXISTS positions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id  INTEGER NOT NULL REFERENCES accounts(id),
        ts_code     TEXT    NOT NULL,
        stock_name  TEXT    NOT NULL DEFAULT '',
        quantity    INTEGER NOT NULL DEFAULT 0,
        avg_cost    REAL    NOT NULL DEFAULT 0,
        current_price REAL  NOT NULL DEFAULT 0,
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        UNIQUE(account_id, ts_code)
    );

    CREATE TABLE IF NOT EXISTS trades (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id  INTEGER NOT NULL REFERENCES accounts(id),
        ts_code     TEXT    NOT NULL,
        stock_name  TEXT    NOT NULL DEFAULT '',
        direction   TEXT    NOT NULL CHECK(direction IN ('buy','sell')),
        quantity    INTEGER NOT NULL,
        price       REAL    NOT NULL,
        amount      REAL    NOT NULL,
        fee         REAL    NOT NULL DEFAULT 0,
        reason      TEXT    NOT NULL DEFAULT '',
        trade_date  TEXT    NOT NULL,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS daily_snapshots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id      INTEGER NOT NULL REFERENCES accounts(id),
        date            TEXT    NOT NULL,
        total_value     REAL    NOT NULL,
        cash            REAL    NOT NULL,
        stock_value     REAL    NOT NULL,
        daily_return    REAL,
        cumulative_return REAL,
        UNIQUE(account_id, date)
    );
    """)


# ── 初始化 ──
_connection = _conn()
_init_tables(_connection)
# 兼容升级：为已有数据库添加 reason 列
try:
    _connection.execute("ALTER TABLE trades ADD COLUMN reason TEXT NOT NULL DEFAULT ''")
except sqlite3.OperationalError:
    pass  # 列已存在
_connection.close()


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def _to_json(rows) -> str:
    if isinstance(rows, dict):
        return json.dumps(rows, ensure_ascii=False)
    return json.dumps([dict(r) for r in rows], ensure_ascii=False)


# ══════════════════════════════════════════════
# 账户
# ══════════════════════════════════════════════

def create_account(user_id: str, name: str, initial_capital: float) -> dict:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO accounts (user_id, name, initial_capital, cash) VALUES (?, ?, ?, ?)",
            (user_id, name, initial_capital, initial_capital),
        )
        row = conn.execute(
            "SELECT * FROM accounts WHERE user_id=? AND name=?", (user_id, name)
        ).fetchone()
        return dict(row)


def get_account(user_id: str, name: str = "默认账户") -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE user_id=? AND name=?", (user_id, name)
        ).fetchone()
        return dict(row) if row else None


def list_accounts(user_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE user_id=?", (user_id,)
        ).fetchall()
        return _rows_to_list(rows)


def update_cash(account_id: int, cash: float):
    with _conn() as conn:
        conn.execute("UPDATE accounts SET cash=? WHERE id=?", (cash, account_id))


def update_initial_capital(account_id: int, initial_capital: float):
    with _conn() as conn:
        conn.execute("UPDATE accounts SET initial_capital=? WHERE id=?", (initial_capital, account_id))


# ══════════════════════════════════════════════
# 持仓
# ══════════════════════════════════════════════

def get_positions(account_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE account_id=? AND quantity>0", (account_id,)
        ).fetchall()
        return _rows_to_list(rows)


def get_position(account_id: int, ts_code: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE account_id=? AND ts_code=?",
            (account_id, ts_code),
        ).fetchone()
        return dict(row) if row else None


def upsert_position(account_id: int, ts_code: str, stock_name: str,
                    quantity: int, avg_cost: float, current_price: float):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        conn.execute("""
            INSERT INTO positions (account_id, ts_code, stock_name, quantity, avg_cost, current_price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, ts_code) DO UPDATE SET
                stock_name=excluded.stock_name,
                quantity=excluded.quantity,
                avg_cost=excluded.avg_cost,
                current_price=excluded.current_price,
                updated_at=excluded.updated_at
        """, (account_id, ts_code, stock_name, quantity, avg_cost, current_price, now))


def update_position_price(account_id: int, ts_code: str, current_price: float):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        conn.execute(
            "UPDATE positions SET current_price=?, updated_at=? WHERE account_id=? AND ts_code=?",
            (current_price, now, account_id, ts_code),
        )


# ══════════════════════════════════════════════
# 交易记录
# ══════════════════════════════════════════════

def add_trade(account_id: int, ts_code: str, stock_name: str,
              direction: str, quantity: int, price: float,
              amount: float, fee: float, trade_date: str,
              reason: str = "") -> dict:
    with _conn() as conn:
        cur = conn.execute("""
            INSERT INTO trades (account_id, ts_code, stock_name, direction, quantity, price, amount, fee, reason, trade_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, ts_code, stock_name, direction, quantity, price, amount, fee, reason, trade_date))
        row = conn.execute("SELECT * FROM trades WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)


def get_trades(account_id: int, ts_code: str = "",
               start_date: str = "", end_date: str = "",
               limit: int = 100) -> list[dict]:
    with _conn() as conn:
        sql = "SELECT * FROM trades WHERE account_id=?"
        params: list = [account_id]
        if ts_code:
            sql += " AND ts_code=?"
            params.append(ts_code)
        if start_date:
            sql += " AND trade_date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date<=?"
            params.append(end_date)
        sql += " ORDER BY trade_date DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)


# ══════════════════════════════════════════════
# 每日快照
# ══════════════════════════════════════════════

def save_snapshot(account_id: int, snap_date: str, total_value: float,
                  cash: float, stock_value: float,
                  daily_return: Optional[float], cumulative_return: Optional[float]):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO daily_snapshots (account_id, date, total_value, cash, stock_value, daily_return, cumulative_return)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, date) DO UPDATE SET
                total_value=excluded.total_value,
                cash=excluded.cash,
                stock_value=excluded.stock_value,
                daily_return=excluded.daily_return,
                cumulative_return=excluded.cumulative_return
        """, (account_id, snap_date, total_value, cash, stock_value, daily_return, cumulative_return))


def get_snapshots(account_id: int, start_date: str = "", end_date: str = "") -> list[dict]:
    with _conn() as conn:
        sql = "SELECT * FROM daily_snapshots WHERE account_id=?"
        params: list = [account_id]
        if start_date:
            sql += " AND date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND date<=?"
            params.append(end_date)
        sql += " ORDER BY date ASC"
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)


def get_latest_snapshot(account_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_snapshots WHERE account_id=? ORDER BY date DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        return dict(row) if row else None


def get_all_accounts() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM accounts").fetchall()
        return _rows_to_list(rows)
