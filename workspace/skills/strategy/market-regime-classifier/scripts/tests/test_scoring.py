"""六维打分的表驱动单元测试。

每个打分函数都需覆盖 5 个区间的典型值 + 边界值。边界值的归属以
`scoring.py` 的 docstring 为准(左闭右开, 带上强/弱不等号区分)。
"""

import pytest

from scoring import (
    _round_half_away_from_zero,
    _score_ma_for_index,
    score_advance_decline,
    score_ma_position,
    score_sentiment_delta,
    score_sentiment_index,
    score_streak_height,
    score_volume_trend,
    total_score,
)


# --------------------------------------------------------------------------- #
# 辅助: 四舍五入 (远离零)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "x,expected",
    [
        (0.0, 0),
        (0.4, 0),
        (0.5, 1),
        (0.6, 1),
        (1.5, 2),
        (-0.5, -1),
        (-1.5, -2),
        (-0.49, 0),
        (2.0, 2),
    ],
)
def test_round_half_away_from_zero(x, expected):
    assert _round_half_away_from_zero(x) == expected


# --------------------------------------------------------------------------- #
# 维度 1: 指数 vs 均线
# --------------------------------------------------------------------------- #


def _make_index(close, ma5, ma20, ma60, ma250):
    return {"close": close, "ma5": ma5, "ma20": ma20, "ma60": ma60, "ma250": ma250}


class TestScoreMaForIndex:
    def test_plus_two_full_bull(self):
        # 站上 5/20/60/250 + MA 多头排列
        assert _score_ma_for_index(close=110, ma5=108, ma20=105, ma60=100, ma250=95) == 2

    def test_plus_two_close_equals_ma_not_strictly_above(self):
        # close == ma250: 不严格站上 → 退到 +1 (站上 5/20/60)
        assert _score_ma_for_index(close=100, ma5=99, ma20=98, ma60=97, ma250=100) == 1

    def test_plus_one_above_5_20_60_no_bull_align(self):
        # 站上 5/20/60, 但 MA250 混乱或未站上
        assert _score_ma_for_index(close=100, ma5=99, ma20=98, ma60=97, ma250=105) == 1

    def test_plus_one_above_all_but_no_bull_alignment(self):
        # 站上全部均线但不严格多头排列: 由 +1 分支兜住 (不是 +2)
        assert _score_ma_for_index(close=110, ma5=100, ma20=101, ma60=99, ma250=95) == 1

    def test_zero_above_20_not_60(self):
        assert _score_ma_for_index(close=100, ma5=101, ma20=98, ma60=102, ma250=95) == 0

    def test_zero_above_20_below_5(self):
        # 站上 20 但 close < ma5
        assert _score_ma_for_index(close=100, ma5=102, ma20=99, ma60=95, ma250=90) == 0

    def test_minus_one_below_20(self):
        # 跌破 20 但未空头排列
        assert _score_ma_for_index(close=98, ma5=100, ma20=99, ma60=95, ma250=105) == -1

    def test_minus_two_bear_alignment(self):
        # MA5 < MA20 < MA60 < MA250 → -2, 即使 close 位置不定
        assert _score_ma_for_index(close=80, ma5=85, ma20=90, ma60=95, ma250=100) == -2

    def test_minus_two_bear_alignment_even_if_close_above_ma5(self):
        # close 高于 ma5 也要 -2
        assert _score_ma_for_index(close=90, ma5=85, ma20=90, ma60=95, ma250=100) == -2


class TestScoreMaPosition:
    def test_average_plus_two(self):
        bull = _make_index(110, 108, 105, 100, 95)
        assert score_ma_position(bull, bull) == 2

    def test_average_rounds_half_away(self):
        # HS300 +2, CSI1000 +1 → 平均 1.5 → +2 (spec §4 示例)
        hs300 = _make_index(110, 108, 105, 100, 95)  # +2
        csi1000 = _make_index(100, 99, 98, 97, 105)  # +1 (站 5/20/60 未站 250)
        assert score_ma_position(hs300, csi1000) == 2

    def test_average_minus_half_rounds_to_minus_one(self):
        # -1 + 0 = -1 → -0.5 → -1
        weak = _make_index(98, 100, 99, 95, 105)  # -1
        zero = _make_index(100, 101, 98, 102, 95)  # 0
        assert score_ma_position(weak, zero) == -1

    def test_average_zero(self):
        zero = _make_index(100, 101, 98, 102, 95)  # 0
        assert score_ma_position(zero, zero) == 0

    def test_average_minus_two(self):
        bear = _make_index(80, 85, 90, 95, 100)
        assert score_ma_position(bear, bear) == -2


# --------------------------------------------------------------------------- #
# 维度 2: 涨跌家数比
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (0.80, 2),
        (0.7501, 2),
        (0.75, 1),  # 闭区间上界归 +1
        (0.65, 1),
        (0.60, 1),  # 闭区间下界
        (0.59, 0),
        (0.50, 0),
        (0.40, 0),
        (0.3999, -1),
        (0.30, -1),
        (0.25, -1),
        (0.2499, -2),
        (0.10, -2),
        (0.0, -2),
    ],
)
def test_score_advance_decline(ratio, expected):
    assert score_advance_decline(ratio) == expected


# --------------------------------------------------------------------------- #
# 维度 3: 情绪(涨停-跌停)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "delta,expected",
    [
        (120, 2),
        (81, 2),
        (80, 1),
        (60, 1),
        (40, 1),
        (39, 0),
        (10, 0),
        (9, -1),
        (0, -1),
        (-40, -1),
        (-41, -2),
        (-100, -2),
    ],
)
def test_score_sentiment_delta(delta, expected):
    assert score_sentiment_delta(delta) == expected


# --------------------------------------------------------------------------- #
# 维度 4: 情绪评分
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,expected",
    [
        (90, 2),
        (71, 2),
        (70, 1),
        (60, 1),
        (55, 1),
        (54.9, 0),
        (50, 0),
        (40, 0),
        (39.9, -1),
        (30, -1),
        (25, -1),
        (24.9, -2),
        (10, -2),
        (0, -2),
    ],
)
def test_score_sentiment_index(value, expected):
    assert score_sentiment_index(value) == expected


# --------------------------------------------------------------------------- #
# 维度 5: 最高连板高度
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "streak,expected",
    [
        (10, 2),
        (5, 2),
        (4, 1),
        (3, 0),
        (2, -1),
        (1, -2),
        (0, -2),
    ],
)
def test_score_streak_height(streak, expected):
    assert score_streak_height(streak) == expected


# --------------------------------------------------------------------------- #
# 维度 6: 成交量趋势
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (1.80, 2),
        (1.31, 2),
        (1.30, 1),
        (1.20, 1),
        (1.10, 1),
        (1.09, 0),
        (1.0, 0),
        (0.90, 0),
        (0.89, -1),
        (0.80, -1),
        (0.70, -1),
        (0.69, -2),
        (0.50, -2),
    ],
)
def test_score_volume_trend(ratio, expected):
    assert score_volume_trend(ratio) == expected


# --------------------------------------------------------------------------- #
# 总分合成
# --------------------------------------------------------------------------- #


class TestTotalScore:
    def test_full_bull(self):
        scores = {k: 2 for k in [
            "ma_position", "advance_decline", "sentiment_delta",
            "sentiment_index", "streak_height", "volume_trend",
        ]}
        assert total_score(scores) == 12

    def test_full_bear(self):
        scores = {k: -2 for k in [
            "ma_position", "advance_decline", "sentiment_delta",
            "sentiment_index", "streak_height", "volume_trend",
        ]}
        assert total_score(scores) == -12

    def test_mixed(self):
        scores = {
            "ma_position": 1,
            "advance_decline": 0,
            "sentiment_delta": 1,
            "sentiment_index": 1,
            "streak_height": 0,
            "volume_trend": 0,
        }
        assert total_score(scores) == 3

    def test_missing_dims_treated_as_zero(self):
        # 缺失维度按 0 分计入 (spec §8)
        scores = {"ma_position": 2, "advance_decline": -1}
        assert total_score(scores) == 1

    def test_empty_dict(self):
        assert total_score({}) == 0

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            total_score({"ma_position": 3})

    def test_non_int_raises(self):
        with pytest.raises(TypeError):
            total_score({"ma_position": 1.5})
