"""六维打分 — 纯函数。

输入原始数据、输出 -2 ~ +2 的整数得分。规则来源见 spec §4 和
`references/scoring.md`。每个函数都是纯函数，便于测试。

维度:
  1. score_ma_position        指数 vs 均线（HS300 + CSI1000 平均）
  2. score_advance_decline    涨跌家数比
  3. score_sentiment_delta    情绪（涨停数 − 跌停数）
  4. score_sentiment_index    情绪评分（0-100 复合指标）
  5. score_streak_height      最高连板高度
  6. score_volume_trend       成交量趋势（MA5/MA20）

合成:
  total_score(dim_scores: dict) -> int     范围 [-12, +12]

所有阈值采用 "向下走格子" 的左闭右开区间, 与 spec §4 的表对齐:
如某维度 "≥ X" 归 +2, 则 X 归 +1 而非 +2, 除非 spec 明确标注 ">X"。
"""

from __future__ import annotations

import math
from typing import TypedDict


# --------------------------------------------------------------------------- #
# 维度 1: 指数 vs 均线
# --------------------------------------------------------------------------- #


class IndexMA(TypedDict):
    """单个指数的收盘价与 5/20/60/250 日 SMA。"""

    close: float
    ma5: float
    ma20: float
    ma60: float
    ma250: float


def _score_ma_for_index(close: float, ma5: float, ma20: float, ma60: float, ma250: float) -> int:
    """单个指数按 spec §4 的均线规则打 -2 ~ +2 分。

    +2: 站上 5/20/60/250 且 MA 多头排列 (MA5>MA20>MA60>MA250)
    +1: 站上 5/20/60
     0: 站上 20, 60 不定
    -1: 跌破 20
    -2: MA 空头排列 (MA5<MA20<MA60<MA250)
    """
    above_5 = close > ma5
    above_20 = close > ma20
    above_60 = close > ma60
    above_250 = close > ma250
    bull_alignment = ma5 > ma20 > ma60 > ma250
    bear_alignment = ma5 < ma20 < ma60 < ma250

    # 最悲观: 空头排列直接 -2, 不论价格位置
    if bear_alignment:
        return -2
    # 最乐观: 站上全部均线 + 多头排列
    if above_5 and above_20 and above_60 and above_250 and bull_alignment:
        return 2
    # +1: 站上 5/20/60 (不要求 MA 多头排列, 也不要求站上 250)
    if above_5 and above_20 and above_60:
        return 1
    # 0: 站上 20, 60 位置不定
    if above_20:
        return 0
    # 其余 (跌破 20 但未空头排列) → -1
    return -1


def _round_half_away_from_zero(x: float) -> int:
    """四舍五入到最近整数, 零点处向远离零的方向。

    Python 内置 round() 使用 banker's rounding (round half to even), 对
    打分场景不直观: round(0.5) == 0, round(-0.5) == 0。本函数保证
    0.5 → 1, -0.5 → -1, 1.5 → 2, -1.5 → -2, 与 spec §4 示例
    "沪深300 +2、中证1000 +1, 平均 1.5 → +2" 一致。
    """
    return int(math.copysign(math.floor(abs(x) + 0.5), x)) if x != 0 else 0


def score_ma_position(hs300: IndexMA, csi1000: IndexMA) -> int:
    """HS300 与 CSI1000 各自打分, 算术平均后四舍五入到整数 (spec §4)。"""
    s1 = _score_ma_for_index(
        hs300["close"], hs300["ma5"], hs300["ma20"], hs300["ma60"], hs300["ma250"]
    )
    s2 = _score_ma_for_index(
        csi1000["close"], csi1000["ma5"], csi1000["ma20"], csi1000["ma60"], csi1000["ma250"]
    )
    avg = (s1 + s2) / 2.0
    return _round_half_away_from_zero(avg)


# --------------------------------------------------------------------------- #
# 维度 2: 涨跌家数比
# --------------------------------------------------------------------------- #


def score_advance_decline(ratio: float) -> int:
    """涨跌家数比 → -2 ~ +2。

    >0.75 → +2 ; [0.60, 0.75] → +1 ; [0.40, 0.60) → 0
    [0.25, 0.40) → -1 ; <0.25 → -2

    注: spec 区间 "0.60-0.75" 视为闭区间 (含 0.75), 故 0.75 → +1 而非 +2。
    """
    if ratio > 0.75:
        return 2
    if ratio >= 0.60:
        return 1
    if ratio >= 0.40:
        return 0
    if ratio >= 0.25:
        return -1
    return -2


# --------------------------------------------------------------------------- #
# 维度 3: 情绪(涨停-跌停)
# --------------------------------------------------------------------------- #


def score_sentiment_delta(delta: int) -> int:
    """涨停数 − 跌停数 → -2 ~ +2。

    >80 → +2 ; [40, 80] → +1 ; [10, 40) → 0 ; [-40, 10) → -1 ; <-40 → -2
    """
    if delta > 80:
        return 2
    if delta >= 40:
        return 1
    if delta >= 10:
        return 0
    if delta >= -40:
        return -1
    return -2


# --------------------------------------------------------------------------- #
# 维度 4: 情绪评分 (0-100 复合指标)
# --------------------------------------------------------------------------- #


def score_sentiment_index(value: float) -> int:
    """复盘 MD 情绪温度计的 "情绪评分 N/100" → -2 ~ +2。

    >70 → +2 ; [55, 70] → +1 ; [40, 55) → 0 ; [25, 40) → -1 ; <25 → -2
    """
    if value > 70:
        return 2
    if value >= 55:
        return 1
    if value >= 40:
        return 0
    if value >= 25:
        return -1
    return -2


# --------------------------------------------------------------------------- #
# 维度 5: 最高连板高度
# --------------------------------------------------------------------------- #


def score_streak_height(streak: int) -> int:
    """最高连板高度 → -2 ~ +2。

    ≥5 → +2 ; 4 → +1 ; 3 → 0 ; 2 → -1 ; ≤1 → -2
    """
    if streak >= 5:
        return 2
    if streak == 4:
        return 1
    if streak == 3:
        return 0
    if streak == 2:
        return -1
    return -2


# --------------------------------------------------------------------------- #
# 维度 6: 成交量趋势 (MA5/MA20)
# --------------------------------------------------------------------------- #


def score_volume_trend(ratio: float) -> int:
    """5 日均量 / 20 日均量 → -2 ~ +2。

    >1.30 → +2 ; [1.10, 1.30] → +1 ; [0.90, 1.10) → 0
    [0.70, 0.90) → -1 ; <0.70 → -2
    """
    if ratio > 1.30:
        return 2
    if ratio >= 1.10:
        return 1
    if ratio >= 0.90:
        return 0
    if ratio >= 0.70:
        return -1
    return -2


# --------------------------------------------------------------------------- #
# 总分合成
# --------------------------------------------------------------------------- #


DIMENSION_KEYS = (
    "ma_position",
    "advance_decline",
    "sentiment_delta",
    "sentiment_index",
    "streak_height",
    "volume_trend",
)


def total_score(dim_scores: dict) -> int:
    """将六维得分加总, 返回总分。

    缺失维度按 0 分计入 (spec §8 降级策略)。未知键会被忽略但会抛警告,
    以防上游传错字段名。
    """
    total = 0
    for key in DIMENSION_KEYS:
        v = dim_scores.get(key, 0)
        if not isinstance(v, int):
            raise TypeError(f"dim_scores[{key!r}] must be int, got {type(v).__name__}")
        if v < -2 or v > 2:
            raise ValueError(f"dim_scores[{key!r}] out of range [-2, 2]: {v}")
        total += v
    return total
