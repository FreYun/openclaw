#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import openpyxl

BASE_DIR = Path(__file__).resolve().parent
EASTMONEY_CSV = BASE_DIR / "东财基金.csv"
RULES_MD = BASE_DIR / "基金推荐规则.md"


def _find_latest(pattern: str) -> Path:
    """按文件名倒序找最新的 YYYYMM-xxx.xlsx，找不到则报错。"""
    matches = sorted(BASE_DIR.glob(pattern), reverse=True)
    if not matches:
        raise FileNotFoundError(f"找不到匹配 {pattern} 的文件，请先运行 download_fund_pools.py 下载基金池")
    return matches[0]


INDEX_XLSX = _find_latest("*-指数基金池.xlsx")
EQUITY_XLSX = _find_latest("*-权益基金池.xlsx")

LAYER_PRIORITY = {
    "东财指数": 1,
    "东财权益": 2,
    "其他指数": 3,
    "其他权益": 4,
}
ALLOWED_LAYERS = ("东财指数", "东财权益", "其他指数", "其他权益")

LLM_API_URL = os.environ.get(
    "FUND_SELECTOR_API_URL",
    "https://dd-ai-api.eastmoney.com/v1/chat/completions",
)
LLM_API_KEY = os.environ.get(
    "FUND_SELECTOR_API_KEY",
    "XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69",
)
LLM_MODEL = os.environ.get("FUND_SELECTOR_MODEL", "kimi-k2.5")
LLM_TIMEOUT = float(os.environ.get("FUND_SELECTOR_TIMEOUT", "60"))
MCP_TIMEOUT = float(os.environ.get("FUND_SELECTOR_MCP_TIMEOUT", "30"))
MCP_FIELDS = "FCODE,SHORTNAME,JJJL,SGZT,FTYPE"

BOARD_SYNONYMS = {
    "科技": [
        "科技", "ai", "人工智能", "算力", "芯片", "半导体", "通信", "云计算", "消费电子", "信创", "科创", "机器人",
    ],
    "新能源": [
        "新能源", "光伏", "储能", "锂电", "新能源车", "风电", "绿电", "清洁能源", "电池",
    ],
    "医药": [
        "医药", "创新药", "cxo", "医疗器械", "医疗服务", "中药", "生物医药", "医疗",
    ],
    "消费": [
        "消费", "食品饮料", "白酒", "家电", "大众消费", "消费复苏", "农业", "养殖",
    ],
    "金融": [
        "金融", "券商", "保险", "银行", "非银", "证券", "证券公司",
    ],
    "周期": [
        "周期", "有色", "化工", "煤炭", "钢铁", "资源品", "黄金", "铜", "铝",
    ],
    "制造": [
        "制造", "高端制造", "先进制造", "工业母机", "设备更新", "工业4.0", "机械",
    ],
    "基建地产": [
        "基建", "地产", "建筑", "工程机械", "高铁", "环境治理", "房地产",
    ],
    "全市场": [
        "全市场", "宽基", "红利", "大盘", "a500", "沪深300", "中证500", "北证50", "上证50", "中证1000",
    ],
}


@dataclass
class Candidate:
    candidate_id: str
    code: str
    name: str
    manager: str
    layer: str
    source: str
    board: str | None
    tracking_index: str
    theme: str
    fund_type: str
    purchase_status: str
    pool_tags: list[str]
    match_signals: list[str]
    score: int
    purchase_codes: list[str]
    raw_name: str
    raw_code: str

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "code": self.code,
            "name": self.name,
            "manager": self.manager,
            "layer": self.layer,
            "source": self.source,
            "board": self.board,
            "tracking_index": self.tracking_index,
            "theme": self.theme,
            "fund_type": self.fund_type,
            "purchase_status": self.purchase_status,
            "pool_tags": self.pool_tags,
            "match_signals": self.match_signals,
            "score": self.score,
        }


@dataclass
class FundInfo:
    code: str
    name: str
    manager: str
    purchase_status: str
    fund_type: str


def canonicalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def split_input_topics(value: str) -> list[str]:
    parts = re.split(r"[,，、/；;\n]+", value or "")
    return [part.strip() for part in parts if part.strip()]


def dedupe_key(name: str) -> str:
    text = (name or "").strip()
    text = re.sub(r"(混合|股票|指数增强|指数|联接|发起式|灵活配置|主题|优选|精选|成长|智选|增强)$", "", text)
    text = re.sub(r"[ABCDEFHIORY]类?$", "", text)
    return canonicalize_text(text)


def parse_purchase_codes(value: Any) -> list[str]:
    parts = re.split(r"[,，、/；;\s]+", str(value or "").strip())
    return [part for part in parts if re.fullmatch(r"\d{6}", part)]


def detect_share_suffix(name: str) -> str | None:
    match = re.search(r"([A-Z])(?:类)?$", str(name or "").strip())
    return match.group(1) if match else None


def strip_share_suffix(name: str) -> str:
    return re.sub(r"([A-Z])(?:类)?$", "", str(name or "").strip())


def is_c_share(name: str) -> bool:
    return detect_share_suffix(name) == "C"


def is_a_share(name: str) -> bool:
    return detect_share_suffix(name) == "A"


def is_plain_share(name: str) -> bool:
    return detect_share_suffix(name) is None


def prefers_c_or_plain(candidates: list[FundInfo]) -> FundInfo | None:
    if not candidates:
        return None
    for item in candidates:
        if is_c_share(item.name):
            return item
    for item in candidates:
        if is_plain_share(item.name):
            return item
    return candidates[0]


def purchase_weight(status: str) -> int:
    status = (status or "").strip()
    if status == "开放申购":
        return 3
    if status == "限大额":
        return 2
    return 0


def share_class_weight(name: str) -> int:
    return 2 if is_c_share(name) else 0


def pool_rank_weight(tags: list[str]) -> int:
    normalized_tags = [str(tag or "").strip() for tag in tags]
    if any("核心" in tag for tag in normalized_tags):
        return 20
    if any("优选" in tag for tag in normalized_tags):
        return 10
    return 0


def normalize_board(topic: str) -> tuple[str | None, list[str]]:
    raw = canonicalize_text(topic)
    if not raw:
        return None, []
    if topic in BOARD_SYNONYMS:
        return topic, BOARD_SYNONYMS[topic]

    best_label = None
    best_score = 0
    for label, keywords in BOARD_SYNONYMS.items():
        score = 0
        for keyword in keywords + [label]:
            token = canonicalize_text(keyword)
            if token and token in raw:
                score += max(1, len(token))
        if score > best_score:
            best_label = label
            best_score = score
    if best_label:
        return best_label, BOARD_SYNONYMS[best_label]
    return None, []


def extract_rules_digest() -> str:
    text = RULES_MD.read_text(encoding="utf-8")
    keep_headers = {
        "## 基金来源",
        "## 方向归一",
        "## 选取优先级",
        "### 来源优先级",
        "### 同层筛选规则",
        "### 匹配规则",
        "## 展示格式",
    }
    lines = text.splitlines()
    out: list[str] = []
    keep = False
    for line in lines:
        if line.startswith("#"):
            keep = line.strip() in keep_headers
        if keep:
            out.append(line)
    return "\n".join(out).strip()


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_xlsx_rows(path: Path, sheet_name: str) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    columns = [str(item).strip() if item is not None else "" for item in header]
    result: list[dict[str, Any]] = []
    for row in rows:
        item = {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
        result.append(item)
    return result


def text_fields_for_board(*values: Any) -> str:
    return " ".join(str(v).strip() for v in values if str(v or "").strip())


def infer_board_from_text(*values: Any) -> tuple[str | None, list[str]]:
    merged = canonicalize_text(text_fields_for_board(*values))
    if not merged:
        return None, []
    best_label = None
    best_keywords: list[str] = []
    best_score = 0
    for label, keywords in BOARD_SYNONYMS.items():
        score = 0
        for keyword in [label] + keywords:
            token = canonicalize_text(keyword)
            if token and token in merged:
                score += max(1, len(token))
        if score > best_score:
            best_label = label
            best_keywords = keywords
            best_score = score
    return best_label, best_keywords


def topic_match_tokens(topic: str) -> list[str]:
    raw_text = str(topic or "").strip()
    if not raw_text:
        return []

    stripped = raw_text
    for suffix in ("板块", "赛道", "方向", "主题", "行业", "概念"):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
            break

    tokens: list[str] = []
    for value in (raw_text, stripped):
        token = canonicalize_text(value)
        if token and token not in tokens:
            tokens.append(token)

    canonical_stripped = canonicalize_text(stripped)
    for label, keywords in BOARD_SYNONYMS.items():
        for kw in [label] + keywords:
            kw_token = canonicalize_text(kw)
            if kw_token and len(kw_token) >= 2 and kw_token in canonical_stripped and kw_token != canonical_stripped:
                if kw_token not in tokens:
                    tokens.append(kw_token)

    return tokens


def build_match_signals(topic: str, candidate: Candidate, normalized_board: str | None = None, board_tokens: list[str] | None = None) -> list[str]:
    tokens = topic_match_tokens(topic)
    if board_tokens:
        tokens = tokens + [t for t in board_tokens if t not in tokens]
    signals: list[str] = []
    tracking_index_text = canonicalize_text(candidate.tracking_index)
    name_text = canonicalize_text(candidate.name)
    theme_text = canonicalize_text(candidate.theme)

    if candidate.tracking_index and any(token in tracking_index_text for token in tokens):
        signals.append("tracking_index:direct")
    if any(token in name_text for token in tokens):
        signals.append("name:direct")
    if any(token in theme_text for token in tokens):
        signals.append("theme:direct")
    if not signals and normalized_board and candidate.board == normalized_board:
        signals.append("board:match")
    return signals


def score_candidate(topic: str, candidate: Candidate, normalized_board: str | None = None, board_tokens: list[str] | None = None) -> int:
    score = 1000 - LAYER_PRIORITY[candidate.layer] * 100
    signals = build_match_signals(topic, candidate, normalized_board, board_tokens)
    candidate.match_signals = signals
    if any(s.startswith("tracking_index") for s in signals):
        score += 90
    if any(s.startswith("name") for s in signals):
        score += 60
    if any(s.startswith("theme") for s in signals):
        score += 30
    if any(s == "board:match" for s in signals):
        score += 10
    score += purchase_weight(candidate.purchase_status)
    score += share_class_weight(candidate.name)
    score += pool_rank_weight(candidate.pool_tags)
    return score


def map_eastmoney_rows(rows: list[dict[str, Any]]) -> list[Candidate]:
    result: list[Candidate] = []
    for row in rows:
        name = str(row.get("SHORTNAME") or "").strip()
        if not name or "ETF" in name.upper():
            continue
        fund_type = str(row.get("FTYPE") or "").strip()
        layer = "东财指数" if fund_type.startswith("指数型") else "东财权益"
        board, _ = infer_board_from_text(row.get("LABEL_NAME_122"), name)
        code = str(row.get("FCODE") or "").strip()
        result.append(
            Candidate(
                candidate_id=f"eastmoney:{code}",
                code=code,
                name=name,
                manager=str(row.get("JJJL") or "").strip(),
                layer=layer,
                source="东财基金.csv",
                board=board,
                tracking_index="",
                theme=str(row.get("LABEL_NAME_122") or "").strip(),
                fund_type=fund_type,
                purchase_status=str(row.get("SGZT") or "").strip(),
                pool_tags=[],
                match_signals=[],
                score=0,
                purchase_codes=[],
                raw_name=name,
                raw_code=code,
            )
        )
    return result


def map_index_rows(rows: list[dict[str, Any]]) -> list[Candidate]:
    result: list[Candidate] = []
    for row in rows:
        name = str(row.get("基金简称") or "").strip()
        if not name:
            continue
        code = str(row.get("基金代码") or "").strip()
        pool_tag = str(row.get("入池情况") or "").strip()
        board, _ = infer_board_from_text(row.get("指数名称"), row.get("主题(近一年)"), row.get("风格(近一年)"), row.get("市值(近一年)"), name)
        result.append(
            Candidate(
                candidate_id=f"index_pool:{code}",
                code=code,
                name=name,
                manager=str(row.get("基金经理") or "").strip(),
                layer="其他指数",
                source=INDEX_XLSX.name,
                board=board,
                tracking_index=str(row.get("指数名称") or "").strip(),
                theme=str(row.get("主题(近一年)") or "").strip(),
                fund_type=str(row.get("基金分类") or "").strip(),
                purchase_status="开放申购",
                pool_tags=[pool_tag] if pool_tag else [],
                match_signals=[],
                score=0,
                purchase_codes=parse_purchase_codes(row.get("可购买代码")),
                raw_name=name,
                raw_code=code,
            )
        )
    return result


def map_equity_rows(rows: list[dict[str, Any]]) -> list[Candidate]:
    result: list[Candidate] = []
    for row in rows:
        name = str(row.get("基金简称") or "").strip()
        if not name:
            continue
        code = str(row.get("基金代码") or "").strip()
        tags = [str(row.get(key) or "").strip() for key in ("主题池", "市值池", "风格池") if str(row.get(key) or "").strip()]
        board, _ = infer_board_from_text(row.get("主题(最新)"), row.get("主题(近一年)"), row.get("风格(最新)"), row.get("风格(近一年)"), name)
        result.append(
            Candidate(
                candidate_id=f"equity_pool:{code}",
                code=code,
                name=name,
                manager=str(row.get("基金经理") or "").strip(),
                layer="其他权益",
                source=EQUITY_XLSX.name,
                board=board,
                tracking_index="",
                theme=text_fields_for_board(row.get("主题(最新)"), row.get("主题(近一年)")),
                fund_type="权益型",
                purchase_status=str(row.get("申购状态") or "").strip(),
                pool_tags=tags,
                match_signals=[],
                score=0,
                purchase_codes=[],
                raw_name=name,
                raw_code=code,
            )
        )
    return result


def load_all_candidates() -> list[Candidate]:
    eastmoney = map_eastmoney_rows(load_csv_rows(EASTMONEY_CSV))
    index_pool = map_index_rows(load_xlsx_rows(INDEX_XLSX, "全部基金"))
    equity_pool = map_equity_rows(load_xlsx_rows(EQUITY_XLSX, "全部基金"))
    return eastmoney + index_pool + equity_pool


def candidate_relevant(topic: str, normalized_board: str | None, candidate: Candidate, board_tokens: list[str] | None = None) -> bool:
    tokens = topic_match_tokens(topic)
    if board_tokens:
        tokens = tokens + [t for t in board_tokens if t not in tokens]
    if not tokens:
        return False
    haystack = canonicalize_text(" ".join([
        candidate.name,
        candidate.tracking_index,
        candidate.theme,
        candidate.fund_type,
        " ".join(candidate.pool_tags),
        candidate.board or "",
    ]))
    if any(token in haystack for token in tokens):
        return True
    if board_tokens and normalized_board and candidate.board == normalized_board:
        return True
    return False


def _filter_group_dedup(
    topic: str,
    normalized_board: str | None,
    all_candidates: list[Candidate],
    per_layer_limit: int,
    board_tokens: list[str] | None = None,
) -> dict[str, list[Candidate]]:
    grouped: dict[str, list[Candidate]] = {layer: [] for layer in ALLOWED_LAYERS}
    for candidate in all_candidates:
        if not candidate_relevant(topic, normalized_board, candidate, board_tokens=board_tokens):
            continue
        candidate.score = score_candidate(topic, candidate, normalized_board, board_tokens=board_tokens)
        grouped[candidate.layer].append(candidate)

    for layer in ALLOWED_LAYERS:
        seen_codes: set[str] = set()
        seen_names: set[str] = set()
        ranked = sorted(grouped[layer], key=lambda item: (-item.score, item.code, item.name))
        deduped: list[Candidate] = []
        for item in ranked:
            base = dedupe_key(item.name)
            if item.code in seen_codes or base in seen_names:
                continue
            seen_codes.add(item.code)
            seen_names.add(base)
            deduped.append(item)
            if len(deduped) >= per_layer_limit:
                break
        grouped[layer] = deduped
    return grouped


def shortlist_for_topic(topic: str, all_candidates: list[Candidate], per_layer_limit: int = 8) -> dict[str, list[Candidate]]:
    normalized_board, board_keywords = normalize_board(topic)

    # Round 1: enhanced token match (with compound word decomposition)
    grouped = _filter_group_dedup(topic, normalized_board, all_candidates, per_layer_limit)
    total = sum(len(v) for v in grouped.values())

    if total < 2 and normalized_board and board_keywords:
        # Round 2: expand with board synonym keywords for broader matching
        extra = [canonicalize_text(kw) for kw in board_keywords if canonicalize_text(kw)]
        grouped = _filter_group_dedup(topic, normalized_board, all_candidates, per_layer_limit, board_tokens=extra)

    return grouped


def is_strong_match(candidate: Candidate) -> bool:
    return any(
        signal in candidate.match_signals
        for signal in ("tracking_index:direct", "name:direct", "theme:direct", "board:match")
    )


def pick_layer_candidates(grouped: dict[str, list[Candidate]], limit: int) -> tuple[list[Candidate], list[str]]:
    chosen: list[Candidate] = []
    used_codes: set[str] = set()
    used_names: set[str] = set()
    layers_used: list[str] = []

    for layer in ALLOWED_LAYERS:
        layer_items = grouped.get(layer, [])
        if not layer_items:
            continue

        if layer in {"东财指数", "东财权益"}:
            eligible = layer_items
        else:
            strong = [item for item in layer_items if is_strong_match(item)]
            eligible = strong or layer_items

        remaining = limit - len(chosen)
        if remaining <= 0:
            return chosen, layers_used

        available: list[Candidate] = []
        for item in eligible:
            base = dedupe_key(item.name)
            if item.code in used_codes or base in used_names:
                continue
            available.append(item)

        if not available:
            continue

        take_count = min(remaining, len(available))
        selected_batch = available[:take_count]
        for item in selected_batch:
            base = dedupe_key(item.name)
            chosen.append(item)
            used_codes.add(item.code)
            used_names.add(base)
        if layer not in layers_used:
            layers_used.append(layer)

        if take_count >= remaining:
            return chosen, layers_used

    return chosen, layers_used


def extract_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


def extract_json_block(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end >= start:
        return stripped[start:end + 1]
    return stripped


def fetch_fund_basicinfo_by_codes(codes: list[str]) -> tuple[dict[str, FundInfo], str | None]:
    valid_codes = []
    seen: set[str] = set()
    for code in codes:
        if re.fullmatch(r"\d{6}", str(code or "").strip()) and code not in seen:
            seen.add(code)
            valid_codes.append(code)
    if not valid_codes:
        return {}, None

    command = (
        "npx mcporter call "
        f'"research-mcp.fund_basicinfo(fcodes: \'{",".join(valid_codes)}\', fields: \'{MCP_FIELDS}\')"'
    )
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=None,  # inherit caller's cwd (bot workspace) so mcporter finds config/mcporter.json
            timeout=MCP_TIMEOUT,
        )
    except Exception as exc:
        return {}, str(exc)

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}, "research-mcp 返回空输出"

    try:
        payload = json.loads(extract_json_block(stdout))
    except Exception as exc:
        return {}, f"research-mcp 返回解析失败: {exc}; raw={stdout[:300]}"

    content = payload.get("content") if isinstance(payload, dict) else None
    text = ""
    rows = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text") or "").strip()
                if text:
                    break
    elif isinstance(payload, dict):
        text = str(payload.get("text") or "").strip()
        for key in ("data", "result", "rows", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
    if text:
        try:
            parsed = json.loads(extract_json_block(text))
        except Exception as exc:
            return {}, f"research-mcp text 解析失败: {exc}; raw={text[:300]}"

        if isinstance(parsed, list):
            rows = parsed
        elif isinstance(parsed, dict):
            for key in ("data", "result", "rows", "list"):
                value = parsed.get(key)
                if isinstance(value, list):
                    rows = value
                    break
            if not rows and all(k in parsed for k in ("FCODE", "SHORTNAME")):
                rows = [parsed]
    elif not rows:
        return {}, f"research-mcp 未返回可解析内容: {json.dumps(payload, ensure_ascii=False)[:300]}"

    fund_map: dict[str, FundInfo] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("FCODE") or row.get("fcode") or "").strip()
        if not code:
            continue
        fund_map[code] = FundInfo(
            code=code,
            name=str(row.get("SHORTNAME") or row.get("shortname") or "").strip(),
            manager=str(row.get("JJJL") or row.get("jjjl") or "").strip(),
            purchase_status=str(row.get("SGZT") or row.get("sgzt") or "").strip(),
            fund_type=str(row.get("FTYPE") or row.get("ftype") or "").strip(),
        )
    return fund_map, None


def collect_sibling_candidates(selected_fund: dict[str, Any], original_candidate: Candidate, fetched_map: dict[str, FundInfo]) -> list[FundInfo]:
    siblings: list[FundInfo] = []
    base_name = strip_share_suffix(selected_fund["name"])
    for info in fetched_map.values():
        if strip_share_suffix(info.name) == base_name:
            siblings.append(info)
    if siblings:
        return siblings
    if original_candidate.purchase_codes:
        return [fetched_map[code] for code in original_candidate.purchase_codes if code in fetched_map]
    current = fetched_map.get(selected_fund["code"])
    return [current] if current else []


def normalize_selected_funds(selected_funds: list[dict[str, Any]], candidate_pool: list[Candidate]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_map = {candidate.candidate_id: candidate for candidate in candidate_pool}
    normalized: list[dict[str, Any]] = []
    debug_entries: list[dict[str, Any]] = []

    for fund in selected_funds:
        original_candidate = candidate_map.get(str(fund.get("candidate_id") or ""))
        current = dict(fund)
        debug_entry = {
            "candidate_id": current.get("candidate_id"),
            "original_name": current.get("name"),
            "original_code": current.get("code"),
            "purchase_codes": list(original_candidate.purchase_codes) if original_candidate else [],
            "normalized": False,
            "reason": None,
            "mcp_error": None,
        }
        fetched_map: dict[str, FundInfo] = {}

        if original_candidate and original_candidate.purchase_codes and "ETF" in original_candidate.name.upper():
            fetched_map, error = fetch_fund_basicinfo_by_codes(original_candidate.purchase_codes)
            debug_entry["mcp_error"] = error
            preferred = prefers_c_or_plain([fetched_map[code] for code in original_candidate.purchase_codes if code in fetched_map])
            if preferred:
                current["code"] = preferred.code
                current["name"] = preferred.name or current["name"]
                current["manager"] = preferred.manager or current["manager"]
                debug_entry["normalized"] = preferred.code != fund.get("code") or preferred.name != fund.get("name")
                debug_entry["reason"] = "etf_purchase_to_c_or_plain"
            else:
                debug_entry["reason"] = "etf_normalization_failed"
                debug_entry["needs_manual_resolution"] = True

        if is_a_share(current.get("name", "")):
            sibling_map = fetched_map
            if not sibling_map:
                lookup_codes = list(dict.fromkeys(original_candidate.purchase_codes if original_candidate and original_candidate.purchase_codes else [current["code"]]))
                sibling_map, error = fetch_fund_basicinfo_by_codes(lookup_codes)
                debug_entry["mcp_error"] = debug_entry["mcp_error"] or error
            siblings = collect_sibling_candidates(current, original_candidate, sibling_map) if original_candidate else []
            preferred_c = next((item for item in siblings if is_c_share(item.name)), None)
            if preferred_c:
                current["code"] = preferred_c.code
                current["name"] = preferred_c.name or current["name"]
                current["manager"] = preferred_c.manager or current["manager"]
                debug_entry["normalized"] = True
                debug_entry["reason"] = "a_to_c"
            else:
                debug_entry["reason"] = "a_to_c_normalization_failed"
                debug_entry["needs_manual_resolution"] = True

        debug_entry["final_name"] = current.get("name")
        debug_entry["final_code"] = current.get("code")
        normalized.append(current)
        debug_entries.append(debug_entry)

    return normalized, debug_entries


def call_llm(topic: str, normalized_board: str | None, allowed_layers: list[str], candidates: list[Candidate], limit: int) -> dict[str, Any]:
    if not LLM_API_KEY:
        raise RuntimeError("缺少 FUND_SELECTOR_API_KEY 或 GLM_API_KEY")

    rules_digest = extract_rules_digest()
    payload = {
        "topic": topic,
        "normalized_board": normalized_board,
        "allowed_layers_in_priority_order": allowed_layers,
        "limit": limit,
        "rules_digest": rules_digest,
        "selection_requirements": [
            "你要灵活理解用户传入的主题/板块，不要只做字面匹配。",
            "但你只能从提供的候选集中选择基金。",
            "来源优先级固定：东财指数 > 东财权益 > 其他指数 > 其他权益。",
            "同一层内要先按基金池优先级选择：带‘核心’字样 > 带‘优选’字样 > 其他/全部基金。",
            "如果高优先级层有相关基金，应先保留高优先级层的相关基金，再往低优先级层补足到 3只。",
            "一旦某个后续层已经足够补满剩余名额，就在这一层补满，不要继续深入更低层。",
            "其他指数和其他权益要更看重细分主题命中，优先顺序：跟踪指数 > 基金名称 > 主题。",
            "允许混合多层返回，但必须符合优先级补位逻辑，不能跳过更高优先级层里已相关的基金。",
            "返回数量只能是 0 或 3，绝不能返回 1。",
        ],
        "candidates": [c.to_prompt_dict() for c in candidates],
        "output_schema": {
            "topic": "string",
            "normalized_board": "string|null",
            "selected_layers": ["string"],
            "selected_funds": [
                {"candidate_id": "string", "reason": "string"}
            ],
            "selection_reason": "string"
        },
    }
    system_prompt = (
        "你是基金筛选助手。你的任务是根据用户传入的板块/主题，灵活理解语义并从候选基金里筛选结果。"
        "你可以做语义匹配，但不能编造基金，不能跳出候选集。"
        "本次允许按优先级跨层补位：高优先级层先选，再用低优先级层补足。"
        "禁止输出思考过程。禁止输出解释性正文。只返回一个合法 JSON 对象。"
    )
    request_body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 1,
        "max_tokens": 1500,
    }
    request = urllib.request.Request(
        LLM_API_URL,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=LLM_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"模型接口 HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"模型接口调用失败: {exc}") from exc

    choice = body.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = (
        extract_content_text(message.get("content"))
        or extract_content_text(choice.get("text"))
        or extract_content_text(body.get("output_text"))
    )
    if not content and isinstance(message, dict):
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip().startswith("{"):
            content = reasoning.strip()
    if not content:
        raise RuntimeError(f"模型未返回可解析内容，原始响应: {json.dumps(body, ensure_ascii=False)}")
    return json.loads(extract_json_block(content))


def validate_llm_result(result: dict[str, Any], allowed_layers: list[str], candidates: list[Candidate], limit: int) -> dict[str, Any]:
    selected = result.get("selected_funds")
    if not isinstance(selected, list):
        raise RuntimeError("模型返回缺少 selected_funds")

    candidate_map = {c.candidate_id: c for c in candidates}
    validated: list[dict[str, Any]] = []
    used_codes: set[str] = set()
    used_names: set[str] = set()

    for item in selected:
        candidate_id = str((item or {}).get("candidate_id") or "").strip()
        if candidate_id not in candidate_map:
            raise RuntimeError(f"模型选择了候选外基金: {candidate_id}")
        candidate = candidate_map[candidate_id]
        if candidate.layer not in allowed_layers:
            raise RuntimeError("模型返回了非法层级基金")
        base = dedupe_key(candidate.name)
        if candidate.code in used_codes or base in used_names:
            raise RuntimeError(f"模型返回了重复产品线: {candidate.name}")
        used_codes.add(candidate.code)
        used_names.add(base)
        validated.append({
            "candidate_id": candidate.candidate_id,
            "code": candidate.code,
            "name": candidate.name,
            "manager": candidate.manager,
            "layer": candidate.layer,
            "reason": str((item or {}).get("reason") or "").strip(),
        })

    if len(validated) not in {0, 2, 3}:
        raise RuntimeError(f"模型返回数量非法: {len(validated)}，只允许 0/2/3")
    if len(validated) > limit:
        raise RuntimeError(f"模型返回数量超限: {len(validated)} > {limit}")

    selected_layers = result.get("selected_layers") or []
    actual_layers = []
    for fund in validated:
        if fund["layer"] not in actual_layers:
            actual_layers.append(fund["layer"])
    if selected_layers and selected_layers != actual_layers:
        raise RuntimeError("selected_layers 与实际返回层级不一致")

    return {
        "topic": str(result.get("topic") or "").strip(),
        "normalized_board": result.get("normalized_board"),
        "selected_layers": actual_layers,
        "selected_layer": actual_layers[0] if len(actual_layers) == 1 else None,
        "selected_funds": validated,
        "selection_reason": str(result.get("selection_reason") or "").strip(),
    }


def format_fund_display(fund: dict[str, Any]) -> str:
    return f"{fund['name']}（{fund['code']}，基金经理：{fund['manager']}）"


def select_for_topic(topic: str, all_candidates: list[Candidate], limit: int, debug: bool) -> dict[str, Any]:
    normalized_board, _ = normalize_board(topic)
    grouped = shortlist_for_topic(topic, all_candidates)
    pool_size = max(limit * 3, 9)
    candidate_pool, layers_used = pick_layer_candidates(grouped, pool_size)
    if len(candidate_pool) < 2:
        return {
            "topic": topic,
            "normalized_board": normalized_board,
            "selected_layers": [],
            "selected_layer": None,
            "selected_funds": [],
            "selection_reason": "按优先级补位后仍不足2只候选，不返回基金",
            "display": "",
            "debug": {
                layer: [c.to_prompt_dict() for c in items] for layer, items in grouped.items()
            } if debug else None,
        }

    llm_result = call_llm(topic, normalized_board, layers_used, candidate_pool, limit)
    validated = validate_llm_result(llm_result, layers_used, candidate_pool, limit)
    normalized_funds, normalization_debug = normalize_selected_funds(validated["selected_funds"], candidate_pool)
    validated["selected_funds"] = normalized_funds

    # Collect warnings for funds that couldn't be normalized (ETF/A-share with MCP failure)
    warnings: list[str] = []
    for entry in normalization_debug:
        if entry.get("needs_manual_resolution"):
            original = f"{entry['original_name']}（{entry['original_code']}）"
            codes = entry.get("purchase_codes", [])
            mcp_err = entry.get("mcp_error") or "unknown"
            warnings.append(
                f"⚠️ {original} 是ETF/A份额，需要转换为可购买的C份额联接基金，"
                f"但 research-mcp 查询失败（{mcp_err}）。"
                f"可购买代码：{','.join(codes) if codes else '无'}。"
                f"请手动确认正确的C份额代码和名称后替换。"
            )
    validated["warnings"] = warnings

    display = "、".join(format_fund_display(fund) for fund in validated["selected_funds"])
    validated["display"] = f"{topic}：{display}" if display else ""
    if debug:
        validated["debug"] = {
            "layers_used": layers_used,
            "candidate_pool": [c.to_prompt_dict() for c in candidate_pool],
            "all_grouped": {layer: [c.to_prompt_dict() for c in items] for layer, items in grouped.items()},
            "llm_raw": llm_result,
            "normalization": normalization_debug,
        }
    return validated


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 基金筛选脚本")
    parser.add_argument("--topic", help="单个板块/主题，例如 科技 或 算力")
    parser.add_argument("--topics", help="多个板块/主题，逗号分隔，例如 科技,新能源,医药")
    parser.add_argument("--limit", type=int, default=3, help="每个主题最多返回几只，默认 3")
    parser.add_argument("--debug", action="store_true", help="输出调试信息")
    args = parser.parse_args()

    topics = []
    if args.topic:
        topics.extend(split_input_topics(args.topic))
    if args.topics:
        topics.extend(split_input_topics(args.topics))
    if not topics:
        print("请传 --topic 或 --topics", file=sys.stderr)
        return 2

    limit = max(2, min(int(args.limit), 3))
    all_candidates = load_all_candidates()
    results = [select_for_topic(topic, all_candidates, limit, args.debug) for topic in topics]
    all_warnings: list[str] = []
    for item in results:
        all_warnings.extend(item.get("warnings", []))
    payload = {
        "topics": topics,
        "results": results,
        "display_lines": [item["display"] for item in results if item.get("display")],
        "warnings": all_warnings,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
