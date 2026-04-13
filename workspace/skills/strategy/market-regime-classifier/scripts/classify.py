#!/usr/bin/env python3
"""classify.py — market-regime-classifier 的 CLI 编排器。

流程:
    parse 复盘 MD + akshare       (parser.py)
      → 六维打分                  (scoring.py)
      → 读历史 log, 构造 3 日窗口  (output_writer.parse_regime_log)
      → 逃生门检查                (regime_rules.check_emergency_hatch)
      → 3 日确认 + 缓冲区          (regime_rules.apply_3day_confirmation)
      → 写 MD / JSON / 追加 log    (output_writer.write_outputs)

用法 (对齐 spec §9):
    python3 classify.py                       跑今日 (本地时区)
    python3 classify.py --date=2026-04-13
    python3 classify.py --from-review=/path/to/复盘_2026-04-13.md
    python3 classify.py --format=json         仅打印 JSON 到 stdout
    python3 classify.py --output-dir=/tmp/out 覆盖写入目录

本模块也提供 `classify(date, ...)` 纯函数供测试和下游 skill 直接调用,
不涉及 CLI 也不涉及文件 IO。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

from output_writer import (
    ClassifyResult,
    append_log,
    determine_confidence,
    parse_regime_log,
    render_md,
    result_to_json,
    write_outputs,
)
from parser import RawMarketData, build_raw_market_data
from regime_rules import (
    DEFAULT_REGIME,
    apply_3day_confirmation,
    apply_emergency_switch,
    check_emergency_hatch,
    lookup_playbook,
    score_to_raw_regime,
)
from scoring import (
    score_advance_decline,
    score_ma_position,
    score_sentiment_delta,
    score_sentiment_index,
    score_streak_height,
    score_volume_trend,
    total_score,
)


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 路径常量
# --------------------------------------------------------------------------- #


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
DEFAULT_CACHE_DIR = os.path.join(SKILL_DIR, "memory", "cache")
DEFAULT_LOG_PATH = os.path.join(SKILL_DIR, "memory", "regime-log.md")

# bot11 的复盘 MD 默认位置 (daily_review.py 的输出目录)
DEFAULT_REVIEW_DIR = os.path.expanduser(
    "~/.openclaw/workspace-bot11/memory/posts/review-output"
)


# --------------------------------------------------------------------------- #
# 辅助: 六维得分
# --------------------------------------------------------------------------- #


def _score_all_dims(raw: RawMarketData) -> dict:
    """把 RawMarketData 转成六维得分 dict。

    缺失维度按 0 分计入 (spec §8 降级策略)。
    """
    scores: dict = {}

    if raw.hs300 is not None and raw.csi1000 is not None:
        scores["ma_position"] = score_ma_position(raw.hs300, raw.csi1000)
    else:
        scores["ma_position"] = 0

    scores["advance_decline"] = (
        score_advance_decline(raw.advance_decline_ratio)
        if raw.advance_decline_ratio is not None
        else 0
    )
    scores["sentiment_delta"] = (
        score_sentiment_delta(raw.sentiment_delta)
        if raw.sentiment_delta is not None
        else 0
    )
    scores["sentiment_index"] = (
        score_sentiment_index(raw.sentiment_index)
        if raw.sentiment_index is not None
        else 0
    )
    scores["streak_height"] = (
        score_streak_height(raw.max_streak) if raw.max_streak is not None else 0
    )
    scores["volume_trend"] = (
        score_volume_trend(raw.volume_ratio_5_20)
        if raw.volume_ratio_5_20 is not None
        else 0
    )

    return scores


def _build_raw_data_snapshot(raw: RawMarketData) -> dict:
    """扁平化 RawMarketData 为 JSON 可序列化的原始值 dict (用于 raw_data 字段)。"""
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


# --------------------------------------------------------------------------- #
# 辅助: 3 日窗口构造 (以上次 emergency 为边界重置)
# --------------------------------------------------------------------------- #


def _build_scores_window(prior_entries: list, today_score: int) -> list:
    """从历史 log 条目构造 3 日窗口, 以最近一次 emergency 为重置边界。

    spec §6 规定: 逃生门触发后, 后续切换从新 regime 重新计算 3 日窗口。
    实现上等价于: 只取 emergency 之后的历史分数, 加上今日, 作为窗口。

    prior_entries 必须已按日期升序排列, 且不包含今日。
    """
    # 从后往前找最近的 emergency
    reset_idx = -1
    for i in range(len(prior_entries) - 1, -1, -1):
        if prior_entries[i]["emergency_switch"]:
            reset_idx = i
            break

    effective = prior_entries[reset_idx + 1 :] if reset_idx >= 0 else prior_entries
    # 最多取最近 2 条历史 + 今日 = 3 日窗口
    window = [e["total_score"] for e in effective[-2:]] + [today_score]
    return window


# --------------------------------------------------------------------------- #
# 核心编排函数
# --------------------------------------------------------------------------- #


def classify(
    date: str,
    review_md_path: Optional[str] = None,
    cache_dir: Optional[str] = None,
    log_path: Optional[str] = None,
    hs300_df=None,
    csi1000_df=None,
) -> ClassifyResult:
    """完整决策流程, 返回 ClassifyResult。

    不做文件 IO (写入由 CLI 层负责), 便于测试和下游 skill 直接调用。

    参数:
        date            目标交易日 'YYYY-MM-DD'
        review_md_path  复盘 MD 路径, 为 None 时 MD 侧字段全部缺失
        cache_dir       akshare 缓存目录, 默认 skill 下 memory/cache
        log_path        regime-log.md 路径, 默认 skill 下 memory/regime-log.md
        hs300_df        (测试用) 预加载的 HS300 日线 DF, 非 None 时跳过 akshare
        csi1000_df      (测试用) 同上
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    log_path = log_path or DEFAULT_LOG_PATH

    # 1. 解析原始值
    raw = build_raw_market_data(
        date=date,
        md_path=review_md_path,
        cache_dir=cache_dir if (hs300_df is None or csi1000_df is None) else None,
        hs300_df=hs300_df,
        csi1000_df=csi1000_df,
    )

    # 2. 六维打分
    dim_scores = _score_all_dims(raw)
    total = total_score(dim_scores)

    # 3. 读历史 log, 只保留 date 之前的条目
    log_entries = parse_regime_log(log_path)
    prior_entries = [e for e in log_entries if e["date"] < date]
    last_regime = (
        prior_entries[-1]["regime_code"] if prior_entries else DEFAULT_REGIME
    )
    yesterday_score = prior_entries[-1]["total_score"] if prior_entries else None

    # 4. 逃生门优先
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
    else:
        # 5. 标准 3 日确认
        window = _build_scores_window(prior_entries, total)
        decision = apply_3day_confirmation(last_regime, window)

    # 6. 组装结果
    confidence = determine_confidence(len(raw.missing_dims))
    result = ClassifyResult(
        date=date,
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
    return result


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _locate_review_md(date: str, explicit: Optional[str]) -> Optional[str]:
    """按优先级查找复盘 MD 路径。"""
    if explicit:
        if os.path.exists(explicit):
            return explicit
        logger.warning("--from-review path not found: %s", explicit)
        return None
    default = os.path.join(DEFAULT_REVIEW_DIR, f"复盘_{date}.md")
    return default if os.path.exists(default) else None


def _is_likely_trading_day(date: str) -> bool:
    """简易交易日判断: 仅排除周末, 不覆盖节假日。

    daily_review.py 先尝试 tushare 日历, 失败时也用这个回退。本 CLI
    不需要节假日精度 — 数据拉不到自然会降级。
    """
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        return dt.weekday() < 5
    except ValueError:
        return True  # 格式问题让下游报错, 不在这里拦截


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="classify.py",
        description="market-regime-classifier: 跑一次六维打分 → regime 决策 → 写三种输出",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="目标日期 YYYY-MM-DD, 默认今日本地时区",
    )
    parser.add_argument(
        "--from-review",
        default=None,
        help="复盘 MD 路径, 默认 workspace-bot11/memory/posts/review-output/复盘_{date}.md",
    )
    parser.add_argument(
        "--format",
        choices=["all", "json", "md"],
        default="all",
        help="all (默认) 写三种文件 + 打印摘要; json/md 仅 stdout 不写文件",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录, 默认 = 复盘 MD 所在目录; 若复盘 MD 找不到, 默认 skill 下 memory/outputs/",
    )
    parser.add_argument(
        "--log-path",
        default=None,
        help="regime-log.md 路径, 默认 skill 下 memory/regime-log.md",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="akshare 缓存目录, 默认 skill 下 memory/cache",
    )
    parser.add_argument(
        "--ignore-trading-day",
        action="store_true",
        help="即使是周末也跑 (调试用)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    date = args.date or datetime.now().strftime("%Y-%m-%d")

    if not _is_likely_trading_day(date) and not args.ignore_trading_day:
        print(f"{date} 看起来不是交易日 (周末), 跳过。用 --ignore-trading-day 强制执行。")
        return 0

    review_md = _locate_review_md(date, args.from_review)
    if review_md is None:
        logger.warning(
            "未找到复盘 MD, MD 侧字段将全部缺失: date=%s, explicit=%s",
            date,
            args.from_review,
        )

    log_path = args.log_path or DEFAULT_LOG_PATH
    cache_dir = args.cache_dir or DEFAULT_CACHE_DIR

    result = classify(
        date=date,
        review_md_path=review_md,
        cache_dir=cache_dir,
        log_path=log_path,
    )

    if args.format == "json":
        print(json.dumps(result_to_json(result), ensure_ascii=False, indent=2))
        return 0
    if args.format == "md":
        print(render_md(result))
        return 0

    # all 模式: 写文件
    if args.output_dir:
        output_dir = args.output_dir
    elif review_md is not None:
        output_dir = os.path.dirname(os.path.abspath(review_md))
    else:
        output_dir = os.path.join(SKILL_DIR, "memory", "outputs")

    md_path = os.path.join(output_dir, f"regime_{date}.md")
    json_path = os.path.join(output_dir, f"regime_{date}.json")
    paths = write_outputs(result, md_path, json_path, log_path)

    # 终端摘要
    from regime_rules import REGIME_CODE_TO_NAME

    name = REGIME_CODE_TO_NAME[result.regime_code]
    last_name = REGIME_CODE_TO_NAME[result.last_regime_code]
    tag = ""
    if result.emergency_switch:
        tag = f" 🚨 emergency={result.emergency_direction}"
    elif result.switched:
        tag = f" (从 {last_name} 切)"
    print(f"[regime] {date} → {name} 总分 {result.score_total}{tag}")
    print(f"  MD:   {paths['md']}")
    print(f"  JSON: {paths['json']}")
    print(f"  Log:  {paths['log']}")
    if result.missing_dims:
        print(f"  ⚠️  missing: {', '.join(result.missing_dims)} (confidence={result.confidence})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
