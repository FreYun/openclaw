"""S5 输出层 — MD 人可读 + JSON 机器可读。

JSON 接口由下游策略 skill / bot 消费, 字段稳定不可随意改。
"""

from __future__ import annotations

import json
import os
from datetime import datetime


# --------------------------------------------------------------------------- #
# JSON 输出
# --------------------------------------------------------------------------- #


def write_json(output_path: str, payload: dict):
    """写 candidates_YYYY-MM-DD.json"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# Markdown 输出
# --------------------------------------------------------------------------- #


def render_md(payload: dict) -> str:
    """把 select 的 payload 渲染成人可读的 Markdown。"""
    date = payload["date"]
    strategy = payload["strategy"]
    candidates = payload.get("candidates", [])
    skipped = payload.get("skipped_reason")
    stats = payload.get("stats")
    regime_input = payload.get("regime_input", {})

    lines = []
    lines.append(f"# S5 龙回头候选清单 — {date}")
    lines.append("")

    # 上游 regime
    lines.append("## 上游 Regime")
    lines.append("")
    lines.append(f"- **regime**: {regime_input.get('regime_name', regime_input.get('code', '?'))} (score={regime_input.get('score', '?')})")
    lines.append(f"- **confidence**: {regime_input.get('confidence', '?')}")
    lines.append(f"- **switched**: {regime_input.get('switched', False)}")
    lines.append(f"- **emergency_switch**: {regime_input.get('emergency_switch', False)}")
    lines.append(f"- **base 单票上限**: {regime_input.get('position_limit_single_base', '?')}")
    lines.append("")

    # 跳过路径
    if skipped:
        lines.append("## ⏭️ 本日跳过")
        lines.append("")
        lines.append(f"**原因**: {skipped}")
        lines.append("")
        return "\n".join(lines)

    # Stats
    if stats:
        lines.append("## 选股漏斗")
        lines.append("")
        lines.append(f"| 阶段 | 数量 |")
        lines.append(f"|---|---|")
        lines.append(f"| 候选股池 (universe) | {stats.get('universe_size', 0)} |")
        lines.append(f"| 龙头池 (≥2 连板) | {stats.get('dragon_pool_size', 0)} |")
        lines.append(f"| 信号通过 (passed) | {stats.get('passed_count', 0)} |")
        lines.append("")

    # Candidates
    if not candidates:
        lines.append("## 候选清单")
        lines.append("")
        lines.append("**今日 0 只 candidate**。可能原因: 无前期龙头进入冷却 / 无足够大反包 / 行情偏弱无热门题材。")
        lines.append("")
        # 拒因 top
        rejects = payload.get("reject_samples", [])
        if rejects:
            lines.append("### 拒因抽样 (前 5 只最接近的)")
            lines.append("")
            for r in rejects[:5]:
                lines.append(f"- **{r['code']} {r['name']}** — {r['reject_reason']}")
            lines.append("")
        return "\n".join(lines)

    lines.append(f"## 候选清单 ({len(candidates)} 只)")
    lines.append("")
    for i, c in enumerate(candidates, 1):
        lines.append(f"### {i}. {c['code']} {c['name']} ({c['industry']})")
        lines.append("")
        # 三段证据
        peak = c["dragon_peak"]
        cd = c["cooldown"]
        rb = c["rebound"]
        lines.append(f"- **龙头日**: {peak['date']} 收 {peak['close']:.2f}, 最高 {peak['max_streak']} 板")
        lines.append(f"- **冷却**: {cd['days']} 个交易日, 阶段跌幅 {cd['drop_pct']:.2f}%")
        lines.append(f"- **反包**: T 日涨 {rb['t_pct']:.2f}%, 收 {rb['t_close']:.2f}, T-1 最高 {rb['t1_high']:.2f}")
        lines.append("")
        # 交易计划
        e = c["entry"]
        sl = c["stop_loss"]
        t1 = c["target_1"]
        t2 = c["target_2"]
        lines.append(f"- **入场区**: {e['zone_low']:.2f} ~ {e['zone_high']:.2f} ({e['rule']})")
        lines.append(f"- **止损**: {sl['price']:.2f} ({sl['rule']})")
        lines.append(f"- **止盈 1**: {t1['price']:.2f} (+{t1['pct']:.0f}%)")
        lines.append(f"- **止盈 2**: {t2['price']:.2f} (+{t2['pct']:.0f}%)")
        lines.append(f"- **建议仓位**: {c['position_pct'] * 100:.2f}%")
        lines.append(f"  - 计算: `{c['position_calc']}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> 本清单仅供参考, 实盘前请人工复核。T+1 开盘 5-10 分钟跑 `verify.py` 检查实际开盘是否触发买点。")
    lines.append("")
    return "\n".join(lines)


def write_md(output_path: str, payload: dict):
    """写 candidates_YYYY-MM-DD.md"""
    md = render_md(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
