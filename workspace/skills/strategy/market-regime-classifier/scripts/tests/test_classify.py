"""classify.py 的集成测试 — 纯 classify() 编排函数 + CLI 入口。

不依赖 akshare 网络: 所有测试通过 hs300_df / csi1000_df 注入合成 DF。
"""

import json
import os

import pandas as pd
import pytest

from classify import _build_scores_window, classify, main
from output_writer import ClassifyResult, append_log, ClassifyResult as _CR

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
REVIEW_MD_2026_03_20 = os.path.join(FIXTURE_DIR, "复盘_2026-03-20.md")


def _make_index_df(
    n_days: int = 260,
    close_series=None,
    volume_series=None,
    start_date: str = "2025-01-02",
):
    dates = pd.bdate_range(start=start_date, periods=n_days).strftime("%Y-%m-%d")
    close = [100.0] * n_days if close_series is None else list(close_series)
    volume = [10000.0] * n_days if volume_series is None else list(volume_series)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
        }
    )


# --------------------------------------------------------------------------- #
# _build_scores_window
# --------------------------------------------------------------------------- #


class TestBuildScoresWindow:
    def test_empty_history(self):
        assert _build_scores_window([], 5) == [5]

    def test_no_emergency_takes_last_two(self):
        prior = [
            {"date": "2026-04-01", "total_score": 1, "emergency_switch": False},
            {"date": "2026-04-02", "total_score": 2, "emergency_switch": False},
            {"date": "2026-04-03", "total_score": 3, "emergency_switch": False},
        ]
        assert _build_scores_window(prior, 4) == [2, 3, 4]

    def test_emergency_resets_window(self):
        # 4/2 有 emergency → 只取 4/3 + 今日 (不足 3 日)
        prior = [
            {"date": "2026-04-01", "total_score": 5, "emergency_switch": False},
            {"date": "2026-04-02", "total_score": 0, "emergency_switch": True},
            {"date": "2026-04-03", "total_score": 1, "emergency_switch": False},
        ]
        assert _build_scores_window(prior, 2) == [1, 2]

    def test_emergency_at_last_day_resets_to_today_only(self):
        prior = [
            {"date": "2026-04-01", "total_score": 5, "emergency_switch": False},
            {"date": "2026-04-02", "total_score": 0, "emergency_switch": True},
        ]
        assert _build_scores_window(prior, 1) == [1]


# --------------------------------------------------------------------------- #
# classify(): 无历史 + 完整数据
# --------------------------------------------------------------------------- #


class TestClassifyFirstRun:
    def test_with_real_fixture_md_and_flat_index(self, tmp_path):
        """用 2026-03-20 fixture 跑一次完整流程, log 从空开始。"""
        df = _make_index_df(n_days=260)
        target = df.iloc[-1]["date"]
        log_path = tmp_path / "log.md"

        result = classify(
            date=target,
            review_md_path=REVIEW_MD_2026_03_20,
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        assert isinstance(result, ClassifyResult)
        # MD 侧字段都抽到了 → missing 只有 ma/volume 相关可能为空
        assert result.missing_dims == []
        assert result.confidence == "high"
        # fixture 数据: sentiment_index=25 (-1), delta=10 (0), streak=0 (-2),
        # ratio=0.1136 (-2). 平坦合成 index → ma=+1 (close 持平所有均线视为
        # 站上), volume=0 → total = -4
        assert result.score_total == -4
        # -4 ∈ [-5, -2] → WEAK_RANGE (但首次运行 bootstrap, 维持 NEUTRAL)
        assert result.regime_code == "NEUTRAL_RANGE"
        assert result.bootstrap is True
        assert result.switched is False
        assert result.switch_warning is not None
        # playbook 对应 NEUTRAL_RANGE
        assert result.playbook["position_limit"]["total"] == 0.50

    def test_without_review_md_all_md_dims_missing(self, tmp_path):
        df = _make_index_df(n_days=260)
        target = df.iloc[-1]["date"]
        log_path = tmp_path / "log.md"
        result = classify(
            date=target,
            review_md_path=None,
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        assert "advance_decline" in result.missing_dims
        assert "sentiment_index" in result.missing_dims
        assert result.confidence == "low"  # >=3 缺失
        # 所有 MD 侧字段按 0, 平坦合成指数 (ma=+1, volume=0) → total = 1
        assert result.score_total == 1


# --------------------------------------------------------------------------- #
# classify(): 带历史 log
# --------------------------------------------------------------------------- #


def _seed_log(log_path, entries):
    """用 output_writer.append_log 构造一段历史。每个 entry 是 kwargs dict。"""
    for e in entries:
        result = ClassifyResult(
            date=e["date"],
            score_total=e["total_score"],
            score_breakdown={
                "ma_position": 0,
                "advance_decline": 0,
                "sentiment_delta": 0,
                "sentiment_index": 0,
                "streak_height": 0,
                "volume_trend": 0,
            },
            raw_data={},
            regime_code=e["regime_code"],
            last_regime_code=e.get("last_regime_code", e["regime_code"]),
            switched=e.get("switched", False),
            bootstrap=False,
            confidence="high",
            missing_dims=[],
            emergency_switch=e.get("emergency_switch", False),
            emergency_direction=e.get("emergency_direction"),
            emergency_reason=e.get("emergency_reason", []),
            playbook={},
        )
        append_log(result, log_path)


class TestClassifyWithHistory:
    def test_three_day_confirmation_triggers_switch(self, tmp_path):
        log_path = tmp_path / "log.md"
        _seed_log(
            str(log_path),
            [
                {"date": "2025-12-20", "total_score": 3, "regime_code": "NEUTRAL_RANGE"},
                {"date": "2025-12-21", "total_score": 4, "regime_code": "NEUTRAL_RANGE"},
            ],
        )
        # 今日也 >= +2, 总分构造: 所有 flat index (ma=0 vol=0) + 不传 MD
        # 但我们要 total=3, 所以注入一个有涨跌比的 MD
        md = tmp_path / "m.md"
        md.write_text(
            "- 上涨：**4000** 家 / 下跌：**1000** 家 / 平盘：500\n"  # ratio=0.727 → +1
            "- 最高连板：**4** 板\n"  # +1
            "| 情绪评分 | 60 / 100 |\n"  # +1
            "| 涨停:跌停 | 40:20 |\n",  # delta=20 → 0
            encoding="utf-8",
        )
        df = _make_index_df(n_days=260, start_date="2024-12-01")
        target = "2025-12-22"
        # 让 df 包含 target 日期
        df.loc[df.index[-1], "date"] = target
        df = df.sort_values("date").reset_index(drop=True)

        result = classify(
            date=target,
            review_md_path=str(md),
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        # 总分 = 1 (ma) + 1 (ratio) + 0 (delta) + 1 (sentiment) + 1 (streak) + 0 (vol) = 4
        assert result.score_total == 4
        # 3 日窗口 = [3, 4, 4], 全 >= +2 → 切到 STRONG_RANGE
        assert result.regime_code == "STRONG_RANGE"
        assert result.switched is True
        assert result.last_regime_code == "NEUTRAL_RANGE"

    def test_single_day_in_new_zone_warns_but_stays(self, tmp_path):
        log_path = tmp_path / "log.md"
        _seed_log(
            str(log_path),
            [
                {"date": "2025-12-20", "total_score": 0, "regime_code": "NEUTRAL_RANGE"},
                {"date": "2025-12-21", "total_score": -1, "regime_code": "NEUTRAL_RANGE"},
            ],
        )
        md = tmp_path / "m.md"
        md.write_text(
            "- 上涨：**4000** 家 / 下跌：**1000** 家\n"  # +2
            "- 最高连板：**4** 板\n"  # +1
            "| 情绪评分 | 60 / 100 |\n"  # +1
            "| 涨停:跌停 | 40:20 |\n",  # 0
            encoding="utf-8",
        )
        df = _make_index_df(n_days=260, start_date="2024-12-01")
        df.loc[df.index[-1], "date"] = "2025-12-22"
        df = df.sort_values("date").reset_index(drop=True)
        result = classify(
            date="2025-12-22",
            review_md_path=str(md),
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        # 今日得分 ~4 (STRONG_RANGE 区间) 但前 2 日都在 NEUTRAL_RANGE → 维持 NEUTRAL
        assert result.regime_code == "NEUTRAL_RANGE"
        assert result.switched is False
        assert result.switch_warning is not None
        assert "强势震荡" in result.switch_warning


# --------------------------------------------------------------------------- #
# classify(): 逃生门触发
# --------------------------------------------------------------------------- #


class TestClassifyEmergency:
    def test_sentiment_collapse_triggers_emergency_down(self, tmp_path):
        log_path = tmp_path / "log.md"
        _seed_log(
            str(log_path),
            [
                {"date": "2025-12-20", "total_score": 3, "regime_code": "STRONG_RANGE"},
                {"date": "2025-12-21", "total_score": 4, "regime_code": "STRONG_RANGE"},
            ],
        )
        md = tmp_path / "m.md"
        # 构造情绪评分 = 15 → sentiment_collapse 触发
        md.write_text(
            "- 上涨：**1000** 家 / 下跌：**4000** 家 / 平盘：500\n"  # 0.18 → -2
            "- 最高连板：**0** 板\n"  # -2
            "| 情绪评分 | **15** / 100 |\n"  # -2
            "| 涨停:跌停 | 10:50 |\n",  # -40 → -1
            encoding="utf-8",
        )
        df = _make_index_df(n_days=260, start_date="2024-12-01")
        df.loc[df.index[-1], "date"] = "2025-12-22"
        df = df.sort_values("date").reset_index(drop=True)
        result = classify(
            date="2025-12-22",
            review_md_path=str(md),
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        assert result.emergency_switch is True
        assert result.emergency_direction == "down"
        assert "sentiment_collapse" in result.emergency_reason
        # 从 STRONG_RANGE 降一档到 NEUTRAL_RANGE
        assert result.last_regime_code == "STRONG_RANGE"
        assert result.regime_code == "NEUTRAL_RANGE"
        assert result.switched is True

    def test_emergency_then_three_day_window_resets(self, tmp_path):
        log_path = tmp_path / "log.md"
        _seed_log(
            str(log_path),
            [
                {"date": "2025-12-18", "total_score": 5, "regime_code": "STRONG_RANGE"},
                {"date": "2025-12-19", "total_score": -2, "regime_code": "NEUTRAL_RANGE",
                 "emergency_switch": True, "emergency_direction": "down", "switched": True},
                {"date": "2025-12-20", "total_score": 4, "regime_code": "NEUTRAL_RANGE"},
                {"date": "2025-12-21", "total_score": 5, "regime_code": "NEUTRAL_RANGE"},
            ],
        )
        # 今日也应该是 STRONG_RANGE 区间得分 — 但是 emergency 之后只过了 2 天,
        # 窗口 = [4, 5, 今日] 才能考虑切换
        md = tmp_path / "m.md"
        md.write_text(
            "- 上涨：**4000** 家 / 下跌：**1000** 家 / 平盘：500\n"  # +1 (0.727)
            "- 最高连板：**4** 板\n"  # +1
            "| 情绪评分 | 60 / 100 |\n"  # +1
            "| 涨停:跌停 | 40:20 |\n",  # 0
            encoding="utf-8",
        )
        df = _make_index_df(n_days=260, start_date="2024-12-01")
        df.loc[df.index[-1], "date"] = "2025-12-22"
        df = df.sort_values("date").reset_index(drop=True)
        result = classify(
            date="2025-12-22",
            review_md_path=str(md),
            log_path=str(log_path),
            hs300_df=df,
            csi1000_df=df,
        )
        # total ~4 (ma+1, ratio+1, delta 0, sentiment+1, streak+1, vol 0)
        # 3 日窗口 = [4, 5, 4] (从 emergency 之后) — 全部 ≥ 2 → 切 STRONG
        assert result.score_total == 4
        assert result.regime_code == "STRONG_RANGE"
        assert result.switched is True


# --------------------------------------------------------------------------- #
# CLI main() — 借助 hs300_df 注入是不可能的, 所以只测 --format=json 非交易日跳过
# --------------------------------------------------------------------------- #


class TestCliEntry:
    def test_weekend_date_skips_without_force(self, capsys):
        # 2026-03-22 是周日
        ret = main(["--date=2026-03-22"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "不是交易日" in out or "周末" in out

    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
