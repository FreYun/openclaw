"""输出层 — MD / JSON / regime-log 三种写入格式。

本模块负责把 classify 的决策结果渲染为三种输出:

- MD 文件 (regime_YYYY-MM-DD.md)   — 人可读, 对齐 spec §7 示例
- JSON 文件 (regime_YYYY-MM-DD.json) — 机器可读, 下游 strategy skill 的契约
- regime-log.md                     — 追加一行, 供 3 日确认读取历史

同时提供 parse_regime_log 读取历史日志, 给 classify.py 用来构造
scores_window (供 apply_3day_confirmation)。

spec §7 的 JSON 字段名是下游约定, 改名要非常小心。
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from regime_rules import REGIME_CODE_TO_NAME, REGIME_NAME_TO_CODE


# --------------------------------------------------------------------------- #
# 结果容器
# --------------------------------------------------------------------------- #


@dataclass
class ClassifyResult:
    """一次 classify 的完整结果, 所有下游消费者从这里取数据。"""

    date: str

    # 得分
    score_total: int
    score_breakdown: dict  # {ma_position, advance_decline, sentiment_delta,
    #                        sentiment_index, streak_height, volume_trend}

    # 原始数据 (JSON 输出用)
    raw_data: dict

    # Regime 决策
    regime_code: str
    last_regime_code: str
    switched: bool
    bootstrap: bool

    # 降级
    confidence: str  # "high" | "medium" | "low"
    missing_dims: list

    # 提示
    switch_warning: Optional[str] = None

    # 战法
    playbook: dict = field(default_factory=dict)

    # 逃生门
    emergency_switch: bool = False
    emergency_direction: Optional[str] = None  # "up" | "down" | None
    emergency_reason: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 降级策略 (spec §8)
# --------------------------------------------------------------------------- #


def determine_confidence(missing_dim_count: int) -> str:
    """按缺失维度数返回可信度标签。"""
    if missing_dim_count <= 0:
        return "high"
    if missing_dim_count <= 2:
        return "medium"
    return "low"


# --------------------------------------------------------------------------- #
# JSON 输出
# --------------------------------------------------------------------------- #


def result_to_json(result: ClassifyResult) -> dict:
    """构造 spec §7 格式的 JSON dict。

    关键字段名 (下游契约, 改名需谨慎):
      date / regime / regime_code / score.{total,breakdown} /
      raw_data / confidence / missing_dims / switch_warning /
      playbook.{recommended,forbidden,position_limit.{total,single}} /
      last_regime / switched / emergency_switch / emergency_reason
    """
    return {
        "date": result.date,
        "regime": REGIME_CODE_TO_NAME[result.regime_code],
        "regime_code": result.regime_code,
        "score": {
            "total": result.score_total,
            "breakdown": dict(result.score_breakdown),
        },
        "raw_data": dict(result.raw_data),
        "confidence": result.confidence,
        "missing_dims": list(result.missing_dims),
        "switch_warning": result.switch_warning,
        "playbook": dict(result.playbook),
        "last_regime": REGIME_CODE_TO_NAME[result.last_regime_code],
        "switched": result.switched,
        "emergency_switch": result.emergency_switch,
        "emergency_reason": list(result.emergency_reason),
    }


def write_json(result: ClassifyResult, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result_to_json(result), f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# MD 输出
# --------------------------------------------------------------------------- #


_REGIME_EMOJI = {
    "STRONG_BULL": "🟢🔥",
    "STRONG_RANGE": "🟢",
    "NEUTRAL_RANGE": "🟡",
    "WEAK_RANGE": "🟠",
    "BEAR": "🔴",
}


def _fmt_score(s: int) -> str:
    return f"+{s}" if s > 0 else str(s)


def _fmt_breakdown_value(val) -> str:
    if val is None:
        return "-"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _fmt_ma_position_raw(val) -> str:
    """ma_position 字段是嵌套 dict, 需要压成一行人看的简短摘要。

    接受两种格式:
    - 真实数据: {hs300: {close, ma*, ...}, csi1000: {...}, hs300_pct_change, csi1000_pct_change}
    - 测试 mock: {hs300: "above_20", csi1000: "..."}  (简化占位符)
    - 其它: 退化到标量格式
    """
    if not isinstance(val, dict):
        return _fmt_breakdown_value(val)

    def _short(idx):
        if idx is None:
            return "-"
        if isinstance(idx, dict) and "close" in idx and "ma20" in idx:
            return f"c={idx['close']:.0f} MA20={idx['ma20']:.0f}"
        return str(idx)

    hs300 = val.get("hs300")
    csi1000 = val.get("csi1000")
    hs_chg = val.get("hs300_pct_change")
    csi_chg = val.get("csi1000_pct_change")

    chg_part = ""
    if isinstance(hs_chg, (int, float)) and isinstance(csi_chg, (int, float)):
        chg_part = f" (日涨跌 HS300 {hs_chg:+.2f}% / CSI1000 {csi_chg:+.2f}%)"
    return f"HS300 {_short(hs300)} / CSI1000 {_short(csi1000)}{chg_part}"


def render_md(result: ClassifyResult) -> str:
    """渲染 spec §7 风格的 MD 报告。"""
    regime_name = REGIME_CODE_TO_NAME[result.regime_code]
    last_name = REGIME_CODE_TO_NAME[result.last_regime_code]
    emoji = _REGIME_EMOJI.get(result.regime_code, "")

    lines: list = []
    lines.append(f"# 市场 Regime 判断 — {result.date}")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append(f"- **当前 regime**：{regime_name} {emoji}")
    lines.append(f"- **总分**：{_fmt_score(result.score_total)} / 12")

    if result.emergency_switch:
        icon = "🚨" if result.emergency_direction == "down" else "🚀"
        reasons = ", ".join(result.emergency_reason) if result.emergency_reason else "-"
        lines.append(
            f"- **{icon} 逃生门触发**：方向 {result.emergency_direction}, 原因 [{reasons}] "
            f"(从 {last_name} 切到 {regime_name})"
        )
    elif result.switched:
        lines.append(f"- **已切换**：{last_name} → {regime_name}")
    elif result.bootstrap:
        lines.append(f"- **bootstrap**：历史不足 3 日, 维持默认 {last_name}")

    if result.switch_warning:
        lines.append(f"- **切换警戒**：{result.switch_warning}")

    pb = result.playbook or {}
    if pb.get("recommended"):
        recs = " → ".join(
            f"{r['id']} {r.get('name', '')}" + (f" ({r['mode']})" if r.get("mode") else "")
            for r in pb["recommended"]
        )
        lines.append(f"- **建议战法**：{recs}")
    if pb.get("forbidden"):
        lines.append(f"- **禁止战法**：{', '.join(pb['forbidden'])}")
    if pb.get("position_limit"):
        total = pb["position_limit"].get("total")
        single = pb["position_limit"].get("single")
        if total is not None and single is not None:
            lines.append(f"- **仓位上限**：总 {int(total * 100)}% / 单票 {int(single * 100)}%")

    lines.append("")
    lines.append("## 六维打分明细")
    lines.append("")
    lines.append("| 维度 | 原始值 | 得分 |")
    lines.append("|---|---|---|")

    dim_labels = [
        ("ma_position", "指数 vs 均线"),
        ("advance_decline", "涨跌家数比"),
        ("sentiment_delta", "情绪(涨停-跌停)"),
        ("sentiment_index", "情绪评分"),
        ("streak_height", "最高连板"),
        ("volume_trend", "成交量趋势"),
    ]
    raw = result.raw_data or {}
    for key, label in dim_labels:
        score = result.score_breakdown.get(key, 0)
        raw_val = raw.get(key)
        if key == "ma_position":
            raw_text = _fmt_ma_position_raw(raw_val)
        else:
            raw_text = _fmt_breakdown_value(raw_val)
        lines.append(f"| {label} | {raw_text} | {_fmt_score(score)} |")

    lines.append("")
    lines.append("## 战法推荐详情")
    lines.append("")
    if not pb.get("recommended"):
        lines.append("(无)")
    else:
        for r in pb["recommended"]:
            mode_tag = f" ({r['mode']})" if r.get("mode") else ""
            lines.append(f"- **{r['id']} {r.get('name', '')}**{mode_tag} — 优先级 {r['priority']}")

    if pb.get("forbidden"):
        lines.append("")
        lines.append("## 禁止战法")
        lines.append("")
        for sid in pb["forbidden"]:
            lines.append(f"- {sid}")

    lines.append("")
    lines.append("## 数据可信度")
    lines.append("")
    conf_mark = {"high": "✅", "medium": "⚠️", "low": "❌"}.get(result.confidence, "?")
    lines.append(f"{conf_mark} **{result.confidence}**")
    if result.missing_dims:
        lines.append(f"- 缺失维度: {', '.join(result.missing_dims)}")
    else:
        lines.append("- 所有 6 维数据完整")

    return "\n".join(lines) + "\n"


def write_md(result: ClassifyResult, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_md(result))


# --------------------------------------------------------------------------- #
# regime-log.md — 追加 + 读取
# --------------------------------------------------------------------------- #


_LOG_HEADER = "| 日期 | 6维原始值 | 6维得分 | 总分 | 当日 regime | 是否切换 |"
_LOG_SEPARATOR = "|---|---|---|---|---|---|"


def render_log_row(result: ClassifyResult) -> str:
    """单行日志, spec §6 格式。"""
    raw = result.raw_data or {}
    bd = result.score_breakdown or {}

    def _r(key):
        v = raw.get(key)
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    raw_cells = (
        f"MA:{_r('ma_position')}, 涨跌:{_r('advance_decline')}, "
        f"涨停差:{_r('sentiment_delta')}, 评分:{_r('sentiment_index')}, "
        f"连板:{_r('streak_height')}, 量比:{_r('volume_trend')}"
    )
    score_cells = ",".join(
        _fmt_score(bd.get(k, 0))
        for k in [
            "ma_position",
            "advance_decline",
            "sentiment_delta",
            "sentiment_index",
            "streak_height",
            "volume_trend",
        ]
    )

    regime_name = REGIME_CODE_TO_NAME[result.regime_code]

    switch_cell_parts: list = []
    if result.emergency_switch:
        icon = "🚨 EMERGENCY_DOWN" if result.emergency_direction == "down" else "🚀 EMERGENCY_UP"
        switch_cell_parts.append(icon)
    if result.switched and not result.emergency_switch:
        switch_cell_parts.append(
            f"{REGIME_CODE_TO_NAME[result.last_regime_code]}→{regime_name}"
        )
    if not switch_cell_parts:
        switch_cell_parts.append("-")
    switch_cell = " ".join(switch_cell_parts)

    return (
        f"| {result.date} | {raw_cells} | {score_cells} | "
        f"{_fmt_score(result.score_total)} | {regime_name} | {switch_cell} |"
    )


def append_log(result: ClassifyResult, log_path: str) -> None:
    """追加一行到 regime-log.md。

    - 文件不存在时创建, 写入表头
    - 同一日期已有一行时, 替换为新行 (handle 重跑场景)
    """
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    new_row = render_log_row(result)

    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("# Regime 决策日志\n\n")
            f.write(f"{_LOG_HEADER}\n{_LOG_SEPARATOR}\n{new_row}\n")
        return

    with open(log_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    # 找到并删除同日期的旧行 (如果有)
    date_pattern = re.compile(rf"^\|\s*{re.escape(result.date)}\s*\|")
    filtered: list = [ln for ln in lines if not date_pattern.match(ln)]

    # 确保有表头
    if _LOG_HEADER not in filtered:
        filtered = ["# Regime 决策日志", "", _LOG_HEADER, _LOG_SEPARATOR]

    filtered.append(new_row)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(filtered) + "\n")


# --------------------------------------------------------------------------- #
# regime-log 读取
# --------------------------------------------------------------------------- #


_LOG_ROW_RE = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|"          # 1 日期
    r"\s*([^|]*)\s*\|"                         # 2 原始值
    r"\s*([^|]*)\s*\|"                         # 3 六维得分
    r"\s*([+\-]?\d+)\s*\|"                     # 4 总分
    r"\s*([^|]*?)\s*\|"                        # 5 regime 中文名
    r"\s*([^|]*?)\s*\|"                        # 6 是否切换
)


def parse_regime_log(log_path: str) -> list:
    """读取 regime-log.md, 返回按日期升序的 entries。

    返回每条: {
        date: "YYYY-MM-DD",
        total_score: int,
        regime_code: str,
        switched: bool,
        emergency_switch: bool,
    }

    若文件不存在或为空, 返回空列表。解析失败的行被跳过并记录警告。
    """
    import logging

    logger = logging.getLogger(__name__)

    if not os.path.exists(log_path):
        return []

    entries: list = []
    with open(log_path, encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\n")
            m = _LOG_ROW_RE.match(line)
            if not m:
                continue
            try:
                date = m.group(1)
                total_score = int(m.group(4))
                regime_name = m.group(5).strip()
                switch_cell = m.group(6).strip()
                regime_code = REGIME_NAME_TO_CODE.get(regime_name)
                if regime_code is None:
                    logger.warning("unknown regime name in log: %s", regime_name)
                    continue
                emergency_switch = "EMERGENCY" in switch_cell
                switched = emergency_switch or ("→" in switch_cell)
                entries.append(
                    {
                        "date": date,
                        "total_score": total_score,
                        "regime_code": regime_code,
                        "switched": switched,
                        "emergency_switch": emergency_switch,
                    }
                )
            except Exception as e:
                logger.warning("failed to parse log line %d: %s (%s)", lineno, line, e)

    entries.sort(key=lambda e: e["date"])
    return entries


# --------------------------------------------------------------------------- #
# 一次写三种输出
# --------------------------------------------------------------------------- #


def write_outputs(
    result: ClassifyResult,
    md_path: str,
    json_path: str,
    log_path: str,
) -> dict:
    """一次性写 MD / JSON / 追加日志, 返回实际写入的路径字典。

    同时写入 market.db.regime_daily (CLASSIFIER_OUTPUT 控制双写, 默认 both)。
    """
    output_target = os.environ.get("CLASSIFIER_OUTPUT", "both").lower()
    paths = {}

    if output_target in ("file", "both"):
        write_md(result, md_path)
        write_json(result, json_path)
        append_log(result, log_path)
        paths = {"md": md_path, "json": json_path, "log": log_path}

    if output_target in ("db", "both"):
        try:
            _write_regime_to_db(result_to_json(result))
            _write_regime_to_classify_daily(result)
            paths["db"] = "market.db.regime_daily + regime_classify_daily"
        except Exception as e:
            logging.warning(f"market.db 写入失败 (CLASSIFIER_OUTPUT={output_target}): {e}")

    return paths


def _write_regime_to_classify_daily(result: ClassifyResult):
    """把 ClassifyResult 同步写入 regime_classify_daily (rules_version='v2')。

    字段口径与 backfill/load_to_db.py 保持一致, 下游按 regime_name + switched
    查仓位规则 (见 memory/position-sizing-v2-entry-only.md)。
    """
    _here = os.path.dirname(os.path.abspath(__file__))
    _classifier_root = os.path.dirname(_here)
    _strategy_root = os.path.dirname(_classifier_root)
    _lib_dir = os.path.join(_strategy_root, "_lib")
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)
    import db as _db

    conn = _db.get_market_db()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO regime_classify_daily (
                trade_date, rules_version, total_score,
                score_ma_position, score_advance_decline, score_sentiment_delta,
                score_sentiment_index, score_streak_height, score_volume_trend,
                regime_code, regime_name, last_regime_code, switched, bootstrap,
                emergency_switch, emergency_direction, emergency_reason,
                confidence, missing_dims
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                result.date,
                "v2",
                result.score_total,
                result.score_breakdown.get("ma_position"),
                result.score_breakdown.get("advance_decline"),
                result.score_breakdown.get("sentiment_delta"),
                result.score_breakdown.get("sentiment_index"),
                result.score_breakdown.get("streak_height"),
                result.score_breakdown.get("volume_trend"),
                result.regime_code,
                REGIME_CODE_TO_NAME[result.regime_code],
                result.last_regime_code,
                1 if result.switched else 0,
                1 if result.bootstrap else 0,
                1 if result.emergency_switch else 0,
                result.emergency_direction,
                ";".join(result.emergency_reason) if result.emergency_reason else None,
                result.confidence,
                ";".join(result.missing_dims) if result.missing_dims else None,
            ),
        )
        conn.commit()
        logging.info(f"market.db 写入 regime_classify_daily(v2): date={result.date}")
    finally:
        conn.close()


def _write_regime_to_db(payload: dict):
    """把 result_to_json 的 dict 写入 market.db.regime_daily。"""
    # 按需 import, 避免单元测试时强制依赖 _lib/db
    _here = os.path.dirname(os.path.abspath(__file__))
    _classifier_root = os.path.dirname(_here)
    _strategy_root = os.path.dirname(_classifier_root)
    _lib_dir = os.path.join(_strategy_root, "_lib")
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)
    import db as _db
    import json as _json

    _db.init_market_db()
    conn = _db.get_market_db()
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
                int(score.get("total", 0) or 0) if isinstance(score, dict) else 0,
                breakdown.get("ma_position"),
                breakdown.get("advance_decline"),
                breakdown.get("sentiment_delta"),
                breakdown.get("sentiment_index"),
                breakdown.get("streak_height"),
                breakdown.get("volume_trend"),
                _json.dumps(payload.get("raw_data"), ensure_ascii=False),
                payload.get("confidence", "high"),
                _json.dumps(payload.get("missing_dims", []), ensure_ascii=False),
                payload.get("last_regime"),
                1 if payload.get("switched") else 0,
                1 if payload.get("emergency_switch") else 0,
                _json.dumps(payload.get("emergency_reason", []), ensure_ascii=False),
                payload.get("switch_warning"),
                _json.dumps(playbook.get("recommended", []), ensure_ascii=False),
                _json.dumps(playbook.get("forbidden", []), ensure_ascii=False),
                float(pos_limit.get("total", 0) or 0),
                float(pos_limit.get("single", 0) or 0),
            ),
        )
        conn.commit()
        logging.info(f"market.db 写入 regime_daily: date={date}")
    finally:
        conn.close()
