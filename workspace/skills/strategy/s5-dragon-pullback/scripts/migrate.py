"""S5 + classifier 历史文件 → DB 迁移脚本。

扫描指定目录的 regime_*.json / candidates_*.json / verification_*.json,
解析后写入 market.db / s5.db。完成后把成功导入的 JSON 文件移到 archive/。
对应的 MD 文件保留不动 (双写期还有效)。

用法:
    python3 migrate.py \\
        --regime-dir=/home/rooot/.openclaw/workspace-bot11/memory/review-output \\
        --s5-dir=/tmp/s5-backtest \\
        [--archive-dir=...] \\
        [--no-archive]   # 不移文件, 只导入

幂等: 多次跑不会重复写, 用 INSERT OR REPLACE。
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
S5_SKILL_DIR = os.path.dirname(SCRIPT_DIR)
STRATEGY_ROOT = os.path.dirname(S5_SKILL_DIR)
sys.path.insert(0, os.path.join(STRATEGY_ROOT, "_lib"))

import db  # noqa: E402


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# --------------------------------------------------------------------------- #
# regime → market.db.regime_daily
# --------------------------------------------------------------------------- #


def import_regime_file(conn, payload: dict) -> bool:
    """从 classifier regime_*.json payload 写入 regime_daily。返回 True 表示成功。"""
    try:
        date = payload["date"]
        score = payload.get("score", {})
        breakdown = score.get("breakdown", {}) if isinstance(score, dict) else {}
        playbook = payload.get("playbook", {}) or {}
        pos_limit = playbook.get("position_limit", {}) or {}

        conn.execute(
            """
            INSERT OR REPLACE INTO regime_daily (
                date, regime_code, regime_name, score_total,
                score_ma_position, score_advance_decline, score_sentiment_delta,
                score_sentiment_index, score_streak_height, score_volume_trend,
                raw_data_json, confidence, missing_dims_json, last_regime,
                switched, emergency_switch, emergency_reason_json, switch_warning,
                playbook_recommended_json, playbook_forbidden_json,
                position_limit_total, position_limit_single
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                payload.get("regime_code", ""),
                payload.get("regime", ""),
                score.get("total", 0) if isinstance(score, dict) else 0,
                breakdown.get("ma_position"),
                breakdown.get("advance_decline"),
                breakdown.get("sentiment_delta"),
                breakdown.get("sentiment_index"),
                breakdown.get("streak_height"),
                breakdown.get("volume_trend"),
                json.dumps(payload.get("raw_data"), ensure_ascii=False),
                payload.get("confidence", "high"),
                json.dumps(payload.get("missing_dims", []), ensure_ascii=False),
                payload.get("last_regime"),
                1 if payload.get("switched") else 0,
                1 if payload.get("emergency_switch") else 0,
                json.dumps(payload.get("emergency_reason", []), ensure_ascii=False),
                payload.get("switch_warning"),
                json.dumps(playbook.get("recommended", []), ensure_ascii=False),
                json.dumps(playbook.get("forbidden", []), ensure_ascii=False),
                float(pos_limit.get("total", 0)),
                float(pos_limit.get("single", 0)),
            ),
        )
        return True
    except Exception as e:
        logging.error(f"  regime import 失败 date={payload.get('date')}: {e}")
        return False


# --------------------------------------------------------------------------- #
# candidates → s5.db.select_runs + candidates + candidate_rejects
# --------------------------------------------------------------------------- #


def import_candidates_file(conn, payload: dict) -> tuple:
    """写 select_runs + candidates + rejects。返回 (cands_inserted, rejects_inserted)。"""
    date = payload["date"]
    regime = payload.get("regime_input", {})
    stats = payload.get("stats") or {}

    # 1. select_runs
    conn.execute(
        """
        INSERT OR REPLACE INTO select_runs (
            date, strategy, regime_code, regime_name, regime_score,
            confidence, switched, emergency_switch, position_limit_single_base,
            skipped_reason, universe_size, dragon_pool_size, passed_count,
            hot_industries_json, config_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date,
            payload.get("strategy", "S5"),
            regime.get("code", ""),
            regime.get("regime_name", ""),
            regime.get("score", 0) or 0,
            regime.get("confidence"),
            1 if regime.get("switched") else 0,
            1 if regime.get("emergency_switch") else 0,
            regime.get("position_limit_single_base"),
            payload.get("skipped_reason"),
            stats.get("universe_size"),
            stats.get("dragon_pool_size"),
            stats.get("passed_count"),
            json.dumps(stats.get("hot_industries", []), ensure_ascii=False) if stats else None,
            None,  # config_json: v1 不快照
        ),
    )

    # 2. candidates (清除该日期旧记录, 重新插)
    conn.execute("DELETE FROM candidates WHERE date = ?", (date,))
    cands_inserted = 0
    for c in payload.get("candidates") or []:
        try:
            peak = c["dragon_peak"]
            cd = c["cooldown"]
            rb = c["rebound"]
            entry = c["entry"]
            sl = c["stop_loss"]
            t1 = c.get("target_1", {})
            t2 = c.get("target_2", {})
            conn.execute(
                """
                INSERT INTO candidates (
                    date, code, name, industry,
                    dragon_peak_date, dragon_peak_close, dragon_peak_max_streak,
                    cooldown_days, cooldown_drop_pct, cooldown_t1_close,
                    rebound_t_pct, rebound_t_close, rebound_t_low, rebound_t_high, rebound_t1_high,
                    entry_zone_low, entry_zone_high, entry_rule,
                    stop_loss_price, stop_loss_rule,
                    target_1_price, target_2_price,
                    position_pct, position_calc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date,
                    c["code"],
                    c.get("name"),
                    c.get("industry"),
                    peak["date"],
                    float(peak["close"]),
                    int(peak["max_streak"]),
                    int(cd["days"]),
                    float(cd["drop_pct"]),
                    cd.get("t1_close"),
                    float(rb["t_pct"]),
                    float(rb["t_close"]),
                    rb.get("t_low"),
                    rb.get("t_high"),
                    rb.get("t1_high"),
                    float(entry["zone_low"]),
                    float(entry["zone_high"]),
                    entry.get("rule"),
                    float(sl["price"]),
                    sl.get("rule"),
                    t1.get("price"),
                    t2.get("price"),
                    float(c["position_pct"]),
                    c.get("position_calc"),
                ),
            )
            cands_inserted += 1
        except Exception as e:
            logging.error(f"  candidate import 失败 {c.get('code')}: {e}")

    # 3. rejects
    conn.execute("DELETE FROM candidate_rejects WHERE date = ?", (date,))
    rejects_inserted = 0
    for r in payload.get("reject_samples") or []:
        try:
            conn.execute(
                """
                INSERT INTO candidate_rejects (date, code, name, stage_failed, reject_reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, r["code"], r.get("name"), r["stage_failed"], r["reject_reason"]),
            )
            rejects_inserted += 1
        except Exception as e:
            logging.error(f"  reject import 失败 {r.get('code')}: {e}")

    return cands_inserted, rejects_inserted


# --------------------------------------------------------------------------- #
# verification → s5.db.verifications
# --------------------------------------------------------------------------- #


def import_verification_file(conn, payload: dict) -> int:
    t1_date = payload["t1_date"]
    t_date = payload["t_date"]
    mode = payload.get("mode", "live")

    # 清除该 t1_date 旧记录, 重新插
    conn.execute("DELETE FROM verifications WHERE t1_date = ?", (t1_date,))

    inserted = 0
    for item in payload.get("results", []):
        cand = item.get("candidate", {})
        v = item.get("verification", {})
        code = cand.get("code")
        if not code:
            continue
        # 找对应 candidate id
        row = conn.execute(
            "SELECT id FROM candidates WHERE date = ? AND code = ?",
            (t_date, code),
        ).fetchone()
        candidate_id = row["id"] if row else 0
        try:
            conn.execute(
                """
                INSERT INTO verifications (
                    t_date, t1_date, candidate_id, code, mode,
                    status, entry_status, entry_price, exit_price, exit_reason, pnl_pct,
                    t1_open, t1_high, t1_low, t1_close,
                    live_open_price, live_current, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t_date,
                    t1_date,
                    candidate_id,
                    code,
                    mode,
                    v.get("status", "unknown"),
                    v.get("entry_status"),
                    v.get("entry_price"),
                    v.get("exit_price"),
                    v.get("exit_reason"),
                    v.get("pnl_pct"),
                    v.get("t1_open"),
                    v.get("t1_high"),
                    v.get("t1_low"),
                    v.get("t1_close"),
                    v.get("open_price"),  # live mode 字段
                    v.get("current"),     # live mode 字段
                    v.get("note"),
                ),
            )
            inserted += 1
        except Exception as e:
            logging.error(f"  verification import 失败 {code}: {e}")
    return inserted


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #


def run_migrate(regime_dir: str, s5_dir: str, archive_dir: str, do_archive: bool):
    setup_logging()
    db.init_market_db()
    db.init_s5_db()

    counts = {
        "regime_files": 0, "regime_imported": 0,
        "candidates_files": 0, "candidates_inserted": 0, "rejects_inserted": 0,
        "verification_files": 0, "verifications_inserted": 0,
        "archived": 0,
    }

    # 1. regime
    market_conn = db.get_market_db()
    try:
        for path in sorted(glob.glob(os.path.join(regime_dir, "regime_*.json"))):
            counts["regime_files"] += 1
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if import_regime_file(market_conn, payload):
                counts["regime_imported"] += 1
                if do_archive:
                    _archive_file(path, archive_dir)
                    counts["archived"] += 1
        market_conn.commit()
    finally:
        market_conn.close()

    # 2. candidates + 3. verification (s5.db)
    s5_conn = db.get_s5_db()
    try:
        for path in sorted(glob.glob(os.path.join(s5_dir, "candidates_*.json"))):
            counts["candidates_files"] += 1
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            ci, ri = import_candidates_file(s5_conn, payload)
            counts["candidates_inserted"] += ci
            counts["rejects_inserted"] += ri
            if do_archive:
                _archive_file(path, archive_dir)
                counts["archived"] += 1
        s5_conn.commit()  # commit before verifications 引用 candidates.id

        for path in sorted(glob.glob(os.path.join(s5_dir, "verification_*.json"))):
            counts["verification_files"] += 1
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            counts["verifications_inserted"] += import_verification_file(s5_conn, payload)
            if do_archive:
                _archive_file(path, archive_dir)
                counts["archived"] += 1
        s5_conn.commit()
    finally:
        s5_conn.close()

    print()
    print("=" * 50)
    print("迁移汇总")
    print("=" * 50)
    print(f"  regime files:       {counts['regime_files']} 扫到, {counts['regime_imported']} 导入")
    print(f"  candidates files:   {counts['candidates_files']} 扫到")
    print(f"  candidates 插入:    {counts['candidates_inserted']}")
    print(f"  rejects 插入:       {counts['rejects_inserted']}")
    print(f"  verification files: {counts['verification_files']} 扫到")
    print(f"  verifications 插入: {counts['verifications_inserted']}")
    if do_archive:
        print(f"  归档文件:          {counts['archived']}")
        print(f"  归档目录:          {archive_dir}")
    return counts


def _archive_file(src: str, archive_dir: str):
    os.makedirs(archive_dir, exist_ok=True)
    dst = os.path.join(archive_dir, os.path.basename(src))
    shutil.move(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime-dir", required=True, help="classifier regime json 目录")
    ap.add_argument("--s5-dir", required=True, help="s5 candidates/verification json 目录 (可与 regime-dir 相同)")
    ap.add_argument(
        "--archive-dir",
        default=None,
        help="归档目录, 默认 = regime-dir/archive",
    )
    ap.add_argument(
        "--no-archive",
        action="store_true",
        help="只导入, 不移文件",
    )
    args = ap.parse_args()

    archive_dir = args.archive_dir or os.path.join(args.regime_dir, "archive")
    run_migrate(args.regime_dir, args.s5_dir, archive_dir, do_archive=not args.no_archive)


if __name__ == "__main__":
    main()
