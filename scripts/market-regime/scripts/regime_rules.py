"""Regime 决策规则 — 分数映射、3 日确认 + 缓冲区、逃生门、战法映射。

这是本 skill 最复杂的模块, 规则来源严格对齐 spec §5 / §6 / §7:

- score_to_raw_regime      分数 → 5 档 regime code (spec §5)
- apply_3day_confirmation  3 日确认 + 缓冲区, 不对称切换 (spec §6)
- check_emergency_hatch    单日剧变逃生门, 下行 OR / 上行 AND (spec §6)
- lookup_playbook          regime → 战法推荐/禁止/仓位上限 (spec §5)

上游 (backfill/replay.py) 负责:
- 内存维护 prior_entries, 不读真实 regime-log.md
- 通过 scoring.build_scores_window 构造 3 日窗口
- 读昨日 raw 构造 emergency context
- 调用这 4 个函数, 组装 ClassifyResult 写入 regime_classify_daily 表
"""

from __future__ import annotations

from typing import Optional


# --------------------------------------------------------------------------- #
# Regime 常量表
# --------------------------------------------------------------------------- #


# (code, display_name, score_lo_inclusive, score_hi_inclusive)
# 按乐观度从高到低排列: index 0 最乐观, index 4 最悲观
REGIMES = [
    ("STRONG_BULL", "强牛", 7, 12),
    ("STRONG_RANGE", "强势震荡", 2, 6),
    ("NEUTRAL_RANGE", "中性震荡", -1, 1),
    ("WEAK_RANGE", "弱势震荡", -5, -2),
    ("BEAR", "熊", -12, -6),
]

REGIME_CODE_TO_NAME = {code: name for code, name, _, _ in REGIMES}
REGIME_NAME_TO_CODE = {name: code for code, name, _, _ in REGIMES}
REGIME_ORDER = [code for code, _, _, _ in REGIMES]  # 0=bull, 4=bear
REGIME_BOUNDS = {code: (lo, hi) for code, _, lo, hi in REGIMES}

DEFAULT_REGIME = "NEUTRAL_RANGE"  # 首次运行默认

# --------------------------------------------------------------------------- #
# 1. 分数 → 原始 Regime
# --------------------------------------------------------------------------- #


def score_to_raw_regime(score: int) -> str:
    """总分 → regime code, 按 spec §5 的 5 档区间。

    区间 (上下限均含):
      >= +7         STRONG_BULL
      +2..+6        STRONG_RANGE
      -1..+1        NEUTRAL_RANGE
      -5..-2        WEAK_RANGE
      <= -6         BEAR
    """
    if score >= 7:
        return "STRONG_BULL"
    if score >= 2:
        return "STRONG_RANGE"
    if score >= -1:
        return "NEUTRAL_RANGE"
    if score >= -5:
        return "WEAK_RANGE"
    return "BEAR"


# --------------------------------------------------------------------------- #
# 2. 3 日确认 + 缓冲区
# --------------------------------------------------------------------------- #


def apply_3day_confirmation(
    last_regime: str,
    scores_window: list,
) -> dict:
    """3 日确认 + 不对称缓冲区 (spec §6)。

    输入:
        last_regime    昨日 (或上一次 log 记录) 的 regime code
        scores_window  最近 N 日总分, 时序从老到新, 最后一个是今日。
                       N>=3 时启用 3 日确认; N<3 时视为 bootstrap 模式,
                       保持 last_regime 不切换。

    返回:
        {
          "regime": str,         最终声明的 regime code
          "switched": bool,      是否发生切换
          "switch_warning": str | None,   未达确认但已进入新档位时的提示
          "bootstrap": bool,     N<3 时为 True
        }

    规则:
      * 今日 raw regime == last_regime        → 维持, 无 warning
      * 更乐观方向 (today_idx < last_idx):
          target = 相邻一档 (不允许一次跨多档上行)
          条件: 全部 3 日得分 ≥ target 下限
      * 更悲观方向 (today_idx > last_idx):
          先试相邻 target1, 再试跨档 target2
          条件 (target_x 的悲观条件): 全部 3 日得分 ≤ target_x 上限 − 1
          若 today_raw 已是 target2, 且 3 日条件同时满足两档, 允许一次跨档
      * 未达确认 + today_raw != last_regime → switch_warning 标注方向
    """
    if not scores_window:
        return {
            "regime": last_regime,
            "switched": False,
            "switch_warning": None,
            "bootstrap": True,
        }

    today_score = scores_window[-1]
    today_raw = score_to_raw_regime(today_score)

    if today_raw == last_regime:
        return {
            "regime": last_regime,
            "switched": False,
            "switch_warning": None,
            "bootstrap": False,
        }

    # N < 3: bootstrap, 不切换但记录 warning
    if len(scores_window) < 3:
        return {
            "regime": last_regime,
            "switched": False,
            "switch_warning": _warning_text(last_regime, today_raw, today_score, bootstrap=True),
            "bootstrap": True,
        }

    recent3 = scores_window[-3:]
    last_idx = REGIME_ORDER.index(last_regime)
    today_idx = REGIME_ORDER.index(today_raw)

    # ---- 向更乐观切换 ----
    if today_idx < last_idx:
        target = REGIME_ORDER[last_idx - 1]
        lo, _ = REGIME_BOUNDS[target]
        if all(s >= lo for s in recent3):
            return {
                "regime": target,
                "switched": True,
                "switch_warning": None,
                "bootstrap": False,
            }
        return {
            "regime": last_regime,
            "switched": False,
            "switch_warning": _warning_text(last_regime, today_raw, today_score),
            "bootstrap": False,
        }

    # ---- 向更悲观切换 ----
    # 相邻档
    target1 = REGIME_ORDER[last_idx + 1]
    _, hi1 = REGIME_BOUNDS[target1]
    target1_ok = all(s <= hi1 - 1 for s in recent3)

    # 跨档 (只在 today_idx 至少跨了 2 档时考虑)
    target2 = None
    if today_idx - last_idx >= 2:
        target2 = REGIME_ORDER[last_idx + 2]
        _, hi2 = REGIME_BOUNDS[target2]
        # 跨档需同时满足 target1 的悲观条件 + target2 的悲观条件
        target2_ok = target1_ok and all(s <= hi2 - 1 for s in recent3)
    else:
        target2_ok = False

    if target2_ok:
        return {
            "regime": target2,
            "switched": True,
            "switch_warning": None,
            "bootstrap": False,
        }
    if target1_ok:
        return {
            "regime": target1,
            "switched": True,
            "switch_warning": None,
            "bootstrap": False,
        }

    return {
        "regime": last_regime,
        "switched": False,
        "switch_warning": _warning_text(last_regime, today_raw, today_score),
        "bootstrap": False,
    }


def _warning_text(last_regime: str, today_raw: str, today_score: int, bootstrap: bool = False) -> str:
    last_name = REGIME_CODE_TO_NAME[last_regime]
    today_name = REGIME_CODE_TO_NAME[today_raw]
    if bootstrap:
        return (
            f"历史不足 3 日, 启动模式维持 {last_name}; "
            f"今日得分 {_fmt_score(today_score)} 已进入 {today_name} 区间"
        )
    return (
        f"今日得分 {_fmt_score(today_score)} 已进入 {today_name} 区间, "
        f"若后续 2 日持续将切换 (当前维持 {last_name})"
    )


def _fmt_score(s: int) -> str:
    return f"+{s}" if s > 0 else str(s)


# --------------------------------------------------------------------------- #
# 3. 单日剧变逃生门
# --------------------------------------------------------------------------- #


def check_emergency_hatch(
    today_score: int,
    yesterday_score: Optional[int],
    hs300_pct_change: Optional[float] = None,
    csi1000_pct_change: Optional[float] = None,
    advance_decline_ratio: Optional[float] = None,
    sentiment_index: Optional[float] = None,
    sentiment_delta: Optional[int] = None,
) -> dict:
    """单日剧变逃生门检查 (spec §6)。

    返回:
        {
          "triggered": bool,
          "direction": "down" | "up" | None,
          "reasons": list[str],     # 触发的条件 id (英文, 写入 JSON)
        }

    下行逃生门 (OR, 宽松; 缺数据视为该子条件未触发):
      1. total_drop_5      total(t) − total(t-1) ≤ −5
      2. index_crash       (HS300 或 CSI1000 当日涨幅 ≤ −3%) 且 涨跌比 ≤ 0.25
      3. sentiment_collapse 情绪评分 ≤ 20 或 涨停差 ≤ −40

    上行逃生门 (AND, 严格; 所有条件必须有数据且全部满足):
      1. total_surge_5     total(t) − total(t-1) ≥ +5
      2. index_rally       HS300 和 CSI1000 当日涨幅均 ≥ 2%
      3. breadth_confirm   涨跌比 ≥ 0.80

    下行优先级高于上行 (若两者同时触发, 返回下行)。
    昨日数据缺失时, total_drop_5 / total_surge_5 无法判断, 跳过这一条件,
    其它条件独立判断。
    """
    # ---- 下行 ----
    down_reasons = []

    if yesterday_score is not None and today_score - yesterday_score <= -5:
        down_reasons.append("total_drop_5")

    if (
        advance_decline_ratio is not None
        and advance_decline_ratio <= 0.25
        and (
            (hs300_pct_change is not None and hs300_pct_change <= -3.0)
            or (csi1000_pct_change is not None and csi1000_pct_change <= -3.0)
        )
    ):
        down_reasons.append("index_crash")

    sentiment_collapse = False
    if sentiment_index is not None and sentiment_index <= 20:
        sentiment_collapse = True
    if sentiment_delta is not None and sentiment_delta <= -40:
        sentiment_collapse = True
    if sentiment_collapse:
        down_reasons.append("sentiment_collapse")

    if down_reasons:
        return {"triggered": True, "direction": "down", "reasons": down_reasons}

    # ---- 上行 (AND 严格, 缺数据直接失败) ----
    up_ok = (
        yesterday_score is not None
        and (today_score - yesterday_score) >= 5
        and hs300_pct_change is not None
        and hs300_pct_change >= 2.0
        and csi1000_pct_change is not None
        and csi1000_pct_change >= 2.0
        and advance_decline_ratio is not None
        and advance_decline_ratio >= 0.80
    )
    if up_ok:
        return {
            "triggered": True,
            "direction": "up",
            "reasons": ["total_surge_5", "index_rally", "breadth_confirm"],
        }

    return {"triggered": False, "direction": None, "reasons": []}


def apply_emergency_switch(last_regime: str, direction: str) -> str:
    """逃生门触发后的 regime 切换: 向目标方向跳一档 (最多一档)。

    direction = 'down' → 更悲观一档
    direction = 'up'   → 更乐观一档

    若已是端点 (熊/强牛) 且方向指向边界外, 原样返回 last_regime。
    """
    if direction not in ("up", "down"):
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
    idx = REGIME_ORDER.index(last_regime)
    if direction == "down":
        new_idx = min(idx + 1, len(REGIME_ORDER) - 1)
    else:
        new_idx = max(idx - 1, 0)
    return REGIME_ORDER[new_idx]


# --------------------------------------------------------------------------- #
# 4. 战法 & 仓位映射 (spec §5)
# --------------------------------------------------------------------------- #


STRATEGIES = {
    "S1": {"name": "突破战法", "desc": "强势股横盘平台放量突破, 进场买突破位"},
    "S2": {"name": "龙头板接力", "desc": "盯高度板 (3板+) 梯队龙头, 次日竞价接力"},
    "S3": {"name": "首板接力", "desc": "当日领涨板块首板, 次日竞价低开进"},
    "S4": {"name": "回踩战法", "desc": "强势股回踩 5/10 日线不破, 次日进"},
    "S5": {"name": "龙回头", "desc": "前期龙头冷却后二次放量反包"},
    "S6": {"name": "趋势持有", "desc": "指数强势 + 龙头股持仓 5-10 天"},
    "S7": {"name": "超跌反弹", "desc": "连续大跌后的技术性反弹, 一日游"},
    "S8": {"name": "空仓观望", "desc": "不开新仓, 只处理已有持仓"},
}


PLAYBOOKS = {
    "STRONG_BULL": {
        "recommended": [
            {"id": "S1", "priority": 1},
            {"id": "S2", "priority": 2},
            {"id": "S6", "priority": 3},
        ],
        "forbidden": ["S7", "S8"],
        "position_limit": {"total": 0.90, "single": 0.30},
    },
    "STRONG_RANGE": {
        "recommended": [
            {"id": "S4", "priority": 1},
            {"id": "S5", "priority": 2},
            {"id": "S3", "priority": 3},
        ],
        "forbidden": ["S1", "S7"],
        "position_limit": {"total": 0.70, "single": 0.25},
    },
    "NEUTRAL_RANGE": {
        "recommended": [
            {"id": "S5", "priority": 1},
            {"id": "S4", "priority": 2, "mode": "strict"},
        ],
        "forbidden": ["S1", "S2", "S6"],
        "position_limit": {"total": 0.50, "single": 0.20},
    },
    "WEAK_RANGE": {
        "recommended": [
            {"id": "S5", "priority": 1, "mode": "试错"},
        ],
        "forbidden": ["S1", "S2", "S3", "S6"],
        "position_limit": {"total": 0.30, "single": 0.15},
    },
    "BEAR": {
        "recommended": [
            {"id": "S8", "priority": 1},
            {"id": "S7", "priority": 2, "mode": "1-2成仓一日游"},
        ],
        "forbidden": ["S1", "S2", "S3", "S4", "S6"],
        "position_limit": {"total": 0.20, "single": 0.10},
    },
}


def lookup_playbook(regime_code: str) -> dict:
    """返回指定 regime 的战法推荐/禁止/仓位上限 (spec §5)。

    推荐战法列表会被扩展成 {id, name, priority, mode?} 形式,
    便于 JSON 输出直接使用。
    """
    if regime_code not in PLAYBOOKS:
        raise KeyError(f"unknown regime: {regime_code}")
    base = PLAYBOOKS[regime_code]
    recommended = []
    for item in base["recommended"]:
        entry = {
            "id": item["id"],
            "name": STRATEGIES[item["id"]]["name"],
            "priority": item["priority"],
        }
        if "mode" in item:
            entry["mode"] = item["mode"]
        recommended.append(entry)
    return {
        "recommended": recommended,
        "forbidden": list(base["forbidden"]),
        "position_limit": dict(base["position_limit"]),
    }
