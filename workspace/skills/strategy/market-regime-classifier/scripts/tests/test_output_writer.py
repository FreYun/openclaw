"""output_writer.py 单元测试。

覆盖:
1. determine_confidence — spec §8 降级阈值
2. result_to_json — JSON 字段名/结构, 尤其是下游契约字段
3. render_md — 关键章节存在 + 紧急标记/切换提示渲染
4. append_log — 首次创建/幂等重跑 (同一天替换)/emergency 标记
5. parse_regime_log — 读回写入的日志, 循环自洽
6. write_outputs — 端到端一次写三件
"""

import json
import os

import pytest

from output_writer import (
    ClassifyResult,
    append_log,
    determine_confidence,
    parse_regime_log,
    render_log_row,
    render_md,
    result_to_json,
    write_outputs,
)


def _make_result(
    date: str = "2026-04-13",
    regime_code: str = "NEUTRAL_RANGE",
    last_regime_code: str = "NEUTRAL_RANGE",
    score_total: int = 3,
    switched: bool = False,
    emergency_switch: bool = False,
    emergency_direction=None,
    emergency_reason=None,
    switch_warning=None,
    missing_dims=None,
    bootstrap: bool = False,
) -> ClassifyResult:
    return ClassifyResult(
        date=date,
        score_total=score_total,
        score_breakdown={
            "ma_position": 1,
            "advance_decline": 0,
            "sentiment_delta": 1,
            "sentiment_index": 1,
            "streak_height": 0,
            "volume_trend": 0,
        },
        raw_data={
            "ma_position": {"hs300": "above_20", "csi1000": "below_20"},
            "advance_decline": 0.55,
            "sentiment_delta": 25,
            "sentiment_index": 58,
            "streak_height": 3,
            "volume_trend": 1.05,
        },
        regime_code=regime_code,
        last_regime_code=last_regime_code,
        switched=switched,
        bootstrap=bootstrap,
        confidence="high",
        missing_dims=missing_dims or [],
        switch_warning=switch_warning,
        playbook={
            "recommended": [
                {"id": "S5", "name": "龙回头", "priority": 1},
                {"id": "S4", "name": "回踩战法", "priority": 2, "mode": "strict"},
            ],
            "forbidden": ["S1", "S2", "S6"],
            "position_limit": {"total": 0.50, "single": 0.20},
        },
        emergency_switch=emergency_switch,
        emergency_direction=emergency_direction,
        emergency_reason=emergency_reason or [],
    )


# --------------------------------------------------------------------------- #
# determine_confidence
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "n,expected",
    [(0, "high"), (1, "medium"), (2, "medium"), (3, "low"), (6, "low")],
)
def test_determine_confidence(n, expected):
    assert determine_confidence(n) == expected


# --------------------------------------------------------------------------- #
# result_to_json
# --------------------------------------------------------------------------- #


class TestResultToJson:
    def test_basic_shape(self):
        r = _make_result()
        j = result_to_json(r)
        # 下游契约必须存在的关键字段
        for key in [
            "date", "regime", "regime_code", "score", "raw_data",
            "confidence", "missing_dims", "switch_warning", "playbook",
            "last_regime", "switched", "emergency_switch", "emergency_reason",
        ]:
            assert key in j, f"missing key: {key}"

    def test_regime_name_is_chinese(self):
        j = result_to_json(_make_result(regime_code="NEUTRAL_RANGE"))
        assert j["regime"] == "中性震荡"
        assert j["regime_code"] == "NEUTRAL_RANGE"

    def test_score_breakdown_nested(self):
        j = result_to_json(_make_result())
        assert j["score"]["total"] == 3
        assert "ma_position" in j["score"]["breakdown"]

    def test_playbook_position_limit(self):
        j = result_to_json(_make_result())
        assert j["playbook"]["position_limit"]["total"] == 0.50
        assert j["playbook"]["position_limit"]["single"] == 0.20
        assert set(j["playbook"]["forbidden"]) == {"S1", "S2", "S6"}

    def test_emergency_fields_default_false(self):
        j = result_to_json(_make_result())
        assert j["emergency_switch"] is False
        assert j["emergency_reason"] == []

    def test_emergency_fields_set(self):
        r = _make_result(
            emergency_switch=True,
            emergency_direction="down",
            emergency_reason=["total_drop_5", "index_crash"],
            regime_code="WEAK_RANGE",
        )
        j = result_to_json(r)
        assert j["emergency_switch"] is True
        assert j["emergency_reason"] == ["total_drop_5", "index_crash"]


# --------------------------------------------------------------------------- #
# render_md
# --------------------------------------------------------------------------- #


class TestRenderMd:
    def test_contains_title_with_date(self):
        md = render_md(_make_result(date="2026-03-20"))
        assert "# 市场 Regime 判断 — 2026-03-20" in md

    def test_conclusion_section(self):
        md = render_md(_make_result())
        assert "## 结论" in md
        assert "中性震荡" in md
        assert "+3 / 12" in md

    def test_breakdown_table_has_six_dims(self):
        md = render_md(_make_result())
        assert "## 六维打分明细" in md
        for label in ["指数 vs 均线", "涨跌家数比", "情绪评分", "最高连板", "成交量趋势"]:
            assert label in md

    def test_playbook_rendered(self):
        md = render_md(_make_result())
        assert "S5" in md and "龙回头" in md
        assert "S4" in md
        assert "strict" in md  # mode 标记

    def test_forbidden_section(self):
        md = render_md(_make_result())
        assert "S1" in md and "S2" in md and "S6" in md

    def test_position_limit_percentage(self):
        md = render_md(_make_result())
        assert "总 50%" in md and "单票 20%" in md

    def test_emergency_marker(self):
        md = render_md(
            _make_result(
                emergency_switch=True,
                emergency_direction="down",
                emergency_reason=["total_drop_5"],
                regime_code="WEAK_RANGE",
                last_regime_code="NEUTRAL_RANGE",
            )
        )
        assert "🚨" in md
        assert "total_drop_5" in md

    def test_switch_warning_shown(self):
        md = render_md(
            _make_result(switch_warning="今日得分 +3 已进入强势震荡区间")
        )
        assert "切换警戒" in md
        assert "强势震荡" in md

    def test_confidence_mark(self):
        md = render_md(_make_result())
        assert "high" in md
        assert "所有 6 维数据完整" in md

    def test_missing_dims_shown(self):
        md = render_md(_make_result(missing_dims=["volume_trend", "streak_height"]))
        assert "volume_trend" in md
        assert "streak_height" in md


# --------------------------------------------------------------------------- #
# render_log_row
# --------------------------------------------------------------------------- #


class TestRenderLogRow:
    def test_basic_row(self):
        row = render_log_row(_make_result(date="2026-04-13"))
        assert row.startswith("| 2026-04-13 |")
        assert "中性震荡" in row
        assert "+3" in row
        assert row.endswith("|")

    def test_switched_cell(self):
        row = render_log_row(
            _make_result(
                switched=True,
                last_regime_code="NEUTRAL_RANGE",
                regime_code="STRONG_RANGE",
            )
        )
        assert "中性震荡→强势震荡" in row

    def test_emergency_cell(self):
        row = render_log_row(
            _make_result(
                emergency_switch=True,
                emergency_direction="down",
                regime_code="WEAK_RANGE",
                last_regime_code="NEUTRAL_RANGE",
            )
        )
        assert "🚨 EMERGENCY_DOWN" in row


# --------------------------------------------------------------------------- #
# append_log + parse_regime_log 循环自洽
# --------------------------------------------------------------------------- #


class TestAppendAndParseLog:
    def test_creates_file_with_header_if_missing(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(_make_result(date="2026-04-01", score_total=2), str(log))
        text = log.read_text(encoding="utf-8")
        assert "# Regime 决策日志" in text
        assert "| 日期 | 6维原始值" in text
        assert "| 2026-04-01 |" in text

    def test_appends_new_row(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(_make_result(date="2026-04-01", score_total=2), str(log))
        append_log(_make_result(date="2026-04-02", score_total=3), str(log))
        text = log.read_text(encoding="utf-8")
        assert "| 2026-04-01 |" in text
        assert "| 2026-04-02 |" in text

    def test_idempotent_same_date_replaces(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(_make_result(date="2026-04-01", score_total=2), str(log))
        append_log(_make_result(date="2026-04-01", score_total=5), str(log))
        text = log.read_text(encoding="utf-8")
        assert text.count("| 2026-04-01 |") == 1
        assert "+5" in text
        assert " +2 " not in text.replace("+2,", "+X,")  # 原得分已被替换

    def test_parse_returns_sorted_entries(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(_make_result(date="2026-04-02", score_total=3), str(log))
        append_log(_make_result(date="2026-04-01", score_total=2), str(log))
        append_log(_make_result(date="2026-04-03", score_total=1), str(log))
        entries = parse_regime_log(str(log))
        assert [e["date"] for e in entries] == [
            "2026-04-01",
            "2026-04-02",
            "2026-04-03",
        ]
        assert [e["total_score"] for e in entries] == [2, 3, 1]

    def test_parse_extracts_regime_code(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(
            _make_result(date="2026-04-01", score_total=3, regime_code="STRONG_RANGE"),
            str(log),
        )
        entries = parse_regime_log(str(log))
        assert entries[0]["regime_code"] == "STRONG_RANGE"

    def test_parse_detects_emergency_switch(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(
            _make_result(
                date="2026-04-01",
                emergency_switch=True,
                emergency_direction="down",
                regime_code="WEAK_RANGE",
                last_regime_code="NEUTRAL_RANGE",
            ),
            str(log),
        )
        entries = parse_regime_log(str(log))
        assert entries[0]["emergency_switch"] is True
        assert entries[0]["switched"] is True

    def test_parse_detects_regular_switch(self, tmp_path):
        log = tmp_path / "regime-log.md"
        append_log(
            _make_result(
                date="2026-04-01",
                switched=True,
                regime_code="STRONG_RANGE",
                last_regime_code="NEUTRAL_RANGE",
            ),
            str(log),
        )
        entries = parse_regime_log(str(log))
        assert entries[0]["switched"] is True
        assert entries[0]["emergency_switch"] is False

    def test_parse_missing_file_returns_empty(self, tmp_path):
        assert parse_regime_log(str(tmp_path / "nope.md")) == []


# --------------------------------------------------------------------------- #
# write_outputs 端到端
# --------------------------------------------------------------------------- #


class TestWriteOutputs:
    def test_writes_three_files(self, tmp_path):
        md_path = tmp_path / "regime_2026-04-13.md"
        json_path = tmp_path / "regime_2026-04-13.json"
        log_path = tmp_path / "memory" / "regime-log.md"
        result = _make_result()
        paths = write_outputs(result, str(md_path), str(json_path), str(log_path))
        assert os.path.exists(paths["md"])
        assert os.path.exists(paths["json"])
        assert os.path.exists(paths["log"])
        # JSON 可解析回来
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["regime_code"] == "NEUTRAL_RANGE"
        assert data["score"]["total"] == 3
        # MD 含中文标题
        assert "市场 Regime 判断" in md_path.read_text(encoding="utf-8")
        # log 有表头
        assert "| 日期 | 6维原始值" in log_path.read_text(encoding="utf-8")

    def test_json_contract_field_names_exact(self, tmp_path):
        # 回归保护: 下游 strategy skill 读的字段名不能动
        json_path = tmp_path / "r.json"
        write_outputs(
            _make_result(),
            str(tmp_path / "m.md"),
            str(json_path),
            str(tmp_path / "log.md"),
        )
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert set(data.keys()) == {
            "date",
            "regime",
            "regime_code",
            "score",
            "raw_data",
            "confidence",
            "missing_dims",
            "switch_warning",
            "playbook",
            "last_regime",
            "switched",
            "emergency_switch",
            "emergency_reason",
        }
        assert set(data["playbook"].keys()) >= {"recommended", "forbidden", "position_limit"}
        assert set(data["playbook"]["position_limit"].keys()) == {"total", "single"}
