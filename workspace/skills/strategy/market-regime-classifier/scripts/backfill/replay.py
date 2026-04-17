"""Replay 层: 把 SQLite 派生数据喂进 classifier 的核心规则, 逐日生成 regime。

跳过原 classify.py 的复盘 MD 解析层和单日 MD/JSON 输出, 直接:
  1. 从 SQLite 加载完整指数 + 派生层结果 (derive_raw_data.derive)
  2. 对每个交易日构造 RawMarketData (在内存里)
  3. 走 _score_all_dims → check_emergency_hatch → apply_3day_confirmation
  4. 维护内存版 prior_entries, 不读真实 regime-log.md
  5. 输出:
     - regime_replay_3y.csv (每日一行, 供分析)
     - memory/regime-replay-3y.md (独立日志, 不污染生产 regime-log.md)

不为每天生成 regime_YYYY-MM-DD.md / .json (用户明确要求)。

用法:
    python3 replay.py                     # 全量回放
    python3 replay.py --start 20240101    # 从某日起
    python3 replay.py --csv /tmp/x.csv    # 自定义 CSV 路径
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from typing import Optional

# 把上层 scripts 目录加入 path, 复用 classify / parser / regime_rules / output_writer
SKILL_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_SCRIPTS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402

from classify import _score_all_dims, _build_scores_window  # noqa: E402
from parser import (  # noqa: E402
    RawMarketData,
    compute_index_ma,
    compute_pct_change,
    compute_volume_ratio,
)
from regime_rules import (  # noqa: E402
    DEFAULT_REGIME,
    REGIME_CODE_TO_NAME,
    apply_3day_confirmation,
    apply_emergency_switch,
    check_emergency_hatch,
    lookup_playbook,
)
from output_writer import (  # noqa: E402
    ClassifyResult,
    append_log,
    determine_confidence,
)
from scoring import total_score  # noqa: E402

from db import connect  # noqa: E402
from derive_raw_data import derive  # noqa: E402
from rules_v2 import check_emergency_hatch_v2  # noqa: E402

logger = logging.getLogger("replay")


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #


def _yyyymmdd_to_iso(s: str) -> str:
    """20260414 -> 2026-04-14"""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def load_index_df(conn, ts_code: str) -> pd.DataFrame:
    """从 SQLite 加载指数日线为 DataFrame, 列: date (ISO), close。"""
    rows = conn.execute(
        "SELECT trade_date, close FROM index_daily WHERE ts_code=? ORDER BY trade_date ASC",
        (ts_code,),
    ).fetchall()
    df = pd.DataFrame(rows, columns=["trade_date", "close"])
    df["date"] = df["trade_date"].apply(_yyyymmdd_to_iso)
    return df[["date", "close"]]


def load_full_market_amount_df(conn) -> pd.DataFrame:
    """从 SQLite 合成全市场成交额历史 (上证综指 + 深证综指 amount).

    返回 DataFrame, 列: date (ISO), volume (亿元 — 单位仅用于 ratio 计算, 一致即可)
    """
    rows = conn.execute(
        """
        SELECT s.trade_date, s.amount + z.amount AS total_amount
        FROM index_daily s
        INNER JOIN index_daily z
            ON s.trade_date = z.trade_date AND s.ts_code='000001.SH' AND z.ts_code='399106.SZ'
        ORDER BY s.trade_date ASC
        """
    ).fetchall()
    df = pd.DataFrame(rows, columns=["trade_date", "volume"])
    df["date"] = df["trade_date"].apply(_yyyymmdd_to_iso)
    return df[["date", "volume"]]


# --------------------------------------------------------------------------- #
# 主回放循环
# --------------------------------------------------------------------------- #


def build_raw_from_derived(
    derived_row: dict,
    hs300_df: pd.DataFrame,
    csi1000_df: pd.DataFrame,
    full_market_df: pd.DataFrame,
) -> RawMarketData:
    """从派生数据 dict 直接构造 RawMarketData, 跳过复盘 MD 解析。

    维度 1, 6 (指数 + 成交量) 由 compute_* 函数从 DF 算出;
    维度 2-5 (MD 侧) 直接复用派生数据。
    数据不足时 (前 250 天 MA250 算不出) 进 missing_dims。
    """
    iso_date = _yyyymmdd_to_iso(derived_row["trade_date"])
    raw = RawMarketData(
        date=iso_date,
        advance_decline_ratio=derived_row.get("advance_decline_ratio"),
        sentiment_delta=derived_row.get("sentiment_delta"),
        sentiment_index=derived_row.get("sentiment_index"),
        max_streak=derived_row.get("max_streak"),
    )

    # MD 侧 missing 检测
    if raw.advance_decline_ratio is None:
        raw.missing_dims.append("advance_decline")
    if raw.sentiment_delta is None:
        raw.missing_dims.append("sentiment_delta")
    if raw.sentiment_index is None:
        raw.missing_dims.append("sentiment_index")
    if raw.max_streak is None:
        raw.missing_dims.append("streak_height")

    # 维度 1: HS300 + CSI1000 MA + pct_change
    ma_ok = True
    try:
        raw.hs300 = compute_index_ma(hs300_df, iso_date)
    except (KeyError, ValueError) as e:
        ma_ok = False
        raw.warnings.append(f"hs300_ma: {e}")
    try:
        raw.hs300_pct_change = compute_pct_change(hs300_df, iso_date)
    except (KeyError, ValueError) as e:
        raw.warnings.append(f"hs300_pct: {e}")
    try:
        raw.csi1000 = compute_index_ma(csi1000_df, iso_date)
    except (KeyError, ValueError) as e:
        ma_ok = False
        raw.warnings.append(f"csi1000_ma: {e}")
    try:
        raw.csi1000_pct_change = compute_pct_change(csi1000_df, iso_date)
    except (KeyError, ValueError) as e:
        raw.warnings.append(f"csi1000_pct: {e}")

    if not ma_ok:
        raw.missing_dims.append("ma_position")

    # 维度 6: 全市场 5/20 均量比
    try:
        raw.volume_ratio_5_20 = compute_volume_ratio(full_market_df, iso_date)
    except (KeyError, ValueError) as e:
        raw.missing_dims.append("volume_trend")
        raw.warnings.append(f"volume: {e}")

    return raw


def _build_raw_data_snapshot(raw: RawMarketData) -> dict:
    """对齐 classify._build_raw_data_snapshot 的字段结构。"""
    return {
        "ma_position": {
            "hs300": raw.hs300,
            "csi1000": raw.csi1000,
            "hs300_pct_change": raw.hs300_pct_change,
            "csi1000_pct_change": raw.csi1000_pct_change,
        },
        "advance_decline": raw.advance_decline_ratio,
        "sentiment_delta": raw.sentiment_delta,
        "sentiment_index": raw.sentiment_index,
        "streak_height": raw.max_streak,
        "volume_trend": raw.volume_ratio_5_20,
    }


def replay(
    derived_rows: list[dict],
    hs300_df: pd.DataFrame,
    csi1000_df: pd.DataFrame,
    full_market_df: pd.DataFrame,
    rules_version: str = "v1",
) -> list[ClassifyResult]:
    """逐日 replay, 内存维护 prior_entries (不读 / 不写真实 regime-log).

    rules_version:
        "v1" — 使用生产 regime_rules.check_emergency_hatch (默认)
        "v2" — 使用 rules_v2.check_emergency_hatch_v2 (实验性)
    """
    all_results: list[ClassifyResult] = []
    prior_entries: list[dict] = []
    last_emergency_idx: Optional[int] = None  # v2 用于冷静期

    for idx, d in enumerate(derived_rows):
        # 1. 构造 RawMarketData
        raw = build_raw_from_derived(d, hs300_df, csi1000_df, full_market_df)

        # 2. 六维打分
        dim_scores = _score_all_dims(raw)
        total = total_score(dim_scores)

        # 3. last_regime + yesterday_score (从内存 prior_entries)
        last_regime = (
            prior_entries[-1]["regime_code"] if prior_entries else DEFAULT_REGIME
        )
        yesterday_score = (
            prior_entries[-1]["total_score"] if prior_entries else None
        )

        # 4. 逃生门
        if rules_version == "v2":
            days_since = (
                idx - last_emergency_idx if last_emergency_idx is not None else None
            )
            emergency = check_emergency_hatch_v2(
                today_score=total,
                yesterday_score=yesterday_score,
                hs300_pct_change=raw.hs300_pct_change,
                csi1000_pct_change=raw.csi1000_pct_change,
                advance_decline_ratio=raw.advance_decline_ratio,
                sentiment_index=raw.sentiment_index,
                sentiment_delta=raw.sentiment_delta,
                days_since_last_emergency=days_since,
            )
        else:
            emergency = check_emergency_hatch(
                today_score=total,
                yesterday_score=yesterday_score,
                hs300_pct_change=raw.hs300_pct_change,
                csi1000_pct_change=raw.csi1000_pct_change,
                advance_decline_ratio=raw.advance_decline_ratio,
                sentiment_index=raw.sentiment_index,
                sentiment_delta=raw.sentiment_delta,
            )

        emergency_switch = False
        emergency_direction = None
        emergency_reason: list = []
        if emergency["triggered"]:
            final_regime = apply_emergency_switch(last_regime, emergency["direction"])
            decision = {
                "regime": final_regime,
                "switched": True,
                "switch_warning": None,
                "bootstrap": False,
            }
            emergency_switch = True
            emergency_direction = emergency["direction"]
            emergency_reason = emergency["reasons"]
            last_emergency_idx = idx  # 更新 v2 冷静期锚点
        else:
            window = _build_scores_window(prior_entries, total)
            decision = apply_3day_confirmation(last_regime, window)

        # 5. 组装 ClassifyResult
        confidence = determine_confidence(len(raw.missing_dims))
        result = ClassifyResult(
            date=raw.date,
            score_total=total,
            score_breakdown=dim_scores,
            raw_data=_build_raw_data_snapshot(raw),
            regime_code=decision["regime"],
            last_regime_code=last_regime,
            switched=decision["switched"],
            bootstrap=decision.get("bootstrap", False),
            confidence=confidence,
            missing_dims=list(raw.missing_dims),
            switch_warning=decision.get("switch_warning"),
            playbook=lookup_playbook(decision["regime"]),
            emergency_switch=emergency_switch,
            emergency_direction=emergency_direction,
            emergency_reason=emergency_reason,
        )
        all_results.append(result)

        # 6. 更新内存 prior_entries (对齐 parse_regime_log 的字段结构)
        prior_entries.append({
            "date": raw.date,
            "total_score": total,
            "regime_code": result.regime_code,
            "switched": result.switched,
            "emergency_switch": result.emergency_switch,
        })

    return all_results


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #


def write_replay_csv(results: list[ClassifyResult], path: str) -> None:
    """每日一行的回放结果 CSV, 适合做事后分析。"""
    if not results:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "total_score",
            "ma_position", "advance_decline", "sentiment_delta",
            "sentiment_index", "streak_height", "volume_trend",
            "regime_code", "regime_name",
            "last_regime_code", "switched", "bootstrap",
            "emergency_switch", "emergency_direction", "emergency_reason",
            "confidence", "missing_dims",
        ])
        for r in results:
            bd = r.score_breakdown
            writer.writerow([
                r.date, r.score_total,
                bd.get("ma_position", 0),
                bd.get("advance_decline", 0),
                bd.get("sentiment_delta", 0),
                bd.get("sentiment_index", 0),
                bd.get("streak_height", 0),
                bd.get("volume_trend", 0),
                r.regime_code,
                REGIME_CODE_TO_NAME[r.regime_code],
                r.last_regime_code,
                int(r.switched),
                int(r.bootstrap),
                int(r.emergency_switch),
                r.emergency_direction or "",
                ";".join(r.emergency_reason),
                r.confidence,
                ";".join(r.missing_dims),
            ])
    logger.info(f"CSV: {path} ({len(results)} 行)")


def write_replay_log(results: list[ClassifyResult], log_path: str) -> None:
    """把回放结果追加到独立的 regime-replay log (不污染生产 regime-log.md)."""
    if os.path.exists(log_path):
        os.remove(log_path)
    for r in results:
        append_log(r, log_path)
    logger.info(f"Replay log: {log_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main():
    parser = argparse.ArgumentParser(description="market-regime-classifier 历史回放")
    parser.add_argument("--start", default=None, help="起始 YYYYMMDD")
    parser.add_argument("--end", default=None, help="结束 YYYYMMDD")
    parser.add_argument("--csv", default="/tmp/regime_replay_3y.csv", help="输出 CSV")
    parser.add_argument(
        "--log",
        default=os.path.join(SKILL_SCRIPTS, "..", "memory", "regime-replay-3y.md"),
        help="独立 replay log 路径 (默认 skill/memory/regime-replay-3y.md)",
    )
    parser.add_argument(
        "--rules",
        choices=["v1", "v2"],
        default="v1",
        help="逃生门规则版本: v1=生产规则 (默认), v2=改进规则 (冷静期+下行加码+上行放宽)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    conn = connect()
    logger.info("加载指数日线...")
    hs300_df = load_index_df(conn, "000300.SH")
    csi1000_df = load_index_df(conn, "000852.SH")
    full_market_df = load_full_market_amount_df(conn)
    logger.info(
        f"  HS300: {len(hs300_df)}, CSI1000: {len(csi1000_df)}, "
        f"full_market: {len(full_market_df)}"
    )

    logger.info("派生原始数据 (从 SQLite)...")
    derived = derive(conn, args.start, args.end)
    logger.info(f"  {len(derived)} 个交易日")

    logger.info(f"逐日回放 (rules={args.rules})...")
    results = replay(derived, hs300_df, csi1000_df, full_market_df, rules_version=args.rules)
    logger.info(f"  完成: {len(results)} 个交易日")

    # 输出
    write_replay_csv(results, args.csv)
    log_path = os.path.abspath(args.log)
    write_replay_log(results, log_path)

    # 统计摘要
    from collections import Counter
    regime_counts = Counter(REGIME_CODE_TO_NAME[r.regime_code] for r in results)
    n_switched = sum(1 for r in results if r.switched)
    n_emergency = sum(1 for r in results if r.emergency_switch)
    n_bootstrap = sum(1 for r in results if r.bootstrap)
    n_missing = sum(1 for r in results if r.missing_dims)
    logger.info("===== 统计 =====")
    for name, n in regime_counts.most_common():
        logger.info(f"  {name:<10} {n:>4} 天 ({n/len(results)*100:.1f}%)")
    logger.info(f"  切换次数 (含逃生门): {n_switched}")
    logger.info(f"  逃生门触发: {n_emergency}")
    logger.info(f"  bootstrap (前 3 日): {n_bootstrap}")
    logger.info(f"  含 missing_dims 的天数: {n_missing}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
