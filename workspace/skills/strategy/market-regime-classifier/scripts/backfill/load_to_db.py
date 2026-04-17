"""把 CSV 派生数据 + 回放结果灌到 SQLite 表。

数据流:
    /tmp/regime_raw_3y.csv          → market.db.regime_raw_daily
    /tmp/regime_replay_3y.csv       → market.db.regime_classify_daily (rules_version='v1')
    /tmp/regime_replay_3y_v2.csv    → market.db.regime_classify_daily (rules_version='v2')

幂等: INSERT OR REPLACE, 重跑安全。

用法:
    python3 load_to_db.py                       # 全量灌入默认 CSV
    python3 load_to_db.py --raw /tmp/r.csv      # 自定义 raw CSV
    python3 load_to_db.py --skip-raw            # 仅灌 classify 表
    python3 load_to_db.py --skip-classify       # 仅灌 raw 表
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect  # noqa: E402

logger = logging.getLogger("load")


# --------------------------------------------------------------------------- #
# regime_raw_daily
# --------------------------------------------------------------------------- #


def load_regime_raw(conn, csv_path: str) -> int:
    """从 derive_raw_data.py 输出的 CSV 灌 regime_raw_daily 表。"""
    if not os.path.exists(csv_path):
        logger.warning(f"raw CSV 不存在: {csv_path}")
        return 0

    cols = [
        "trade_date", "total", "up", "down", "flat", "advance_decline_ratio",
        "limit_up_count", "limit_down_count", "sentiment_delta", "sentiment_index",
        "max_streak", "total_amount_yi",
        "hs300_close", "hs300_pct_chg", "csi1000_close", "csi1000_pct_chg",
        "shanghai_close", "shenzhen_close", "index_amount_yi",
    ]
    placeholders = ",".join(["?"] * len(cols))
    sql = f"INSERT OR REPLACE INTO regime_raw_daily ({','.join(cols)}) VALUES ({placeholders})"

    rows_inserted = 0
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for r in reader:
            batch.append(tuple(
                _to_num(r.get(c)) if c not in ("trade_date",) else r.get(c)
                for c in cols
            ))
        if batch:
            conn.executemany(sql, batch)
            rows_inserted = len(batch)

    conn.commit()
    return rows_inserted


# --------------------------------------------------------------------------- #
# regime_classify_daily
# --------------------------------------------------------------------------- #


def load_regime_classify(conn, csv_path: str, rules_version: str) -> int:
    """从 replay.py 输出的 CSV 灌 regime_classify_daily 表。

    csv 列: date,total_score,ma_position,advance_decline,sentiment_delta,
            sentiment_index,streak_height,volume_trend,regime_code,regime_name,
            last_regime_code,switched,bootstrap,emergency_switch,
            emergency_direction,emergency_reason,confidence,missing_dims
    """
    if not os.path.exists(csv_path):
        logger.warning(f"replay CSV 不存在: {csv_path}")
        return 0

    sql = """
        INSERT OR REPLACE INTO regime_classify_daily (
            trade_date, rules_version,
            total_score, score_ma_position, score_advance_decline,
            score_sentiment_delta, score_sentiment_index,
            score_streak_height, score_volume_trend,
            regime_code, regime_name, last_regime_code,
            switched, bootstrap,
            emergency_switch, emergency_direction, emergency_reason,
            confidence, missing_dims
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    batch = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            batch.append((
                r["date"], rules_version,
                _to_num(r["total_score"]),
                _to_num(r["ma_position"]),
                _to_num(r["advance_decline"]),
                _to_num(r["sentiment_delta"]),
                _to_num(r["sentiment_index"]),
                _to_num(r["streak_height"]),
                _to_num(r["volume_trend"]),
                r["regime_code"],
                r["regime_name"],
                r["last_regime_code"],
                _to_num(r["switched"]),
                _to_num(r["bootstrap"]),
                _to_num(r["emergency_switch"]),
                r["emergency_direction"] or None,
                r["emergency_reason"] or None,
                r["confidence"],
                r["missing_dims"] or None,
            ))
    if batch:
        conn.executemany(sql, batch)
        conn.commit()
    return len(batch)


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #


def _to_num(v):
    """字符串转数值, 空值返回 None."""
    if v is None or v == "":
        return None
    try:
        if "." in str(v):
            return float(v)
        return int(v)
    except (ValueError, TypeError):
        return v


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main():
    parser = argparse.ArgumentParser(description="把 CSV 派生/回放数据灌入 SQLite")
    parser.add_argument("--raw", default="/tmp/regime_raw_3y.csv", help="派生数据 CSV")
    parser.add_argument("--v1", default="/tmp/regime_replay_3y.csv", help="v1 回放 CSV")
    parser.add_argument("--v2", default="/tmp/regime_replay_3y_v2.csv", help="v2 回放 CSV")
    parser.add_argument("--skip-raw", action="store_true")
    parser.add_argument("--skip-classify", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    conn = connect()

    if not args.skip_raw:
        n = load_regime_raw(conn, args.raw)
        logger.info(f"regime_raw_daily 灌入: {n} 行 (来自 {args.raw})")

    if not args.skip_classify:
        n_v1 = load_regime_classify(conn, args.v1, "v1")
        logger.info(f"regime_classify_daily v1 灌入: {n_v1} 行 (来自 {args.v1})")
        n_v2 = load_regime_classify(conn, args.v2, "v2")
        logger.info(f"regime_classify_daily v2 灌入: {n_v2} 行 (来自 {args.v2})")

    # 行数总览
    logger.info("===== 表行数 =====")
    for t in ("regime_raw_daily", "regime_classify_daily", "regime_strategy_nav"):
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        logger.info(f"  {t}: {n} 行")
    n_v1 = conn.execute(
        "SELECT COUNT(*) FROM regime_classify_daily WHERE rules_version='v1'"
    ).fetchone()[0]
    n_v2 = conn.execute(
        "SELECT COUNT(*) FROM regime_classify_daily WHERE rules_version='v2'"
    ).fetchone()[0]
    logger.info(f"    v1: {n_v1} | v2: {n_v2}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
