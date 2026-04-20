"""S5 T+1 验证 — 两种模式:

1. live (默认): 当日盘中跑, 用 akshare stock_intraday_em 拿实时分时
   判定: triggered / gap_up_skip / triggered_late / stop_hit / wait
   只适用于"今天验证昨天的 candidate"场景

2. backtest: 历史回放, 用 research-mcp get_stock_daily_quote 拿 T+1 日线 OHLC
   判定: triggered_at_open / triggered_intraday / gap_up_skip / gap_down_skip
         + 日内结局: stop_hit / hit_target_1 / hit_target_2 / close_hold
   用于在已有历史数据上跑 "T 日选股 → T+1 是否盈利" 的真实检验

用法:
    # live 模式 (今日 T+1 验证昨日候选)
    python3 verify.py --date=2026-04-09 \\
        --candidates-json=/path/to/candidates_2026-04-08.json

    # backtest 模式 (历史回放)
    python3 verify.py --date=2026-04-09 --mode=backtest \\
        --candidates-json=/path/to/candidates_2026-04-08.json

输出:
    {output_dir}/verification_YYYY-MM-DD.md/.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from data_fetcher import fetch_intraday, shift_trading_days, fetch_klines_batch


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def find_t_minus_1_candidates(t1_date: str, output_dir: str) -> tuple:
    """根据 T+1 日期反推 T 日 candidate 文件。"""
    t_date = shift_trading_days(t1_date, -1)
    candidates_path = os.path.join(output_dir, f"candidates_{t_date}.json")
    if not os.path.exists(candidates_path):
        # 兼容: 也试一下日历日 -1
        prev = (datetime.strptime(t1_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        alt = os.path.join(output_dir, f"candidates_{prev}.json")
        if os.path.exists(alt):
            return prev, alt
        raise FileNotFoundError(f"找不到 candidates_{t_date}.json 或 candidates_{prev}.json")
    return t_date, candidates_path


def verify_one_backtest(candidate: dict, t1_bar: dict) -> dict:
    """历史回放: 基于 T+1 日线 OHLC 判定入场 + 当日结局。

    两阶段:
      阶段 1 — 入场判定 (open-based):
        gap_up_skip       T+1 open > entry_high
        triggered_at_open open ∈ [entry_low, entry_high] (实际买入价 = open)
        triggered_intraday open < entry_low 且 day high ≥ entry_low (买入价 = entry_low)
        gap_down_skip     open < entry_low 且 day high < entry_low (全天没回到入场区)

      阶段 2 — 如果触发, 当日结局 (OHLC-based, 止损优先):
        stop_hit    T+1 low ≤ stop_loss (假设日内先触发止损)
        hit_target_2 否则 T+1 high ≥ target_2
        hit_target_1 否则 T+1 high ≥ target_1
        close_hold  以上都没有, 持有到收盘, 退出价 = T+1 close

    单日盈亏 pct = (exit_price - entry_price) / entry_price * 100
    未触发时 pnl_pct = None

    Args:
        candidate: select.py 输出的单只 candidate
        t1_bar: T+1 当天的日线 bar (dict, 至少含 open/high/low/close)
    """
    entry_low = candidate["entry"]["zone_low"]
    entry_high = candidate["entry"]["zone_high"]
    stop_loss = candidate["stop_loss"]["price"]
    target_1 = candidate["target_1"]["price"]
    target_2 = candidate["target_2"]["price"]

    t1_open = t1_bar["open"]
    t1_high = t1_bar["high"]
    t1_low = t1_bar["low"]
    t1_close = t1_bar["close"]

    # 阶段 1: 入场判定
    entry_price = None
    if t1_open > entry_high:
        return {
            "status": "gap_up_skip",
            "entry_price": None,
            "exit_price": None,
            "exit_reason": None,
            "pnl_pct": None,
            "t1_open": t1_open,
            "t1_high": t1_high,
            "t1_low": t1_low,
            "t1_close": t1_close,
            "note": f"T+1 开盘 {t1_open:.2f} > 入场区上沿 {entry_high:.2f}, 放弃",
        }

    if entry_low <= t1_open <= entry_high:
        entry_price = t1_open
        entry_status = "triggered_at_open"
        entry_note = f"T+1 开盘 {t1_open:.2f} 命中入场区, 买入价 = {entry_price:.2f}"
    elif t1_open < entry_low and t1_high >= entry_low:
        entry_price = entry_low  # 保守: 按入场区下沿回踩买
        entry_status = "triggered_intraday"
        entry_note = f"T+1 低开 {t1_open:.2f}, 日内最高 {t1_high:.2f} 回到入场区, 买入价 = {entry_price:.2f}"
    else:
        return {
            "status": "gap_down_skip",
            "entry_price": None,
            "exit_price": None,
            "exit_reason": None,
            "pnl_pct": None,
            "t1_open": t1_open,
            "t1_high": t1_high,
            "t1_low": t1_low,
            "t1_close": t1_close,
            "note": (
                f"T+1 低开 {t1_open:.2f} 且日内最高 {t1_high:.2f} < 入场区下沿 {entry_low:.2f}, "
                f"全天未进入入场区"
            ),
        }

    # 阶段 2: 当日结局判定 (保守: 止损优先)
    if t1_low <= stop_loss:
        exit_price = stop_loss
        exit_reason = "stop_hit"
        final_status = "stop_hit"
    elif t1_high >= target_2:
        exit_price = target_2
        exit_reason = "hit_target_2"
        final_status = "hit_target_2"
    elif t1_high >= target_1:
        exit_price = target_1
        exit_reason = "hit_target_1"
        final_status = "hit_target_1"
    else:
        exit_price = t1_close
        exit_reason = "close_hold"
        final_status = "close_hold"

    pnl_pct = (exit_price - entry_price) / entry_price * 100

    return {
        "status": final_status,
        "entry_status": entry_status,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "exit_reason": exit_reason,
        "pnl_pct": round(pnl_pct, 2),
        "t1_open": t1_open,
        "t1_high": t1_high,
        "t1_low": t1_low,
        "t1_close": t1_close,
        "note": f"{entry_note}; 日内 {exit_reason} → {exit_price:.2f}, 盈亏 {pnl_pct:+.2f}%",
    }


def verify_one(candidate: dict) -> dict:
    """对单只 candidate 拉分时, 判定状态。

    Returns:
        {"status": str, "open_price": float | None, "current": float | None, "note": str}
    """
    code = candidate["code"]
    entry_low = candidate["entry"]["zone_low"]
    entry_high = candidate["entry"]["zone_high"]
    stop_loss = candidate["stop_loss"]["price"]

    df = fetch_intraday(code)
    if df is None or df.empty:
        return {
            "status": "no_data",
            "open_price": None,
            "current": None,
            "note": "分时数据为空 (可能停牌)",
        }

    # akshare stock_intraday_em 字段: 时间 成交价 手数 买卖盘性质
    # 第一行 = 开盘成交; 最后一行 = 当前最新
    try:
        first_price = float(df.iloc[0]["成交价"])
        last_price = float(df.iloc[-1]["成交价"])
    except Exception as e:
        return {
            "status": "parse_error",
            "open_price": None,
            "current": None,
            "note": f"分时数据解析失败: {e}",
        }

    # 1. 当前价已破止损 — 立即弃单
    if last_price <= stop_loss:
        return {
            "status": "stop_hit",
            "open_price": first_price,
            "current": last_price,
            "note": f"当前价 {last_price:.2f} ≤ 止损 {stop_loss:.2f}",
        }

    # 2. 开盘高开过多
    if first_price > entry_high:
        return {
            "status": "gap_up_skip",
            "open_price": first_price,
            "current": last_price,
            "note": f"开盘 {first_price:.2f} 高于入场区上沿 {entry_high:.2f}, 不追",
        }

    # 3. 开盘在入场区
    if entry_low <= first_price <= entry_high:
        return {
            "status": "triggered",
            "open_price": first_price,
            "current": last_price,
            "note": f"开盘 {first_price:.2f} 在入场区 [{entry_low:.2f}, {entry_high:.2f}], 按计划买入",
        }

    # 4. 开盘低开但当前回到入场区内
    if first_price < entry_low and entry_low <= last_price <= entry_high:
        return {
            "status": "triggered_late",
            "open_price": first_price,
            "current": last_price,
            "note": f"低开 {first_price:.2f} 已回到入场区, 当前 {last_price:.2f}, 可买入",
        }

    # 5. 仍在等待
    return {
        "status": "wait",
        "open_price": first_price,
        "current": last_price,
        "note": f"开盘 {first_price:.2f}, 当前 {last_price:.2f}, 等待回到入场区 [{entry_low:.2f}, {entry_high:.2f}]",
    }


def render_verification_md(t1_date: str, t_date: str, results: list, mode: str = "live") -> str:
    lines = []
    lines.append(f"# S5 T+1 验证 — {t1_date} (T 日 = {t_date}) [mode={mode}]")
    lines.append("")

    if not results:
        lines.append("**T 日无 candidate 或 T+1 数据缺失。**")
        return "\n".join(lines)

    counts = {}
    for r in results:
        counts[r["verification"]["status"]] = counts.get(r["verification"]["status"], 0) + 1

    lines.append("## 状态统计")
    lines.append("")
    for status, n in sorted(counts.items()):
        lines.append(f"- **{status}**: {n}")
    lines.append("")

    # backtest 模式额外汇总
    if mode == "backtest":
        triggered = [r for r in results if r["verification"].get("pnl_pct") is not None]
        if triggered:
            pnls = [r["verification"]["pnl_pct"] for r in triggered]
            avg = sum(pnls) / len(pnls)
            wins = sum(1 for p in pnls if p > 0)
            lines.append("## 盈亏汇总")
            lines.append("")
            lines.append(f"- 触发: **{len(triggered)}/{len(results)}**")
            lines.append(f"- 胜率 (pnl>0): **{wins}/{len(triggered)} = {wins*100/len(triggered):.0f}%**")
            lines.append(f"- 平均盈亏: **{avg:+.2f}%**")
            lines.append(f"- 最高盈: {max(pnls):+.2f}%")
            lines.append(f"- 最大亏: {min(pnls):+.2f}%")
            lines.append("")

    lines.append("## 明细")
    lines.append("")
    for r in results:
        c = r["candidate"]
        v = r["verification"]
        emoji = {
            # live
            "triggered": "✅", "triggered_late": "🟡", "gap_up_skip": "⚠️",
            "stop_hit": "❌", "wait": "⏳", "no_data": "🚫", "parse_error": "🚫",
            # backtest
            "triggered_at_open": "✅", "triggered_intraday": "🟡",
            "gap_down_skip": "⚠️", "hit_target_1": "🎯", "hit_target_2": "🎯🎯",
            "close_hold": "📦",
        }.get(v["status"], "?")
        title = f"### {emoji} {c['code']} {c['name']} — {v['status']}"
        if v.get("pnl_pct") is not None:
            title += f" ({v['pnl_pct']:+.2f}%)"
        lines.append(title)
        lines.append("")
        lines.append(f"- 入场区: {c['entry']['zone_low']:.2f} ~ {c['entry']['zone_high']:.2f}")
        lines.append(f"- 止损: {c['stop_loss']['price']:.2f}")
        lines.append(f"- 止盈 1/2: {c['target_1']['price']:.2f} / {c['target_2']['price']:.2f}")
        if mode == "backtest":
            if v.get("t1_open") is not None:
                lines.append(f"- T+1 OHLC: O={v['t1_open']:.2f} H={v['t1_high']:.2f} L={v['t1_low']:.2f} C={v['t1_close']:.2f}")
            if v.get("entry_price") is not None:
                lines.append(f"- 入场价: {v['entry_price']:.2f}")
                lines.append(f"- 退出价: {v['exit_price']:.2f} ({v.get('exit_reason')})")
        else:
            if v.get("open_price") is not None:
                lines.append(f"- T+1 开盘: {v['open_price']:.2f}")
            if v.get("current") is not None:
                lines.append(f"- 当前: {v['current']:.2f}")
        lines.append(f"- **{v['note']}**")
        lines.append("")

    return "\n".join(lines)


def run_verify(t1_date: str, candidates_path: str, output_dir: str, mode: str = "live"):
    setup_logging()
    if candidates_path:
        if not os.path.exists(candidates_path):
            raise FileNotFoundError(candidates_path)
        t_date = (
            os.path.basename(candidates_path)
            .replace("candidates_", "")
            .replace(".json", "")
        )
    else:
        t_date, candidates_path = find_t_minus_1_candidates(t1_date, output_dir)

    logging.info(f"===== S5 verify mode={mode} t+1={t1_date} t={t_date} =====")
    logging.info(f"读 candidates: {candidates_path}")

    with open(candidates_path, "r", encoding="utf-8") as f:
        cand_payload = json.load(f)

    candidates = cand_payload.get("candidates", [])
    if not candidates:
        logging.info("T 日无 candidate, 跳过")
        md_path = os.path.join(output_dir, f"verification_{t1_date}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(render_verification_md(t1_date, t_date, [], mode=mode))
        return

    results = []

    if mode == "backtest":
        # 批量拉 T+1 日线 (研究-mcp 一次调回)
        codes = [c["code"] for c in candidates]
        t1_fmt = t1_date.replace("-", "")
        klines_map = fetch_klines_batch(codes, t1_fmt, t1_fmt)
        for cand in candidates:
            code = cand["code"]
            bars = klines_map.get(code, [])
            t1_bar = next((b for b in bars if b["date"] == t1_date), None)
            if t1_bar is None:
                verification = {
                    "status": "no_data",
                    "entry_price": None,
                    "exit_price": None,
                    "pnl_pct": None,
                    "note": f"T+1 {t1_date} 无 K 线数据 (停牌? 节假日?)",
                }
            else:
                verification = verify_one_backtest(cand, t1_bar)
            logging.info(f"  {code} {cand['name']}: {verification['status']} pnl={verification.get('pnl_pct')}")
            results.append({"candidate": cand, "verification": verification})
    else:
        for cand in candidates:
            verification = verify_one(cand)
            logging.info(f"  {cand['code']} {cand['name']}: {verification['status']}")
            results.append({"candidate": cand, "verification": verification})

    output_target = os.environ.get("S5_OUTPUT", "both").lower()

    if output_target in ("file", "both"):
        md_path = os.path.join(output_dir, f"verification_{t1_date}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(render_verification_md(t1_date, t_date, results, mode=mode))
        logging.info(f"写入: {md_path}")

        json_path = os.path.join(output_dir, f"verification_{t1_date}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "t1_date": t1_date,
                    "t_date": t_date,
                    "mode": mode,
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logging.info(f"写入: {json_path}")

    if output_target in ("db", "both"):
        try:
            from db_writer import write_verification
            write_verification(t1_date, t_date, results, mode)
        except Exception as e:
            logging.error(f"DB 写入失败 (S5_OUTPUT={output_target}): {e}")

    print(f"\n📊 T+1 验证结果 mode={mode} ({t1_date}):")
    for r in results:
        c = r["candidate"]
        v = r["verification"]
        pnl = v.get("pnl_pct")
        pnl_str = f" pnl={pnl:+.2f}%" if pnl is not None else ""
        print(f"  {c['code']} {c['name']}: {v['status']}{pnl_str}")
    if mode == "backtest":
        # 汇总统计
        triggered = [r for r in results if r["verification"].get("pnl_pct") is not None]
        if triggered:
            pnls = [r["verification"]["pnl_pct"] for r in triggered]
            avg = sum(pnls) / len(pnls)
            wins = sum(1 for p in pnls if p > 0)
            print(f"\n  汇总: {len(triggered)}/{len(results)} 触发, 胜率 {wins}/{len(triggered)} ({wins*100/len(triggered):.0f}%), 平均盈亏 {avg:+.2f}%")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="T+1 日期 YYYY-MM-DD")
    ap.add_argument("--candidates-json", default=None, help="(可选) 显式指定 T 日 candidates JSON 路径")
    ap.add_argument("--output-dir", default=".", help="验证文件输出目录, 默认 .")
    ap.add_argument(
        "--mode",
        choices=["live", "backtest"],
        default="live",
        help="live=实时分时(akshare stock_intraday_em); backtest=历史日线回放(research-mcp)",
    )
    args = ap.parse_args()

    run_verify(args.date, args.candidates_json, args.output_dir, mode=args.mode)


if __name__ == "__main__":
    main()
