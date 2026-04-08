import sqlite3, json

conn = sqlite3.connect("/home/rooot/.openclaw/data/tougu.db")
conn.row_factory = sqlite3.Row

accounts = conn.execute("SELECT * FROM bot_accounts").fetchall()
result = []

for a in accounts:
    bot_id = a["bot_id"]
    holdings = conn.execute(
        "SELECT h.product_id, h.amount_invested, h.market_value, h.weight, h.role, "
        "h.unrealized_pnl, h.unrealized_pnl_pct, h.latest_nav, h.entry_nav, "
        "i.strategy_name "
        "FROM bot_holdings h LEFT JOIN tougu_info i ON h.product_id = i.strategy_id "
        "WHERE h.bot_id = ? AND h.status = 'active' ORDER BY h.market_value DESC",
        (bot_id,),
    ).fetchall()

    snap = conn.execute(
        "SELECT * FROM bot_daily_snapshots WHERE bot_id = ? ORDER BY trade_date DESC LIMIT 1",
        (bot_id,),
    ).fetchone()

    result.append({
        "bot_id": bot_id,
        "initial_capital": a["initial_capital"],
        "cash": a["cash"],
        "total_value": snap["total_value"] if snap else a["initial_capital"],
        "net_value": snap["net_value"] if snap else 1.0,
        "cumulative_return_pct": snap["cumulative_return_pct"] if snap else 0,
        "daily_return_pct": snap["daily_return_pct"] if snap else 0,
        "max_drawdown": snap["max_drawdown"] if snap else 0,
        "trade_date": snap["trade_date"] if snap else None,
        "holdings": [
            {
                "product_id": h["product_id"],
                "product_name": h["strategy_name"] or h["product_id"],
                "amount": h["amount_invested"],
                "market_value": h["market_value"],
                "weight": h["weight"],
                "role": h["role"],
                "pnl": h["unrealized_pnl"],
                "pnl_pct": h["unrealized_pnl_pct"],
            }
            for h in holdings
        ],
    })

conn.close()
print(json.dumps(result, ensure_ascii=False))
