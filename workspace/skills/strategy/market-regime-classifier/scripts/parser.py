"""数据解析层 — 从复盘 MD 和 akshare 抽取六维原始数据。

设计原则:
- MD 解析: 宽松 regex, 缺字段返回 None 而不是抛异常
- akshare: 带本地 CSV 缓存 (memory/cache/), 失败时上游降级处理
- 纯计算函数 (compute_index_ma / compute_volume_ratio) 接收 DataFrame
  作为输入, 便于单元测试不依赖网络

数据字段来源参见 spec §4 / handoff §2.2。
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 结果容器
# --------------------------------------------------------------------------- #


@dataclass
class RawMarketData:
    """六维原始数据 (解析后, 打分前)。

    任何字段都可能为 None, 表示该维度数据缺失。
    """

    date: str

    # MD 层字段
    advance_decline_ratio: Optional[float] = None
    sentiment_delta: Optional[int] = None  # 涨停数 - 跌停数
    sentiment_index: Optional[float] = None  # 情绪评分 0-100
    max_streak: Optional[int] = None  # 最高连板

    # akshare 指数层
    hs300: Optional[dict] = None  # IndexMA: {close, ma5, ma20, ma60, ma250}
    csi1000: Optional[dict] = None
    volume_ratio_5_20: Optional[float] = None

    # 当日涨跌幅 (逃生门判断需要), 单位: 百分比, 如 -3.15 表示 -3.15%
    hs300_pct_change: Optional[float] = None
    csi1000_pct_change: Optional[float] = None

    # 诊断信息
    missing_dims: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 复盘 MD 解析
# --------------------------------------------------------------------------- #


# regex 都用宽松匹配, 允许 ** 加粗与否, 允许中英文冒号混用
# 新格式 (daily_review.py 自动产出, 单行): "上涨：**662** 家 / 下跌：**4786** 家 / 平盘：377 家"
_RE_BREADTH = re.compile(
    r"上涨[:：]\s*\*{0,2}(\d+)\*{0,2}\s*家\s*/\s*下跌[:：]\s*\*{0,2}(\d+)\*{0,2}\s*家"
    r"(?:\s*/\s*平盘[:：]\s*\*{0,2}(\d+)\*{0,2})?"
)
_RE_LU_LD = re.compile(r"涨停[:：]跌停\s*\|?\s*\*{0,2}(\d+)\*{0,2}\s*[:：]\s*\*{0,2}(\d+)\*{0,2}")
_RE_SENTIMENT_SCORE = re.compile(r"情绪评分\s*\|?\s*\*{0,2}(\d+(?:\.\d+)?)\*{0,2}\s*/\s*100")
_RE_MAX_STREAK = re.compile(r"最高连板[:：]\s*\*{0,2}(-?\d+)\*{0,2}\s*板")

# 老格式 (手工/遗留复盘 MD, 分市场多行). 例:
#   - 上涨：257 家（上证）/ 241 家（深证）
#   - 平盘：11 家（上证）/ 13 家（深证）
#   - 下跌：2075 家（上证）/ 2661 家（深证）
# 每行可能含任意市场数, 全部累加。
_RE_BREADTH_ROW = re.compile(r"^\s*[-\*]?\s*(上涨|下跌|平盘)[:：](.+?)$", re.MULTILINE)
_RE_JIA_NUM = re.compile(r"(\d+)\s*家")


def _extract_multi_market_breadth(text: str):
    """老格式 fallback: 分市场多行的涨跌家数。

    例如:
        - 上涨：257 家（上证）/ 241 家（深证）
        - 下跌：2075 家（上证）/ 2661 家（深证）
        - 平盘：11 家（上证）/ 13 家（深证）

    每一行里可能含多个 "N 家" (上证 + 深证 + 北交所 …), 全部加总。
    返回 (up, down, flat) 元组, 上涨/下跌任一为 None 则返回 None。
    """
    sums = {"上涨": None, "下跌": None, "平盘": None}
    for category, content in _RE_BREADTH_ROW.findall(text):
        if sums.get(category) is not None:
            continue  # 已经记录过, 不覆盖 (防止误匹配到表格里同名的行)
        nums = [int(n) for n in _RE_JIA_NUM.findall(content)]
        if nums:
            sums[category] = sum(nums)
    if sums["上涨"] is None or sums["下跌"] is None:
        return None
    return sums["上涨"], sums["下跌"], sums["平盘"] or 0


def parse_daily_review(md_path: str) -> dict:
    """从复盘 MD 宽松提取 4 个 MD 侧字段。

    返回 dict, 可能包含以下键 (缺失字段不出现):
        advance_count: int
        decline_count: int
        flat_count: int
        advance_decline_ratio: float    — up / (up + down + flat)
        sentiment_delta: int            — 涨停 - 跌停
        sentiment_index: float          — 情绪评分 0-100
        max_streak: int                 — 最高连板

    不抛异常 (除非文件不存在)。解析失败的字段由上游按降级处理。

    兼容两种 MD 格式:
    - 新格式 (daily_review.py 自动产出, 单行汇总)
    - 老格式 (遗留手工 MD, 分市场多行). 老格式里通常只能恢复涨跌家数,
      情绪/连板字段本身就不存在, 会进入 missing_dims。
    """
    with open(md_path, encoding="utf-8") as f:
        text = f.read()

    result: dict = {}

    # 涨跌家数 (primary 新格式 → fallback 老格式)
    up = down = flat = None
    m = _RE_BREADTH.search(text)
    if m:
        up = int(m.group(1))
        down = int(m.group(2))
        flat = int(m.group(3)) if m.group(3) else 0
    else:
        fb = _extract_multi_market_breadth(text)
        if fb is not None:
            up, down, flat = fb
            logger.debug("parse_daily_review: using multi-market fallback breadth")

    if up is not None and down is not None:
        result["advance_count"] = up
        result["decline_count"] = down
        result["flat_count"] = flat
        total = up + down + flat
        if total > 0:
            result["advance_decline_ratio"] = up / total
    else:
        logger.debug("parse_daily_review: breadth not found in %s", md_path)

    # 涨停:跌停
    m = _RE_LU_LD.search(text)
    if m:
        lu = int(m.group(1))
        ld = int(m.group(2))
        result["sentiment_delta"] = lu - ld
    else:
        logger.debug("parse_daily_review: 涨停:跌停 not found")

    # 情绪评分
    m = _RE_SENTIMENT_SCORE.search(text)
    if m:
        result["sentiment_index"] = float(m.group(1))
    else:
        logger.debug("parse_daily_review: 情绪评分 not found")

    # 最高连板
    m = _RE_MAX_STREAK.search(text)
    if m:
        result["max_streak"] = int(m.group(1))
    else:
        logger.debug("parse_daily_review: 最高连板 not found")

    return result


# --------------------------------------------------------------------------- #
# akshare 指数数据 + 缓存
# --------------------------------------------------------------------------- #


# akshare symbol 对应表
INDEX_SYMBOLS = {
    "hs300": "sh000300",
    "csi1000": "sh000852",
}


def fetch_index_daily(
    symbol: str,
    cache_dir: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """拉取指数日线数据, 带本地 CSV 缓存。

    symbol: akshare 格式的指数代码 (如 'sh000300' / 'sh000852')
    cache_dir: 缓存目录, 文件命名 index_{symbol}.csv
    refresh: True 时强制重新拉取并覆盖缓存

    返回 DataFrame, 列: date (str YYYY-MM-DD), open, high, low, close, volume
    按 date 升序排列。

    akshare 接口偶发失败时会抛出原始异常, 由上游捕获后降级。
    """
    cache_path = os.path.join(cache_dir, f"index_{symbol}.csv")

    if os.path.exists(cache_path) and not refresh:
        try:
            df = pd.read_csv(cache_path)
            df["date"] = df["date"].astype(str)
            return df.sort_values("date").reset_index(drop=True)
        except Exception as e:  # 缓存损坏, 重拉
            logger.warning("cache read failed (%s), refetching: %s", cache_path, e)

    # 拉新数据
    import akshare as ak

    df = ak.stock_zh_index_daily(symbol=symbol)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values("date").reset_index(drop=True)

    os.makedirs(cache_dir, exist_ok=True)
    df.to_csv(cache_path, index=False)
    return df


# --------------------------------------------------------------------------- #
# 纯计算: MA / 成交量
# --------------------------------------------------------------------------- #


def compute_index_ma(df: pd.DataFrame, target_date: str) -> dict:
    """给定指数日线 DF, 计算 target_date 当日的收盘价与 MA5/20/60/250。

    返回 IndexMA shape: {close, ma5, ma20, ma60, ma250}

    异常:
        KeyError   — target_date 不在 df 中 (非交易日 / 数据未更新)
        ValueError — 数据不足 250 个交易日, 无法算 MA250
    """
    df = df.sort_values("date").reset_index(drop=True)
    mask = df["date"] == target_date
    if not mask.any():
        raise KeyError(f"target_date {target_date!r} not in index data")
    idx = int(df.index[mask][0])
    if idx < 249:
        raise ValueError(
            f"not enough history for MA250 at {target_date}: "
            f"only {idx + 1} trading days available"
        )
    window = df.iloc[: idx + 1]
    return {
        "close": float(window.iloc[-1]["close"]),
        "ma5": float(window["close"].tail(5).mean()),
        "ma20": float(window["close"].tail(20).mean()),
        "ma60": float(window["close"].tail(60).mean()),
        "ma250": float(window["close"].tail(250).mean()),
    }


def compute_pct_change(df: pd.DataFrame, target_date: str) -> float:
    """target_date 当日相对上一交易日的收盘价涨跌幅 (%, 如 -3.15 表 -3.15%)。

    异常:
        KeyError   — target_date 不在 df 中
        ValueError — target_date 是 df 的第一条, 无前一日可比
    """
    df = df.sort_values("date").reset_index(drop=True)
    mask = df["date"] == target_date
    if not mask.any():
        raise KeyError(f"target_date {target_date!r} not in index data")
    idx = int(df.index[mask][0])
    if idx < 1:
        raise ValueError(f"no previous trading day before {target_date}")
    prev_close = float(df.iloc[idx - 1]["close"])
    today_close = float(df.iloc[idx]["close"])
    if prev_close == 0:
        raise ValueError(f"previous close is zero at {target_date}")
    return (today_close - prev_close) / prev_close * 100.0


def compute_volume_ratio(df: pd.DataFrame, target_date: str) -> float:
    """5 日均量 / 20 日均量 (含 target_date 当日)。

    用 HS300 成交量作为全市场成交量代理: spec §4 没有指定成交量来源,
    选 HS300 是因为我们本就要为 MA 维度拉它的日线, 无需额外 akshare 调用。

    异常:
        KeyError   — target_date 不在 df 中
        ValueError — 数据不足 20 天, 或 20 日均量为 0
    """
    df = df.sort_values("date").reset_index(drop=True)
    mask = df["date"] == target_date
    if not mask.any():
        raise KeyError(f"target_date {target_date!r} not in index data")
    idx = int(df.index[mask][0])
    if idx < 19:
        raise ValueError(
            f"not enough history for 20d volume at {target_date}: "
            f"only {idx + 1} trading days available"
        )
    window = df.iloc[: idx + 1]
    vol5 = float(window["volume"].tail(5).mean())
    vol20 = float(window["volume"].tail(20).mean())
    if vol20 <= 0:
        raise ValueError(f"20d volume average is non-positive at {target_date}: {vol20}")
    return vol5 / vol20


# --------------------------------------------------------------------------- #
# 编排器 — 组装 RawMarketData
# --------------------------------------------------------------------------- #


def build_raw_market_data(
    date: str,
    md_path: Optional[str] = None,
    cache_dir: Optional[str] = None,
    hs300_df: Optional[pd.DataFrame] = None,
    csi1000_df: Optional[pd.DataFrame] = None,
) -> RawMarketData:
    """从复盘 MD + akshare 构建 RawMarketData。

    参数:
        date          — 目标交易日 'YYYY-MM-DD'
        md_path       — 复盘 MD 路径, 为 None 时跳过 MD 解析
        cache_dir     — akshare 缓存目录, 为 None 时不做 akshare 拉取
        hs300_df      — 预加载的 HS300 日线 DF (测试/离线模式用)
        csi1000_df    — 预加载的 CSI1000 日线 DF

    每个失败的维度都被记入 result.missing_dims 列表, 不抛异常。
    """
    result = RawMarketData(date=date)

    # ---- MD 侧 ----
    if md_path is not None:
        try:
            md_data = parse_daily_review(md_path)
        except FileNotFoundError as e:
            logger.warning("review MD not found: %s", e)
            md_data = {}
            result.warnings.append(f"review_md_missing: {md_path}")

        if "advance_decline_ratio" in md_data:
            result.advance_decline_ratio = md_data["advance_decline_ratio"]
        else:
            result.missing_dims.append("advance_decline")

        if "sentiment_delta" in md_data:
            result.sentiment_delta = md_data["sentiment_delta"]
        else:
            result.missing_dims.append("sentiment_delta")

        if "sentiment_index" in md_data:
            result.sentiment_index = md_data["sentiment_index"]
        else:
            result.missing_dims.append("sentiment_index")

        if "max_streak" in md_data:
            result.max_streak = md_data["max_streak"]
        else:
            result.missing_dims.append("streak_height")
    else:
        result.missing_dims.extend(
            ["advance_decline", "sentiment_delta", "sentiment_index", "streak_height"]
        )
        result.warnings.append("md_path=None, all MD-side dims missing")

    # ---- 指数侧 ----
    # HS300
    hs300_data = hs300_df
    if hs300_data is None and cache_dir is not None:
        try:
            hs300_data = fetch_index_daily(INDEX_SYMBOLS["hs300"], cache_dir)
        except Exception as e:
            logger.warning("fetch HS300 failed: %s", e)
            result.warnings.append(f"fetch_hs300_failed: {e}")

    # CSI1000
    csi1000_data = csi1000_df
    if csi1000_data is None and cache_dir is not None:
        try:
            csi1000_data = fetch_index_daily(INDEX_SYMBOLS["csi1000"], cache_dir)
        except Exception as e:
            logger.warning("fetch CSI1000 failed: %s", e)
            result.warnings.append(f"fetch_csi1000_failed: {e}")

    # MA + 涨跌幅
    if hs300_data is not None:
        try:
            result.hs300 = compute_index_ma(hs300_data, date)
        except (KeyError, ValueError) as e:
            logger.warning("compute HS300 MA failed: %s", e)
            result.warnings.append(f"hs300_ma_failed: {e}")
        try:
            result.hs300_pct_change = compute_pct_change(hs300_data, date)
        except (KeyError, ValueError) as e:
            logger.warning("compute HS300 pct_change failed: %s", e)
            result.warnings.append(f"hs300_pct_change_failed: {e}")

    if csi1000_data is not None:
        try:
            result.csi1000 = compute_index_ma(csi1000_data, date)
        except (KeyError, ValueError) as e:
            logger.warning("compute CSI1000 MA failed: %s", e)
            result.warnings.append(f"csi1000_ma_failed: {e}")
        try:
            result.csi1000_pct_change = compute_pct_change(csi1000_data, date)
        except (KeyError, ValueError) as e:
            logger.warning("compute CSI1000 pct_change failed: %s", e)
            result.warnings.append(f"csi1000_pct_change_failed: {e}")

    if result.hs300 is None or result.csi1000 is None:
        result.missing_dims.append("ma_position")

    # 成交量 (用 HS300)
    if hs300_data is not None:
        try:
            result.volume_ratio_5_20 = compute_volume_ratio(hs300_data, date)
        except (KeyError, ValueError) as e:
            logger.warning("compute volume ratio failed: %s", e)
            result.warnings.append(f"volume_ratio_failed: {e}")
            result.missing_dims.append("volume_trend")
    else:
        result.missing_dims.append("volume_trend")

    return result
