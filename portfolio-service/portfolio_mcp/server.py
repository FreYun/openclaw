"""
portfolio-mcp  —  A股模拟炒股组合管理 MCP 服务

支持的工具：
  账户管理 : create_account / get_account_info / list_user_accounts / deposit / withdraw
  交易操作 : buy_stock / sell_stock
  持仓查询 : get_positions / get_position_detail
  交易记录 : get_trade_history
  收益统计 : record_daily_snapshot / get_daily_returns / get_portfolio_curve / get_portfolio_summary

本 MCP 内置 tushare 实时行情接口，无需外部依赖即可完成查价、交易、持仓管理。
"""

import json
import math
import os
from datetime import date, datetime
from typing import Optional

import tushare as ts
from mcp.server.fastmcp import FastMCP

from portfolio_mcp import db

# Tushare token
_TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4")
ts.set_token(_TUSHARE_TOKEN)

mcp = FastMCP(
    "portfolio",
    instructions=(
        "A股模拟炒股组合管理服务。"
        "管理用户的模拟炒股账户，跟踪持仓、交易、收益。"
        "股票代码格式：000001.SZ / 600519.SH。"
        "金额单位：元（人民币）。数量单位：股。"
        "内置实时行情查询，买卖前可先调用 get_stock_quote 获取最新价格。"
        "每日收盘后应调用 record_daily_snapshot 记录快照，用于计算收益率和绘制曲线。"
    ),
)


def _ok(data) -> str:
    return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)


def _err(msg: str) -> str:
    return json.dumps({"status": "error", "message": msg}, ensure_ascii=False)


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


LOT_SIZE = 100  # A股1手=100股
MIN_FEE = 5.0   # 最低手续费5元


def _calc_max_lots(cash: float, price: float, fee_rate: float = 0.0003) -> int:
    """计算可用资金最多能买几手（1手=100股），扣除手续费后绝不超支"""
    if price <= 0 or cash <= 0:
        return 0
    lots = int(cash / (price * LOT_SIZE * (1 + fee_rate)))
    while lots > 0:
        amount = price * lots * LOT_SIZE
        fee = max(amount * fee_rate, MIN_FEE)
        if amount + fee <= cash:
            return lots
        lots -= 1
    return 0


# ═══════════════════════════════════════════════════════
# 账户管理
# ═══════════════════════════════════════════════════════

@mcp.tool()
def create_account(user_id: str, name: str = "默认账户", initial_capital: float = 1000000.0) -> str:
    """
    创建模拟炒股账户。

    Args:
        user_id:         用户标识（如用户名或ID）
        name:            账户名称，默认"默认账户"
        initial_capital:  初始资金（元），默认 100万

    Returns: JSON，含账户信息。
    """
    existing = db.get_account(user_id, name)
    if existing:
        return _err(f"账户 '{name}' 已存在，请使用其他名称")
    account = db.create_account(user_id, name, initial_capital)
    return _ok(account)


@mcp.tool()
def get_account_info(user_id: str, name: str = "默认账户") -> str:
    """
    获取账户基本信息（现金余额、初始资金、创建时间）。

    Args:
        user_id: 用户标识
        name:    账户名称，默认"默认账户"

    Returns: JSON，含 id / user_id / name / initial_capital / cash / created_at。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在，请先 create_account")
    return _ok(account)


@mcp.tool()
def list_user_accounts(user_id: str) -> str:
    """
    列出用户的所有模拟账户。

    Args:
        user_id: 用户标识

    Returns: JSON，账户列表。
    """
    accounts = db.list_accounts(user_id)
    return _ok(accounts)


@mcp.tool()
def deposit(user_id: str, amount: float, name: str = "默认账户") -> str:
    """
    向账户存入资金。

    Args:
        user_id: 用户标识
        amount:  存入金额（元），必须 > 0
        name:    账户名称

    Returns: JSON，含更新后的现金余额。
    """
    if amount <= 0:
        return _err("存入金额必须大于 0")
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")
    new_cash = account["cash"] + amount
    db.update_cash(account["id"], new_cash)
    # 同步调整初始资金，保证收益率计算准确
    new_initial = account["initial_capital"] + amount
    db.update_initial_capital(account["id"], new_initial)
    return _ok({"account_id": account["id"], "deposited": amount, "cash": new_cash,
                "initial_capital": new_initial})


@mcp.tool()
def withdraw(user_id: str, amount: float, name: str = "默认账户") -> str:
    """
    从账户取出资金。

    Args:
        user_id: 用户标识
        amount:  取出金额（元），必须 > 0
        name:    账户名称

    Returns: JSON，含更新后的现金余额。
    """
    if amount <= 0:
        return _err("取出金额必须大于 0")
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")
    if account["cash"] < amount:
        return _err(f"现金不足，当前现金 {account['cash']:.2f}，需要 {amount:.2f}")
    new_cash = account["cash"] - amount
    db.update_cash(account["id"], new_cash)
    # 同步调整初始资金，保证收益率计算准确
    new_initial = account["initial_capital"] - amount
    db.update_initial_capital(account["id"], new_initial)
    return _ok({"account_id": account["id"], "withdrawn": amount, "cash": new_cash,
                "initial_capital": new_initial})


# ═══════════════════════════════════════════════════════
# 交易操作
# ═══════════════════════════════════════════════════════

@mcp.tool()
def calc_max_buy(
    user_id: str,
    price: float,
    fee_rate: float = 0.0003,
    name: str = "默认账户",
) -> str:
    """
    计算当前可用资金最多能买多少手（1手=100股）。买入前应先调用此工具。

    Args:
        user_id:  用户标识
        price:    股票单价（元/股）
        fee_rate: 手续费率，默认万三(0.0003)
        name:     账户名称

    Returns: JSON，含 max_lots（最大手数）/ max_quantity（最大股数）/
             estimated_cost（预计花费含手续费）/ cash_remaining（买后剩余现金）。
    """
    if price <= 0:
        return _err("价格必须大于 0")

    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    max_lots = _calc_max_lots(account["cash"], price, fee_rate)
    max_qty = max_lots * LOT_SIZE
    amount = price * max_qty
    fee = max(amount * fee_rate, MIN_FEE) if max_qty > 0 else 0
    total_cost = amount + fee

    return _ok({
        "cash": round(account["cash"], 2),
        "price": price,
        "max_lots": max_lots,
        "max_quantity": max_qty,
        "estimated_cost": round(total_cost, 2),
        "estimated_fee": round(fee, 2),
        "cash_after_buy": round(account["cash"] - total_cost, 2) if max_lots > 0 else round(account["cash"], 2),
    })

@mcp.tool()
def buy_stock(
    user_id: str,
    ts_code: str,
    price: float,
    quantity: int,
    stock_name: str = "",
    reason: str = "",
    trade_date: str = "",
    fee_rate: float = 0.0003,
    name: str = "默认账户",
) -> str:
    """
    买入股票。A股最小交易单位为 1手=100股，quantity 必须是 100 的整数倍。
    买入前会自动检查可用资金，返回可买最大手数供参考。

    Args:
        user_id:    用户标识
        ts_code:    股票代码，如 "000001.SZ"
        price:      买入价格（元/股），可先调用 get_stock_quote 获取实时价
        quantity:   买入数量（股），必须是 100 的整数倍
        stock_name: 股票名称（可选，便于显示）
        reason:     买入理由（AI 决策原因，便于复盘）
        trade_date: 交易日期 YYYY-MM-DD，默认今天
        fee_rate:   手续费率，默认万三(0.0003)
        name:       账户名称

    Returns: JSON，含交易详情和更新后的持仓。
    """
    if quantity <= 0:
        return _err("买入数量必须大于 0")
    if quantity % LOT_SIZE != 0:
        return _err(f"买入数量必须是 {LOT_SIZE} 的整数倍（1手={LOT_SIZE}股），当前 {quantity} 股")
    if price <= 0:
        return _err("价格必须大于 0")

    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    max_lots = _calc_max_lots(account["cash"], price, fee_rate)
    requested_lots = quantity // LOT_SIZE

    amount = price * quantity
    fee = max(amount * fee_rate, MIN_FEE)
    total_cost = amount + fee

    if account["cash"] < total_cost:
        return _err(
            f"现金不足。需要 {total_cost:.2f}（含手续费 {fee:.2f}），"
            f"当前现金 {account['cash']:.2f}，最多可买 {max_lots} 手（{max_lots * LOT_SIZE} 股）"
        )

    if not trade_date:
        trade_date = _today()

    # 更新现金
    new_cash = account["cash"] - total_cost
    db.update_cash(account["id"], new_cash)

    # 更新持仓
    pos = db.get_position(account["id"], ts_code)
    if pos and pos["quantity"] > 0:
        old_qty = pos["quantity"]
        old_cost = pos["avg_cost"]
        new_qty = old_qty + quantity
        new_avg_cost = (old_cost * old_qty + price * quantity) / new_qty
        db.upsert_position(account["id"], ts_code, stock_name or pos["stock_name"],
                          new_qty, new_avg_cost, price)
    else:
        db.upsert_position(account["id"], ts_code, stock_name, quantity, price, price)

    # 记录交易
    trade = db.add_trade(account["id"], ts_code, stock_name, "buy",
                         quantity, price, amount, fee, trade_date, reason=reason)

    updated_pos = db.get_position(account["id"], ts_code)
    return _ok({
        "trade": trade,
        "position": updated_pos,
        "cash_remaining": new_cash,
    })


@mcp.tool()
def sell_stock(
    user_id: str,
    ts_code: str,
    price: float,
    quantity: int,
    stock_name: str = "",
    reason: str = "",
    trade_date: str = "",
    fee_rate: float = 0.0003,
    stamp_duty_rate: float = 0.0005,
    name: str = "默认账户",
) -> str:
    """
    卖出股票。A股最小交易单位为 1手=100股，quantity 必须是 100 的整数倍。

    Args:
        user_id:          用户标识
        ts_code:          股票代码，如 "000001.SZ"
        price:            卖出价格（元/股）
        quantity:         卖出数量（股），必须是 100 的整数倍
        stock_name:       股票名称（可选）
        reason:           卖出理由（AI 决策原因，便于复盘）
        trade_date:       交易日期 YYYY-MM-DD，默认今天
        fee_rate:         手续费率，默认万三(0.0003)
        stamp_duty_rate:  印花税率，默认万五(0.0005)，卖出时收取
        name:             账户名称

    Returns: JSON，含交易详情、盈亏和更新后的持仓。
    """
    if quantity <= 0:
        return _err("卖出数量必须大于 0")
    if quantity % LOT_SIZE != 0:
        return _err(f"卖出数量必须是 {LOT_SIZE} 的整数倍（1手={LOT_SIZE}股），当前 {quantity} 股")
    if price <= 0:
        return _err("价格必须大于 0")

    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    pos = db.get_position(account["id"], ts_code)
    if not pos or pos["quantity"] < quantity:
        available = pos["quantity"] if pos else 0
        available_lots = available // LOT_SIZE
        return _err(f"持仓不足。可卖 {available} 股（{available_lots} 手），试图卖 {quantity} 股")

    amount = price * quantity
    fee = max(amount * fee_rate, MIN_FEE)
    stamp_duty = amount * stamp_duty_rate
    total_fee = fee + stamp_duty
    net_income = amount - total_fee

    if not trade_date:
        trade_date = _today()

    # 计算本笔盈亏
    profit = (price - pos["avg_cost"]) * quantity - total_fee
    profit_pct = profit / (pos["avg_cost"] * quantity) * 100 if pos["avg_cost"] > 0 else 0

    # 更新现金
    new_cash = account["cash"] + net_income
    db.update_cash(account["id"], new_cash)

    # 更新持仓
    new_qty = pos["quantity"] - quantity
    if new_qty > 0:
        db.upsert_position(account["id"], ts_code, stock_name or pos["stock_name"],
                          new_qty, pos["avg_cost"], price)
    else:
        db.upsert_position(account["id"], ts_code, stock_name or pos["stock_name"],
                          0, 0, 0)

    # 记录交易
    trade = db.add_trade(account["id"], ts_code, stock_name or pos["stock_name"],
                         "sell", quantity, price, amount, total_fee, trade_date, reason=reason)

    return _ok({
        "trade": trade,
        "profit": round(profit, 2),
        "profit_pct": round(profit_pct, 2),
        "cash_remaining": new_cash,
    })


# ═══════════════════════════════════════════════════════
# 持仓查询
# ═══════════════════════════════════════════════════════

@mcp.tool()
def get_all_positions(user_id: str, name: str = "默认账户") -> str:
    """
    获取账户所有当前持仓。

    Args:
        user_id: 用户标识
        name:    账户名称

    Returns: JSON，持仓列表，含 ts_code / stock_name / quantity / avg_cost /
             current_price / market_value / profit / profit_pct。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    positions = db.get_positions(account["id"])
    result = []
    total_market_value = 0
    total_cost = 0
    for p in positions:
        mv = p["current_price"] * p["quantity"]
        cost = p["avg_cost"] * p["quantity"]
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0
        total_market_value += mv
        total_cost += cost
        result.append({
            "ts_code": p["ts_code"],
            "stock_name": p["stock_name"],
            "quantity": p["quantity"],
            "avg_cost": round(p["avg_cost"], 3),
            "current_price": round(p["current_price"], 3),
            "market_value": round(mv, 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 2),
        })

    return _ok({
        "positions": result,
        "total_market_value": round(total_market_value, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_market_value - total_cost, 2),
        "cash": round(account["cash"], 2),
        "total_assets": round(account["cash"] + total_market_value, 2),
    })


@mcp.tool()
def update_position_prices(user_id: str, prices: str, name: str = "默认账户") -> str:
    """
    批量更新持仓的当前价格（通常在获取实时行情后调用）。

    Args:
        user_id: 用户标识
        prices:  JSON 字符串，格式为 {"ts_code": price}，
                 如 '{"000001.SZ": 15.5, "600519.SH": 1800.0}'
        name:    账户名称

    Returns: JSON，更新结果。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    try:
        price_map = json.loads(prices)
    except json.JSONDecodeError:
        return _err("prices 格式错误，需要 JSON 字符串如 '{\"000001.SZ\": 15.5}'")

    updated = []
    for ts_code, price in price_map.items():
        db.update_position_price(account["id"], ts_code, float(price))
        updated.append(ts_code)

    return _ok({"updated": updated, "count": len(updated)})


# ═══════════════════════════════════════════════════════
# 交易记录
# ═══════════════════════════════════════════════════════

@mcp.tool()
def get_trade_history(
    user_id: str,
    ts_code: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 50,
    name: str = "默认账户",
) -> str:
    """
    查询交易历史记录。

    Args:
        user_id:    用户标识
        ts_code:    筛选股票代码（可选）
        start_date: 开始日期 YYYY-MM-DD（可选）
        end_date:   结束日期 YYYY-MM-DD（可选）
        limit:      返回条数上限，默认50
        name:       账户名称

    Returns: JSON，交易记录列表，含 ts_code / direction / quantity / price /
             amount / fee / trade_date。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    trades = db.get_trades(account["id"], ts_code=ts_code,
                           start_date=start_date, end_date=end_date, limit=limit)
    return _ok(trades)


# ═══════════════════════════════════════════════════════
# 收益统计 & 快照
# ═══════════════════════════════════════════════════════

@mcp.tool()
def record_daily_snapshot(user_id: str, snap_date: str = "", name: str = "默认账户") -> str:
    """
    记录当日账户快照（总资产、现金、股票市值、日收益率、累计收益率）。
    应在每日收盘后调用，在此之前需先用 update_position_prices 更新持仓价格。

    Args:
        user_id:   用户标识
        snap_date: 快照日期 YYYY-MM-DD，默认今天
        name:      账户名称

    Returns: JSON，含当日快照详情。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    if not snap_date:
        snap_date = _today()

    # 计算持仓市值
    positions = db.get_positions(account["id"])
    stock_value = sum(p["current_price"] * p["quantity"] for p in positions)
    total_value = account["cash"] + stock_value

    # 计算日收益率
    prev = db.get_latest_snapshot(account["id"])
    if prev and prev["date"] < snap_date:
        daily_return = (total_value - prev["total_value"]) / prev["total_value"] * 100
    else:
        daily_return = 0.0

    # 计算累计收益率
    cumulative_return = (total_value - account["initial_capital"]) / account["initial_capital"] * 100

    db.save_snapshot(account["id"], snap_date, total_value, account["cash"],
                     stock_value, round(daily_return, 4), round(cumulative_return, 4))

    return _ok({
        "date": snap_date,
        "total_value": round(total_value, 2),
        "cash": round(account["cash"], 2),
        "stock_value": round(stock_value, 2),
        "daily_return": round(daily_return, 4),
        "cumulative_return": round(cumulative_return, 4),
    })


@mcp.tool()
def get_daily_returns(
    user_id: str,
    start_date: str = "",
    end_date: str = "",
    name: str = "默认账户",
) -> str:
    """
    获取每日收益率序列。

    Args:
        user_id:    用户标识
        start_date: 开始日期 YYYY-MM-DD（可选）
        end_date:   结束日期 YYYY-MM-DD（可选）
        name:       账户名称

    Returns: JSON，每日快照列表，含 date / total_value / daily_return / cumulative_return。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    snapshots = db.get_snapshots(account["id"], start_date=start_date, end_date=end_date)
    result = [{
        "date": s["date"],
        "total_value": round(s["total_value"], 2),
        "cash": round(s["cash"], 2),
        "stock_value": round(s["stock_value"], 2),
        "daily_return": s["daily_return"],
        "cumulative_return": s["cumulative_return"],
    } for s in snapshots]

    return _ok(result)


@mcp.tool()
def get_portfolio_curve(
    user_id: str,
    start_date: str = "",
    end_date: str = "",
    name: str = "默认账户",
) -> str:
    """
    获取账户净值曲线数据，用于绘制收益走势图。
    返回以初始资金为基准的净值序列（初始净值=1.0）。

    Args:
        user_id:    用户标识
        start_date: 开始日期 YYYY-MM-DD（可选）
        end_date:   结束日期 YYYY-MM-DD（可选）
        name:       账户名称

    Returns: JSON，含 dates[] / net_values[] / daily_returns[] / cumulative_returns[]，
             以及 max_drawdown（最大回撤）等统计信息。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    snapshots = db.get_snapshots(account["id"], start_date=start_date, end_date=end_date)
    if not snapshots:
        return _ok({"dates": [], "net_values": [], "daily_returns": [],
                     "cumulative_returns": [], "max_drawdown": 0, "message": "暂无快照数据"})

    initial = account["initial_capital"]
    dates = [s["date"] for s in snapshots]
    net_values = [round(s["total_value"] / initial, 4) for s in snapshots]
    daily_returns = [s["daily_return"] for s in snapshots]
    cumulative_returns = [s["cumulative_return"] for s in snapshots]

    # 计算最大回撤
    peak = net_values[0]
    max_dd = 0
    for nv in net_values:
        if nv > peak:
            peak = nv
        dd = (peak - nv) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # 统计
    total_days = len(snapshots)
    positive_days = sum(1 for r in daily_returns if r and r > 0)
    negative_days = sum(1 for r in daily_returns if r and r < 0)

    # 年化收益率 & 夏普比率 & 波动率
    annualized_return = 0.0
    sharpe_ratio = 0.0
    volatility = 0.0
    if total_days > 1:
        total_ret = (net_values[-1] / net_values[0]) - 1
        annualized_return = round(((1 + total_ret) ** (252 / total_days) - 1) * 100, 4)
        valid_returns = [r for r in daily_returns if r is not None and r != 0]
        if valid_returns:
            avg_r = sum(valid_returns) / len(valid_returns)
            var = sum((r - avg_r) ** 2 for r in valid_returns) / len(valid_returns)
            daily_vol = math.sqrt(var)
            volatility = round(daily_vol * math.sqrt(252), 4)
            risk_free_daily = 2.0 / 252  # 年化2%无风险利率
            sharpe_ratio = round((avg_r - risk_free_daily) / daily_vol * math.sqrt(252), 4) if daily_vol > 0 else 0

    return _ok({
        "dates": dates,
        "net_values": net_values,
        "daily_returns": daily_returns,
        "cumulative_returns": cumulative_returns,
        "max_drawdown": round(max_dd, 4),
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe_ratio,
        "volatility": volatility,
        "total_days": total_days,
        "positive_days": positive_days,
        "negative_days": negative_days,
        "win_rate": round(positive_days / max(positive_days + negative_days, 1) * 100, 2),
        "latest_net_value": net_values[-1] if net_values else 1.0,
        "total_return": cumulative_returns[-1] if cumulative_returns else 0,
    })


@mcp.tool()
def get_portfolio_summary(user_id: str, name: str = "默认账户") -> str:
    """
    获取账户综合概览：资产总览 + 持仓 + 最近收益。

    Args:
        user_id: 用户标识
        name:    账户名称

    Returns: JSON，含账户信息、持仓汇总、最近快照。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    # 持仓
    positions = db.get_positions(account["id"])
    stock_value = sum(p["current_price"] * p["quantity"] for p in positions)
    total_value = account["cash"] + stock_value
    total_cost = sum(p["avg_cost"] * p["quantity"] for p in positions)
    total_profit = stock_value - total_cost
    cumulative_return = (total_value - account["initial_capital"]) / account["initial_capital"] * 100

    pos_list = []
    for p in positions:
        mv = p["current_price"] * p["quantity"]
        cost = p["avg_cost"] * p["quantity"]
        pnl = mv - cost
        pos_list.append({
            "ts_code": p["ts_code"],
            "stock_name": p["stock_name"],
            "quantity": p["quantity"],
            "avg_cost": round(p["avg_cost"], 3),
            "current_price": round(p["current_price"], 3),
            "market_value": round(mv, 2),
            "profit": round(pnl, 2),
            "profit_pct": round(pnl / cost * 100, 2) if cost > 0 else 0,
            "weight": round(mv / total_value * 100, 2) if total_value > 0 else 0,
        })

    # 最近5条快照
    latest_snaps = db.get_snapshots(account["id"])
    recent = latest_snaps[-5:] if len(latest_snaps) > 5 else latest_snaps

    # 最近5笔交易
    recent_trades = db.get_trades(account["id"], limit=5)

    return _ok({
        "account": {
            "user_id": account["user_id"],
            "name": account["name"],
            "initial_capital": account["initial_capital"],
            "cash": round(account["cash"], 2),
            "stock_value": round(stock_value, 2),
            "total_value": round(total_value, 2),
            "total_profit": round(total_profit, 2),
            "cumulative_return": round(cumulative_return, 4),
            "position_count": len(positions),
        },
        "positions": pos_list,
        "recent_snapshots": [{
            "date": s["date"],
            "total_value": round(s["total_value"], 2),
            "daily_return": s["daily_return"],
        } for s in recent],
        "recent_trades": recent_trades,
    })


@mcp.tool()
def batch_snapshot_all(snap_date: str = "") -> str:
    """
    一次性为所有账户记录每日快照。适用于每日收盘后的批量操作。
    调用前需确保所有账户的持仓价格已通过 update_position_prices 更新。

    Args:
        snap_date: 快照日期 YYYY-MM-DD，默认今天

    Returns: JSON，所有账户的快照结果汇总。
    """
    if not snap_date:
        snap_date = _today()

    all_accounts = db.get_all_accounts()
    if not all_accounts:
        return _ok({"message": "没有任何账户", "count": 0})

    results = []
    for account in all_accounts:
        positions = db.get_positions(account["id"])
        stock_value = sum(p["current_price"] * p["quantity"] for p in positions)
        total_value = account["cash"] + stock_value

        prev = db.get_latest_snapshot(account["id"])
        if prev and prev["date"] < snap_date:
            daily_return = (total_value - prev["total_value"]) / prev["total_value"] * 100
        else:
            daily_return = 0.0

        cumulative_return = (total_value - account["initial_capital"]) / account["initial_capital"] * 100

        db.save_snapshot(account["id"], snap_date, total_value, account["cash"],
                         stock_value, round(daily_return, 4), round(cumulative_return, 4))

        results.append({
            "user_id": account["user_id"],
            "account_name": account["name"],
            "total_value": round(total_value, 2),
            "daily_return": round(daily_return, 4),
            "cumulative_return": round(cumulative_return, 4),
        })

    return _ok({"date": snap_date, "count": len(results), "snapshots": results})


@mcp.tool()
def get_leaderboard(snap_date: str = "") -> str:
    """
    获取所有虚拟人的收益排行榜，按累计收益率排名。

    Args:
        snap_date: 指定日期的排名 YYYY-MM-DD，默认使用最新快照

    Returns: JSON，排行榜列表，含 rank / user_id / account_name / total_value /
             cumulative_return / daily_return / annualized_return。
    """
    all_accounts = db.get_all_accounts()
    if not all_accounts:
        return _ok({"message": "没有任何账户", "leaderboard": []})

    entries = []
    for account in all_accounts:
        if snap_date:
            snaps = db.get_snapshots(account["id"], start_date=snap_date, end_date=snap_date)
            snap = snaps[0] if snaps else None
        else:
            snap = db.get_latest_snapshot(account["id"])

        if snap:
            # 计算年化
            all_snaps = db.get_snapshots(account["id"])
            annualized = 0.0
            if len(all_snaps) > 1:
                first_val = all_snaps[0]["total_value"]
                last_val = snap["total_value"]
                days = len(all_snaps)
                total_ret = (last_val / first_val) - 1
                annualized = round(((1 + total_ret) ** (252 / days) - 1) * 100, 4)

            entries.append({
                "user_id": account["user_id"],
                "account_name": account["name"],
                "initial_capital": account["initial_capital"],
                "total_value": round(snap["total_value"], 2),
                "daily_return": snap["daily_return"],
                "cumulative_return": snap["cumulative_return"],
                "annualized_return": annualized,
                "snap_date": snap["date"],
            })
        else:
            # 没有快照，用当前数据
            positions = db.get_positions(account["id"])
            stock_value = sum(p["current_price"] * p["quantity"] for p in positions)
            total_value = account["cash"] + stock_value
            cum_ret = (total_value - account["initial_capital"]) / account["initial_capital"] * 100

            entries.append({
                "user_id": account["user_id"],
                "account_name": account["name"],
                "initial_capital": account["initial_capital"],
                "total_value": round(total_value, 2),
                "daily_return": 0,
                "cumulative_return": round(cum_ret, 4),
                "annualized_return": 0,
                "snap_date": "N/A",
            })

    # 按累计收益率降序排名
    entries.sort(key=lambda x: x["cumulative_return"], reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    return _ok({"leaderboard": entries, "total_accounts": len(entries)})


# ═══════════════════════════════════════════════════════
# 实时盘中盈亏
# ═══════════════════════════════════════════════════════

def _ts_code_to_raw(ts_code: str) -> str:
    """将 ts_code（如 000001.SZ）转为纯数字代码（000001），供旧版 API 使用。"""
    return ts_code.split(".")[0]


def _fetch_realtime_prices(ts_codes: list[str]) -> dict[str, dict]:
    """
    调用 tushare 旧版实时行情接口，返回 {ts_code: {price, name, change_pct, ...}} 。
    """
    if not ts_codes:
        return {}

    raw_codes = [_ts_code_to_raw(c) for c in ts_codes]
    # 建立 raw_code -> ts_code 的映射
    raw_to_ts = {}
    for raw, tsc in zip(raw_codes, ts_codes):
        raw_to_ts[raw] = tsc

    df = ts.get_realtime_quotes(raw_codes)
    if df is None or df.empty:
        return {}

    result = {}
    for _, row in df.iterrows():
        code = row["code"]
        tsc = raw_to_ts.get(code, code)
        price = float(row["price"]) if row["price"] else 0
        pre_close = float(row["pre_close"]) if row["pre_close"] else 0
        change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0
        result[tsc] = {
            "name": row.get("name", ""),
            "price": price,
            "pre_close": pre_close,
            "open": float(row["open"]) if row["open"] else 0,
            "high": float(row["high"]) if row["high"] else 0,
            "low": float(row["low"]) if row["low"] else 0,
            "volume": float(row["volume"]) if row["volume"] else 0,
            "amount": float(row["amount"]) if row["amount"] else 0,
            "change_pct": round(change_pct, 2),
        }
    return result


@mcp.tool()
def get_stock_quote(codes: str) -> str:
    """
    查询股票实时行情（当前价、涨跌幅、开高低、成交量等）。
    可在买卖前查价，或用于研究个股。

    Args:
        codes: 股票代码，逗号分隔，如 "000001.SZ,600519.SH"

    Returns: JSON，每只股票的实时行情数据。
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return _err("请提供至少一个股票代码")

    try:
        result = _fetch_realtime_prices(code_list)
    except Exception as e:
        return _err(f"获取实时行情失败: {str(e)}")

    if not result:
        return _err("获取行情返回为空，可能不在交易时段或代码错误")

    quotes = []
    for tsc in code_list:
        rt = result.get(tsc)
        if rt:
            quotes.append({
                "ts_code": tsc,
                "name": rt["name"],
                "price": rt["price"],
                "pre_close": rt["pre_close"],
                "change_pct": rt["change_pct"],
                "open": rt["open"],
                "high": rt["high"],
                "low": rt["low"],
                "volume": rt["volume"],
                "amount": rt["amount"],
            })
    return _ok(quotes)


def _ts_code_to_index_symbol(ts_code: str) -> str:
    """将指数 ts_code（如 000001.SH）转为旧版 API 前缀格式（sh000001）。"""
    parts = ts_code.split(".")
    if len(parts) == 2:
        code, exchange = parts
        return exchange.lower() + code
    return ts_code


def _fetch_realtime_index_prices(ts_codes: list[str]) -> dict[str, dict]:
    """
    调用 tushare 旧版实时行情接口获取指数行情，返回 {ts_code: {price, name, ...}} 。
    """
    if not ts_codes:
        return {}

    symbols = [_ts_code_to_index_symbol(c) for c in ts_codes]
    sym_to_ts = {}
    for sym, tsc in zip(symbols, ts_codes):
        sym_to_ts[sym] = tsc

    df = ts.get_realtime_quotes(symbols)
    if df is None or df.empty:
        return {}

    result = {}
    for _, row in df.iterrows():
        code = row["code"]
        # 匹配回 ts_code：code 可能是 "sh000001" 或 "000001"
        tsc = sym_to_ts.get(code, code)
        # 也尝试用原始 symbol 匹配
        for sym, tc in sym_to_ts.items():
            if sym == code or sym.endswith(code):
                tsc = tc
                break
        price = float(row["price"]) if row["price"] else 0
        pre_close = float(row["pre_close"]) if row["pre_close"] else 0
        change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0
        result[tsc] = {
            "name": row.get("name", ""),
            "price": price,
            "pre_close": pre_close,
            "open": float(row["open"]) if row["open"] else 0,
            "high": float(row["high"]) if row["high"] else 0,
            "low": float(row["low"]) if row["low"] else 0,
            "volume": float(row["volume"]) if row["volume"] else 0,
            "amount": float(row["amount"]) if row["amount"] else 0,
            "change_pct": round(change_pct, 2),
        }
    return result


@mcp.tool()
def get_index_quote(codes: str) -> str:
    """
    查询指数实时行情（当前点位、涨跌幅、开高低、成交量等）。

    Args:
        codes: 指数代码，逗号分隔，如 "000001.SH,399001.SZ,000300.SH"

    常用指数：
        000001.SH 上证综指 / 399001.SZ 深证成指 / 000300.SH 沪深300
        000905.SH 中证500 / 399006.SZ 创业板指 / 000688.SH 科创50

    Returns: JSON，每只指数的实时行情数据。
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return _err("请提供至少一个指数代码")

    try:
        result = _fetch_realtime_index_prices(code_list)
    except Exception as e:
        return _err(f"获取指数行情失败: {str(e)}")

    if not result:
        return _err("获取指数行情返回为空，可能不在交易时段或代码错误")

    quotes = []
    for tsc in code_list:
        rt = result.get(tsc)
        if rt:
            quotes.append({
                "ts_code": tsc,
                "name": rt["name"],
                "price": rt["price"],
                "pre_close": rt["pre_close"],
                "change_pct": rt["change_pct"],
                "open": rt["open"],
                "high": rt["high"],
                "low": rt["low"],
                "volume": rt["volume"],
                "amount": rt["amount"],
            })
    return _ok(quotes)


@mcp.tool()
def auto_daily_update(snap_date: str = "") -> str:
    """
    一键盘后更新：自动获取所有持仓股票的最新价格，更新持仓现价，并为所有账户记录每日快照。
    替代手动三步操作（查价 → update_position_prices → batch_snapshot_all）。

    Args:
        snap_date: 快照日期 YYYY-MM-DD，默认今天

    Returns: JSON，更新结果汇总（更新了多少只股票、各账户快照数据）。
    """
    if not snap_date:
        snap_date = _today()

    # 1. 收集所有账户的持仓股票
    all_accounts = db.get_all_accounts()
    if not all_accounts:
        return _ok({"message": "没有任何账户", "count": 0})

    all_ts_codes = set()
    for account in all_accounts:
        positions = db.get_positions(account["id"])
        for p in positions:
            all_ts_codes.add(p["ts_code"])

    if not all_ts_codes:
        return _ok({"message": "所有账户均无持仓", "count": 0})

    # 2. 批量获取实时价格
    try:
        realtime = _fetch_realtime_prices(list(all_ts_codes))
    except Exception as e:
        return _err(f"获取实时行情失败: {str(e)}")

    if not realtime:
        return _err("获取行情返回为空，可能不在交易时段或网络异常")

    # 3. 更新所有账户的持仓价格
    updated_codes = []
    for account in all_accounts:
        positions = db.get_positions(account["id"])
        for p in positions:
            rt = realtime.get(p["ts_code"])
            if rt and rt["price"] > 0:
                db.update_position_price(account["id"], p["ts_code"], rt["price"])
                if p["ts_code"] not in updated_codes:
                    updated_codes.append(p["ts_code"])

    # 4. 为所有账户记录快照
    snapshots = []
    for account in all_accounts:
        positions = db.get_positions(account["id"])
        stock_value = sum(p["current_price"] * p["quantity"] for p in positions)
        total_value = account["cash"] + stock_value

        prev = db.get_latest_snapshot(account["id"])
        if prev and prev["date"] < snap_date:
            daily_return = (total_value - prev["total_value"]) / prev["total_value"] * 100
        else:
            daily_return = 0.0

        cumulative_return = (total_value - account["initial_capital"]) / account["initial_capital"] * 100

        db.save_snapshot(account["id"], snap_date, total_value, account["cash"],
                         stock_value, round(daily_return, 4), round(cumulative_return, 4))

        snapshots.append({
            "user_id": account["user_id"],
            "account_name": account["name"],
            "total_value": round(total_value, 2),
            "daily_return": round(daily_return, 4),
            "cumulative_return": round(cumulative_return, 4),
        })

    return _ok({
        "date": snap_date,
        "prices_updated": len(updated_codes),
        "updated_codes": updated_codes,
        "accounts_snapshot": len(snapshots),
        "snapshots": snapshots,
    })


@mcp.tool()
def get_realtime_pnl(user_id: str, name: str = "默认账户") -> str:
    """
    盘中实时查看账户收益。自动通过 tushare 获取所有持仓股票的最新实时价格，
    计算每只股票和整个账户的浮动盈亏，并同步更新持仓现价。

    适用场景：交易时段内想快速了解当前账户盈亏情况，无需手动查价。

    Args:
        user_id: 用户标识
        name:    账户名称，默认"默认账户"

    Returns: JSON，含每只持仓的实时价格、涨跌幅、浮动盈亏，以及账户汇总信息。
    """
    account = db.get_account(user_id, name)
    if not account:
        return _err(f"账户 '{name}' 不存在")

    positions = db.get_positions(account["id"])
    if not positions:
        return _ok({
            "message": "当前无持仓",
            "cash": round(account["cash"], 2),
            "total_assets": round(account["cash"], 2),
        })

    # 获取所有持仓的 ts_code
    ts_codes = [p["ts_code"] for p in positions]

    # 调用 tushare 实时行情
    try:
        realtime = _fetch_realtime_prices(ts_codes)
    except Exception as e:
        return _err(f"获取实时行情失败: {str(e)}")

    if not realtime:
        return _err("获取实时行情返回为空，可能不在交易时段或网络异常")

    # 计算每只股票的盈亏
    pos_details = []
    total_market_value = 0
    total_cost = 0
    total_today_pnl = 0  # 今日盈亏（基于昨收）

    for p in positions:
        tsc = p["ts_code"]
        rt = realtime.get(tsc)
        if rt and rt["price"] > 0:
            live_price = rt["price"]
            pre_close = rt["pre_close"]
            change_pct = rt["change_pct"]
            stock_name = rt["name"] or p["stock_name"]
        else:
            # 实时数据缺失，用数据库中的现价
            live_price = p["current_price"]
            pre_close = 0
            change_pct = 0
            stock_name = p["stock_name"]

        qty = p["quantity"]
        avg_cost = p["avg_cost"]
        mv = live_price * qty
        cost = avg_cost * qty
        profit = mv - cost
        profit_pct = (profit / cost * 100) if cost > 0 else 0

        # 今日盈亏 = (实时价 - 昨收) * 持仓量
        today_pnl = (live_price - pre_close) * qty if pre_close > 0 else 0

        total_market_value += mv
        total_cost += cost
        total_today_pnl += today_pnl

        # 同步更新持仓现价到数据库
        if rt and rt["price"] > 0:
            db.update_position_price(account["id"], tsc, live_price)

        pos_details.append({
            "ts_code": tsc,
            "stock_name": stock_name,
            "quantity": qty,
            "avg_cost": round(avg_cost, 3),
            "live_price": round(live_price, 3),
            "pre_close": round(pre_close, 3),
            "change_pct": change_pct,
            "market_value": round(mv, 2),
            "total_profit": round(profit, 2),
            "total_profit_pct": round(profit_pct, 2),
            "today_pnl": round(today_pnl, 2),
        })

    total_assets = account["cash"] + total_market_value
    total_profit = total_market_value - total_cost
    cumulative_return = (total_assets - account["initial_capital"]) / account["initial_capital"] * 100

    return _ok({
        "positions": pos_details,
        "summary": {
            "cash": round(account["cash"], 2),
            "stock_value": round(total_market_value, 2),
            "total_assets": round(total_assets, 2),
            "initial_capital": account["initial_capital"],
            "total_profit": round(total_profit, 2),
            "cumulative_return": round(cumulative_return, 4),
            "today_pnl": round(total_today_pnl, 2),
        },
    })


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Portfolio MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18790)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
