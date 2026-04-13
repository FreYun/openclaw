"""parser.py 的单元测试。

覆盖:
1. parse_daily_review — 真实复盘 MD fixture + 合成最小 MD 字符串
2. compute_index_ma / compute_volume_ratio — 合成 DataFrame, 不依赖网络
3. fetch_index_daily — 本地 CSV 缓存读取路径 (不打 akshare)
4. build_raw_market_data — 完整编排器, 含降级路径

不测 akshare 网络调用 (接口已在 REPL 手动验证)。
"""

import os
import tempfile

import pandas as pd
import pytest

from parser import (
    RawMarketData,
    build_raw_market_data,
    compute_index_ma,
    compute_volume_ratio,
    fetch_index_daily,
    parse_daily_review,
)


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
REVIEW_MD_2026_03_20 = os.path.join(FIXTURE_DIR, "复盘_2026-03-20.md")


# --------------------------------------------------------------------------- #
# parse_daily_review: 真实 MD fixture
# --------------------------------------------------------------------------- #


class TestParseDailyReviewFixture:
    """用 workspace-bot11 实际产出的 2026-03-20 复盘作为 ground truth。"""

    @pytest.fixture(scope="class")
    def parsed(self):
        return parse_daily_review(REVIEW_MD_2026_03_20)

    def test_breadth_counts(self, parsed):
        assert parsed["advance_count"] == 662
        assert parsed["decline_count"] == 4786
        assert parsed["flat_count"] == 377

    def test_advance_decline_ratio(self, parsed):
        # 662 / (662 + 4786 + 377) = 662 / 5825
        expected = 662 / 5825
        assert parsed["advance_decline_ratio"] == pytest.approx(expected, rel=1e-9)

    def test_sentiment_delta(self, parsed):
        # 涨停:跌停 32:22 → delta = 10
        assert parsed["sentiment_delta"] == 10

    def test_sentiment_index(self, parsed):
        # "情绪评分 **25** / 100（偏空低迷）"
        assert parsed["sentiment_index"] == 25.0

    def test_max_streak(self, parsed):
        # "最高连板：**0** 板"
        assert parsed["max_streak"] == 0


# --------------------------------------------------------------------------- #
# parse_daily_review: 合成最小 MD
# --------------------------------------------------------------------------- #


class TestParseDailyReviewSynthetic:
    def test_missing_fields_return_no_keys(self, tmp_path):
        md = tmp_path / "empty.md"
        md.write_text("# 空复盘\n没有任何字段\n", encoding="utf-8")
        result = parse_daily_review(str(md))
        assert "advance_decline_ratio" not in result
        assert "sentiment_delta" not in result
        assert "sentiment_index" not in result
        assert "max_streak" not in result

    def test_breadth_without_flat(self, tmp_path):
        md = tmp_path / "no_flat.md"
        md.write_text("- 上涨：**100** 家 / 下跌：**50** 家\n", encoding="utf-8")
        result = parse_daily_review(str(md))
        assert result["advance_count"] == 100
        assert result["decline_count"] == 50
        assert result["flat_count"] == 0
        # 100 / (100 + 50 + 0) = 0.6666...
        assert result["advance_decline_ratio"] == pytest.approx(100 / 150)

    def test_breadth_no_bold(self, tmp_path):
        md = tmp_path / "plain.md"
        md.write_text("上涨：600 家 / 下跌：4800 家 / 平盘：400\n", encoding="utf-8")
        result = parse_daily_review(str(md))
        assert result["advance_count"] == 600
        assert result["decline_count"] == 4800

    def test_chinese_colon_variants(self, tmp_path):
        md = tmp_path / "colon.md"
        md.write_text(
            "最高连板: **3** 板\n情绪评分 | 58 / 100（偏多）\n涨停:跌停 | 45:10\n",
            encoding="utf-8",
        )
        result = parse_daily_review(str(md))
        assert result["max_streak"] == 3
        assert result["sentiment_index"] == 58.0
        assert result["sentiment_delta"] == 35

    def test_sentiment_score_float(self, tmp_path):
        md = tmp_path / "f.md"
        md.write_text("情绪评分 | **67.5** / 100", encoding="utf-8")
        result = parse_daily_review(str(md))
        assert result["sentiment_index"] == 67.5


# --------------------------------------------------------------------------- #
# 合成 DataFrame 辅助工厂
# --------------------------------------------------------------------------- #


def _make_index_df(
    n_days: int = 260,
    close_series=None,
    volume_series=None,
    start_date: str = "2025-01-02",
):
    """构造一个合成的指数日线 DF, 用交易日(工作日)作为日期。

    close_series / volume_series 未传时使用常量 100 / 10000。
    """
    dates = pd.bdate_range(start=start_date, periods=n_days).strftime("%Y-%m-%d")
    close = [100.0] * n_days if close_series is None else list(close_series)
    volume = [10000.0] * n_days if volume_series is None else list(volume_series)
    assert len(close) == n_days and len(volume) == n_days
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
# compute_index_ma
# --------------------------------------------------------------------------- #


class TestComputeIndexMa:
    def test_flat_series_all_equal(self):
        df = _make_index_df(n_days=260)
        target = df.iloc[-1]["date"]
        ma = compute_index_ma(df, target)
        assert ma["close"] == 100.0
        assert ma["ma5"] == 100.0
        assert ma["ma20"] == 100.0
        assert ma["ma60"] == 100.0
        assert ma["ma250"] == 100.0

    def test_ascending_series_bull_alignment(self):
        # close 从 1 递增到 260 → MA5 > MA20 > MA60 > MA250
        close = [float(i + 1) for i in range(260)]
        df = _make_index_df(n_days=260, close_series=close)
        target = df.iloc[-1]["date"]
        ma = compute_index_ma(df, target)
        assert ma["close"] == 260.0
        assert ma["ma5"] > ma["ma20"] > ma["ma60"] > ma["ma250"]
        # MA5 = 平均(256..260) = 258
        assert ma["ma5"] == pytest.approx(258.0)
        # MA20 = 平均(241..260) = 250.5
        assert ma["ma20"] == pytest.approx(250.5)

    def test_target_date_not_in_df_raises(self):
        df = _make_index_df(n_days=260)
        with pytest.raises(KeyError, match="not in index data"):
            compute_index_ma(df, "1999-01-01")

    def test_insufficient_history_raises(self):
        # 只给 100 天, 目标日是最后一天 → idx=99 < 249
        df = _make_index_df(n_days=100)
        target = df.iloc[-1]["date"]
        with pytest.raises(ValueError, match="not enough history"):
            compute_index_ma(df, target)

    def test_target_mid_series_still_computes(self):
        # 目标日是第 250 天 (idx=249), 刚好够 MA250
        df = _make_index_df(n_days=260)
        target = df.iloc[249]["date"]
        ma = compute_index_ma(df, target)
        assert ma["close"] == 100.0


# --------------------------------------------------------------------------- #
# compute_volume_ratio
# --------------------------------------------------------------------------- #


class TestComputeVolumeRatio:
    def test_flat_volume_ratio_one(self):
        df = _make_index_df(n_days=30)
        target = df.iloc[-1]["date"]
        assert compute_volume_ratio(df, target) == pytest.approx(1.0)

    def test_volume_spike_last_5_days(self):
        # 前 25 天 volume=1000, 后 5 天 volume=3000
        vol = [1000.0] * 25 + [3000.0] * 5
        df = _make_index_df(n_days=30, volume_series=vol)
        target = df.iloc[-1]["date"]
        # MA5 = 3000
        # MA20 = 平均(idx 10..29) = (15*1000 + 5*3000)/20 = 30000/20 = 1500
        # ratio = 3000 / 1500 = 2.0
        assert compute_volume_ratio(df, target) == pytest.approx(2.0)

    def test_insufficient_history_raises(self):
        df = _make_index_df(n_days=15)
        target = df.iloc[-1]["date"]
        with pytest.raises(ValueError, match="not enough history"):
            compute_volume_ratio(df, target)

    def test_target_not_in_df_raises(self):
        df = _make_index_df(n_days=30)
        with pytest.raises(KeyError, match="not in index data"):
            compute_volume_ratio(df, "1999-01-01")

    def test_zero_volume_raises(self):
        df = _make_index_df(n_days=25, volume_series=[0.0] * 25)
        target = df.iloc[-1]["date"]
        with pytest.raises(ValueError, match="non-positive"):
            compute_volume_ratio(df, target)


# --------------------------------------------------------------------------- #
# fetch_index_daily: 只测缓存读取路径, 不打网络
# --------------------------------------------------------------------------- #


class TestFetchIndexDailyCache:
    def test_reads_existing_cache(self, tmp_path):
        cache_dir = str(tmp_path)
        # 手工写一个缓存 CSV
        df_in = _make_index_df(n_days=10)
        cache_path = os.path.join(cache_dir, "index_sh000300.csv")
        df_in.to_csv(cache_path, index=False)

        df_out = fetch_index_daily("sh000300", cache_dir, refresh=False)
        assert len(df_out) == 10
        assert list(df_out.columns) == ["date", "open", "high", "low", "close", "volume"]
        assert df_out.iloc[0]["date"] == df_in.iloc[0]["date"]

    def test_cache_sorted_by_date(self, tmp_path):
        cache_dir = str(tmp_path)
        # 写入一个乱序的缓存
        df_in = _make_index_df(n_days=10)
        df_in = df_in.sample(frac=1, random_state=42).reset_index(drop=True)
        df_in.to_csv(os.path.join(cache_dir, "index_sh000300.csv"), index=False)

        df_out = fetch_index_daily("sh000300", cache_dir)
        dates = df_out["date"].tolist()
        assert dates == sorted(dates)


# --------------------------------------------------------------------------- #
# build_raw_market_data: 完整编排器
# --------------------------------------------------------------------------- #


class TestBuildRawMarketData:
    def test_with_fixture_md_and_injected_index_df(self):
        df = _make_index_df(n_days=260)
        # 目标日必须同时存在于 df 和能读到 MD
        target = df.iloc[-1]["date"]
        result = build_raw_market_data(
            date=target,
            md_path=REVIEW_MD_2026_03_20,
            hs300_df=df,
            csi1000_df=df,
        )
        assert isinstance(result, RawMarketData)
        # MD 侧
        assert result.sentiment_index == 25.0
        assert result.sentiment_delta == 10
        assert result.max_streak == 0
        assert result.advance_decline_ratio == pytest.approx(662 / 5825)
        # 指数侧
        assert result.hs300 is not None
        assert result.csi1000 is not None
        assert result.volume_ratio_5_20 == pytest.approx(1.0)
        # 无缺失维度
        assert result.missing_dims == []

    def test_md_path_none_marks_md_dims_missing(self):
        df = _make_index_df(n_days=260)
        target = df.iloc[-1]["date"]
        result = build_raw_market_data(
            date=target,
            md_path=None,
            hs300_df=df,
            csi1000_df=df,
        )
        assert set(result.missing_dims) >= {
            "advance_decline",
            "sentiment_delta",
            "sentiment_index",
            "streak_height",
        }
        assert result.hs300 is not None  # 指数侧仍然成功

    def test_missing_index_df_marks_ma_and_volume_missing(self, tmp_path):
        md = tmp_path / "m.md"
        md.write_text("情绪评分 | 58 / 100\n", encoding="utf-8")
        result = build_raw_market_data(
            date="2025-06-01",
            md_path=str(md),
            hs300_df=None,
            csi1000_df=None,
            cache_dir=None,  # 不触发 akshare
        )
        assert "ma_position" in result.missing_dims
        assert "volume_trend" in result.missing_dims
        assert result.sentiment_index == 58.0

    def test_target_date_not_in_index_df_graceful(self):
        df = _make_index_df(n_days=260)
        result = build_raw_market_data(
            date="1999-01-01",  # 不在 df 中
            md_path=REVIEW_MD_2026_03_20,
            hs300_df=df,
            csi1000_df=df,
        )
        assert result.hs300 is None
        assert result.csi1000 is None
        assert "ma_position" in result.missing_dims
        assert "volume_trend" in result.missing_dims
        # 有 warning 而非 raise
        assert any("hs300_ma_failed" in w for w in result.warnings)

    def test_short_history_df_degrades_gracefully(self):
        # 只给 30 天, 够算 volume 但不够算 MA250
        df = _make_index_df(n_days=30)
        target = df.iloc[-1]["date"]
        result = build_raw_market_data(
            date=target,
            md_path=None,
            hs300_df=df,
            csi1000_df=df,
        )
        assert result.hs300 is None
        assert "ma_position" in result.missing_dims
        # volume 能算出来 (30 天 >= 20)
        assert result.volume_ratio_5_20 == pytest.approx(1.0)
        assert "volume_trend" not in result.missing_dims
