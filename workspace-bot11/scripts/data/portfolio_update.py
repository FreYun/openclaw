"""
旅游基金账户 — 每日持仓收益更新
读取 holdings.json → 使用 akshare 获取最新净值 → 估算当日市值变动 → 生成快照和摘要

用法:
    python scripts/data/portfolio_update.py           # 使用 akshare（默认）
    python scripts/data/portfolio_update.py akshare   # 同上，显式指定
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import akshare as ak

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOLDINGS_PATH = os.path.join(WORKSPACE, "positions", "holdings.json")
HISTORY_DIR = os.path.join(WORKSPACE, "portfolio-history")
SUMMARY_PATH = os.path.join(WORKSPACE, "portfolio-summary.md")


def load_holdings():
    with open(HOLDINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_holdings(data):
    with open(HOLDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ts_code_to_em_code(ts_code):
    """将 ts_code（如 024000.OF / 167301.SZ）转为东方财富 6 位代码"""
    if not ts_code:
        return ""
    return str(ts_code).split(".")[0].strip()


def fetch_nav_akshare(ts_code):
    """通过 akshare（天天基金）获取基金最新净值"""
    try:
        code = _ts_code_to_em_code(ts_code)
        if not code:
            return None
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return None
        df = df.sort_values("净值日期", ascending=False)
        latest = df.iloc[0]
        nav = float(latest["单位净值"])
        nav_date = str(latest["净值日期"]).replace("-", "")
        return {"nav": nav, "daily_pct": None, "nav_date": nav_date}
    except Exception as e:
        print(f"  [akshare] {ts_code} 净值获取失败: {e}")
        return None


def update_holdings(data, source="akshare"):
    """获取最新净值，按【份额 × 净值】优先计算市值（默认使用 akshare）"""
    if source != "akshare":
        print(f"\n暂未实现 {source} 数据源，自动改用 akshare")
        source = "akshare"

    print(f"\n数据源: {source}")
    print("=" * 60)

    results = []
    for h in data["holdings"]:
        if h.get("status") != "holding":
            results.append(h)
            continue

        code = h["ts_code"]
        print(f"\n获取 {h['name']} ({code}) ...")

        nav_info = None
        nav_info = fetch_nav_akshare(code)

        # 记录最新净值信息
        if nav_info:
            h["last_nav"] = nav_info["nav"]
            h["last_nav_date"] = nav_info["nav_date"]
            print(f"  净值日期: {nav_info['nav_date']}  净值: {nav_info['nav']}")
        else:
            print(f"  未获取到净值数据，保持原值（无法按份额更新市值）")

        # 优先按份额 × 净值计算市值和成本
        units = h.get("units")
        avg_nav = h.get("avg_nav")
        fee = h.get("fee") or 0.0

        if units is not None and avg_nav is not None and nav_info:
            try:
                units_f = float(units)
                avg_nav_f = float(avg_nav)
                fee_f = float(fee)
                nav_f = float(nav_info["nav"])

                # 成本 = 份额 × 平均成本净值 + 手续费
                cost = round(units_f * avg_nav_f + fee_f, 2)
                value = round(units_f * nav_f, 2)

                h["cost"] = cost
                h["current_value"] = value
                h["profit"] = round(value - cost, 2)
                h["profit_pct"] = round((value - cost) / cost * 100, 2) if cost > 0 else None

                print(f"  持仓份额: {units_f}  平均成本净值: {avg_nav_f}")
                print(f"  成本(含手续费): {cost:.2f}  市值(按最新净值): {value:.2f}")
                print(f"  累计收益: {h['profit']:+.2f} 元 ({h['profit_pct']:+.2f}% )" if h["profit_pct"] is not None else "")
            except Exception as e:
                print(f"  [warning] 份额/净值计算失败，退回金额口径: {e}")
        else:
            # 没有份额信息时，可以根据当前持仓金额和净值近似反推份额
            if nav_info:
                nav_f = float(nav_info["nav"])
                amount = h.get("current_value") or h.get("cost")
                if amount is not None and nav_f > 0:
                    try:
                        amt_f = float(amount)
                        # 近似反推历史持仓份额：units ≈ 持仓金额 / 当前净值
                        approx_units = round(amt_f / nav_f, 4)
                        if h.get("units") is None:
                            h["units"] = approx_units
                        # 如果有成本，则用成本 / 份额反推平均成本净值；否则先用当前净值作为起点
                        if h.get("avg_nav") is None:
                            if h.get("cost") is not None and approx_units > 0:
                                cost_f = float(h["cost"])
                                h["avg_nav"] = round(cost_f / approx_units, 4)
                            else:
                                h["avg_nav"] = nav_f
                        print(f"  未显式配置 units/avg_nav，按历史金额近似回推：units ≈ {h.get('units')}，avg_nav ≈ {h.get('avg_nav')}")
                    except Exception as e:
                        print(f"  未配置 units/avg_nav，且自动回推失败，暂时按原 cost/current_value 金额口径统计: {e}")
                else:
                    print("  未配置 units/avg_nav，暂时按原 cost/current_value 金额口径统计。")

        results.append(h)

    data["holdings"] = results
    data["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    return data


def calc_account_summary(data):
    """计算账户汇总（已确认持仓 + 待确认金额）"""
    total_cost = 0
    total_value = 0
    valid_count = 0

    pending_amount = 0
    pending_count = 0

    for h in data["holdings"]:
        status = h.get("status")
        if status == "holding":
            if h.get("current_value") is not None:
                total_value += h["current_value"]
                valid_count += 1
            if h.get("cost") is not None:
                total_cost += h["cost"]
        elif status == "pending":
            # 待确认金额：优先用 cost，没有则用 current_value
            amt = h.get("cost") or h.get("current_value")
            if amt is not None:
                try:
                    pending_amount += float(amt)
                    pending_count += 1
                except Exception:
                    pass

    total_profit = round(total_value - total_cost, 2)
    total_profit_pct = round(total_profit / total_cost * 100, 2) if total_cost > 0 else 0

    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_profit": total_profit,
        "total_profit_pct": total_profit_pct,
        "holdings_count": valid_count,
        "pending_amount": round(pending_amount, 2),
        "pending_count": pending_count,
    }


def generate_daily_snapshot(data, summary, today):
    """生成每日快照 markdown 文件"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    path = os.path.join(HISTORY_DIR, f"{today}.md")

    lines = [
        f"# 旅游基金日报 — {today}\n",
        f"## 账户概览\n",
        f"| 项目 | 数值 |",
        f"|------|------|",
        f"| 总市值 | {summary['total_value']:.2f} 元 |",
        f"| 总成本 | {summary['total_cost']:.2f} 元 |",
        f"| 累计收益 | {summary['total_profit']:+.2f} 元 ({summary['total_profit_pct']:+.2f}%) |",
        f"| 持仓数量 | {summary['holdings_count']} 只 |",
        f"| 待确认金额 | {summary['pending_amount']:.2f} 元（{summary['pending_count']} 笔） |",
        f"",
        f"## 持仓明细\n",
        f"| 基金代码 | 基金名称 | 成本 | 市值 | 收益 | 收益率 | 方向 |",
        f"|----------|----------|------|------|------|--------|------|",
    ]

    for h in data["holdings"]:
        if h["status"] != "holding":
            continue
        cost_str = f"{h['cost']:.2f}" if h["cost"] is not None else "—"
        value_str = f"{h['current_value']:.2f}" if h["current_value"] is not None else "—"
        profit_str = f"{h['profit']:+.2f}" if h["profit"] is not None else "—"
        pct_str = f"{h['profit_pct']:+.2f}%" if h["profit_pct"] is not None else "—"
        lines.append(f"| {h['ts_code']} | {h['name']} | {cost_str} | {value_str} | {profit_str} | {pct_str} | {h['direction']} |")

    lines.append("")
    lines.append(f"_更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n日报已保存: {path}")
    return path


def generate_summary(data, summary):
    """生成/覆盖 portfolio-summary.md（始终反映最新状态）"""
    lines = [
        f"# 旅游基金账户总览\n",
        f"> 最后更新: {data['meta']['last_updated']}\n",
        f"## 账户概览\n",
        f"| 项目 | 数值 |",
        f"|------|------|",
        f"| 总市值 | {summary['total_value']:.2f} 元 |",
        f"| 总成本 | {summary['total_cost']:.2f} 元 |",
        f"| 累计收益 | {summary['total_profit']:+.2f} 元 |",
        f"| 累计收益率 | {summary['total_profit_pct']:+.2f}% |",
        f"| 持仓数量 | {summary['holdings_count']} 只 |",
        f"| 待确认金额 | {summary['pending_amount']:.2f} 元（{summary['pending_count']} 笔） |",
        f"",
        f"## 持仓明细\n",
        f"| 基金代码 | 名称 | 成本 | 市值 | 收益 | 收益率 | 方向 | 备注 |",
        f"|----------|------|------|------|------|--------|------|------|",
    ]

    for h in data["holdings"]:
        if h["status"] != "holding":
            continue
        cost_str = f"{h['cost']:.2f}" if h["cost"] is not None else "—"
        value_str = f"{h['current_value']:.2f}" if h["current_value"] is not None else "—"
        profit_str = f"{h['profit']:+.2f}" if h["profit"] is not None else "—"
        pct_str = f"{h['profit_pct']:+.2f}%" if h["profit_pct"] is not None else "—"
        lines.append(f"| {h['ts_code']} | {h['name']} | {cost_str} | {value_str} | {profit_str} | {pct_str} | {h['direction']} | {h['note']} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 累计收益率计算公式")
    lines.append("")
    lines.append("- 单只基金: `(当前市值 - 投入成本) / 投入成本 × 100%`")
    lines.append("- 整个账户: `(账户总市值 - 账户历史净投入) / 账户历史净投入 × 100%`")
    lines.append("")
    lines.append("_此文件由 `scripts/data/portfolio_update.py` 自动生成_")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"总览已保存: {SUMMARY_PATH}")


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "akshare"
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"旅游基金每日更新 — {today}")

    data = load_holdings()
    data = update_holdings(data, source=source)
    save_holdings(data)

    summary = calc_account_summary(data)

    print(f"\n{'=' * 60}")
    print(f"账户汇总")
    print(f"{'=' * 60}")
    print(f"  总市值:   {summary['total_value']:.2f} 元")
    print(f"  总成本:   {summary['total_cost']:.2f} 元")
    print(f"  累计收益: {summary['total_profit']:+.2f} 元 ({summary['total_profit_pct']:+.2f}%)")

    generate_daily_snapshot(data, summary, today)
    generate_summary(data, summary)

    print("\n更新完成。")


if __name__ == "__main__":
    main()
