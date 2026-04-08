#!/usr/bin/env python3
"""
bot9 fund-selector MCP server

模型主判版本：
- 只服务 bot9，不接入全局 MCP
- 只读取本地两个底库 CSV
- 代码只负责候选召回、边界过滤、结果校验
- 最终筛选由大模型依据基金推荐规则.md 决策
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import csv
import json
import os
import re
import time
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SERVER_NAME = "fund-selector"
SERVER_VERSION = "2.0.0"
WORKSPACE_ROOT = Path("/home/rooot/.openclaw/workspace-bot9")
SKILL_DIR = WORKSPACE_ROOT / "skills" / "daily-market-recap"
EASTMONEY_CSV = SKILL_DIR / "东财基金.csv"
POOL_CSV = SKILL_DIR / "基金池.csv"
RULES_MD = SKILL_DIR / "基金推荐规则.md"

LAYER_PRIORITY = {
    "东财指数": 1,
    "东财权益": 2,
    "其他指数": 3,
    "其他权益": 4,
}

ALLOWED_LAYERS = ("东财指数", "东财权益", "其他指数", "其他权益")
DEFAULT_LIMIT = 3
MIN_LIMIT = 2
MAX_LIMIT = 5
SHORTLIST_PER_LAYER = 5

LLM_API_URL = os.environ.get(
    "FUND_SELECTOR_API_URL",
    "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions",
)
LLM_API_KEY = os.environ.get("FUND_SELECTOR_API_KEY") or os.environ.get("GLM_API_KEY", "")
LLM_MODEL = os.environ.get("FUND_SELECTOR_MODEL", "glm-5-turbo")
LLM_TIMEOUT = float(os.environ.get("FUND_SELECTOR_TIMEOUT", "45"))
LLM_MAX_RETRIES = max(1, int(os.environ.get("FUND_SELECTOR_RETRIES", "2")))

SYNONYMS = {
    "科技": [
        "科技", "ai", "人工智能", "算力", "芯片", "半导体", "通信", "云计算",
        "消费电子", "信创", "科创", "数字经济", "机器人",
    ],
    "新能源": [
        "新能源", "光伏", "储能", "锂电", "新能源车", "风电", "有色", "绿电",
        "电池", "低碳", "清洁能源",
    ],
    "医药": [
        "医药", "创新药", "cxo", "医疗器械", "医疗服务", "中药", "大健康",
        "养老",
    ],
    "消费": [
        "消费", "食品饮料", "白酒", "家电", "大众消费", "消费复苏", "农业",
        "养殖",
    ],
    "金融": [
        "金融", "券商", "保险", "银行", "非银",
    ],
    "周期": [
        "周期", "有色", "化工", "煤炭", "钢铁", "资源品", "黄金", "铜", "铝",
    ],
    "制造": [
        "制造", "高端制造", "先进制造", "工业母机", "设备更新", "机器人",
        "工业4.0",
    ],
    "基建地产": [
        "基建", "地产", "建筑", "工程机械", "高铁", "环境治理", "房地产",
    ],
    "全市场": [
        "全市场", "宽基", "红利", "大盘", "a500", "沪深300", "中证500",
        "北证50", "上证50",
    ],
}


def canonicalize_text(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().lower())


def split_directions(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"[,\n，、/；;]+", text)
    return [part.strip() for part in parts if part.strip()]


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def split_article_context(value: Any, directions: list[str]) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v).strip() for k, v in value.items() if str(v).strip()}
    if not value:
        return {}
    text = str(value).strip()
    if not text:
        return {}
    return {direction: text for direction in directions}


def normalize_direction(direction: str) -> tuple[str | None, list[str]]:
    raw = canonicalize_text(direction)
    if not raw:
        return None, []

    if direction in SYNONYMS:
        return direction, SYNONYMS[direction]

    scores: list[tuple[int, str]] = []
    for label, keywords in SYNONYMS.items():
        score = 0
        for keyword in keywords:
            token = canonicalize_text(keyword)
            if token and token in raw:
                score += max(len(token), 1)
        if score > 0:
            scores.append((score, label))

    if not scores:
        return None, []

    scores.sort(key=lambda item: (-item[0], item[1]))
    label = scores[0][1]
    return label, SYNONYMS[label]


def purchase_weight(status: str) -> int:
    status = (status or "").strip()
    if status == "开放申购":
        return 3
    if status == "限大额":
        return 2
    return 1


def share_class_weight(name: str) -> int:
    return 2 if "C" in (name or "") else 0


def pool_rank_weight(fund_type: str) -> int:
    text = fund_type or ""
    if "核心" in text:
        return 2
    if "优选" in text:
        return 1
    return 0


def name_match_score(name: str, original_direction: str, keywords: list[str]) -> int:
    text = canonicalize_text(name)
    raw = canonicalize_text(original_direction)
    if raw and raw in text:
        return 30
    best = 0
    for keyword in keywords:
        token = canonicalize_text(keyword)
        if token and token in text:
            best = max(best, min(len(token), 20))
    if best:
        return 20 + best
    return 10


def dedupe_key(name: str) -> str:
    text = (name or "").strip()
    text = re.sub(r"(混合|股票|指数增强|指数|联接|发起式|灵活配置|主题|优选|精选|成长|智选|增强)$", "", text)
    text = re.sub(r"[ABCDEFHIORY]类?$", "", text)
    return canonicalize_text(text)


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


def extract_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value.strip())
                continue
            if isinstance(text_value, dict):
                nested = text_value.get("value")
                if isinstance(nested, str) and nested.strip():
                    parts.append(nested.strip())
                    continue
            if item.get("type") == "output_text":
                nested = item.get("text")
                if isinstance(nested, str) and nested.strip():
                    parts.append(nested.strip())
        return "\n".join(parts).strip()
    return ""


def extract_rules_digest(markdown_text: str) -> str:
    selected_headers = {
        "## 触发条件（默认必须带）",
        "## 基金来源",
        "## 方向归一",
        "## 选取优先级",
        "### 来源优先级",
        "### 接口执行顺序",
        "### 同层筛选规则",
        "### 匹配规则",
        "### bot 的实际执行步骤",
        "## 仅以下情况可以不带基金",
    }
    lines = markdown_text.splitlines()
    output: list[str] = []
    keep = False
    for line in lines:
        if line.startswith("---"):
            continue
        if line.startswith("#"):
            keep = line.strip() in selected_headers
        if keep:
            output.append(line)
    return "\n".join(output).strip()


@dataclass
class Candidate:
    candidate_id: str
    code: str
    name: str
    manager: str
    layer: str
    fund_type: str
    label: str
    purchase_status: str
    retrieval_score: int
    source_file: str

    def as_dict(self, include_debug: bool = False) -> dict[str, Any]:
        payload = {
            "candidate_id": self.candidate_id,
            "code": self.code,
            "name": self.name,
            "manager": self.manager,
            "layer": self.layer,
            "fund_type": self.fund_type,
            "label": self.label,
            "purchase_status": self.purchase_status,
            "source_file": self.source_file,
        }
        if include_debug:
            payload["retrieval_score"] = self.retrieval_score
        return payload


class LlmDecisionError(Exception):
    pass


class FundSelector:
    def __init__(self) -> None:
        self.eastmoney_rows = self._load_rows(EASTMONEY_CSV)
        self.pool_rows = self._load_rows(POOL_CSV)
        self.rules_text = RULES_MD.read_text(encoding="utf-8")
        self.rules_digest = extract_rules_digest(self.rules_text)

    def _load_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _iter_candidates(self, normalized_direction: str, original_direction: str, keywords: list[str]) -> list[Candidate]:
        results: list[Candidate] = []

        for row in self.eastmoney_rows:
            row_label = (row.get("LABEL_NAME_122") or "").strip()
            name = (row.get("SHORTNAME") or "").strip()
            if row_label != normalized_direction:
                continue
            if not name or "ETF" in name.upper():
                continue

            fund_type = (row.get("FTYPE") or "").strip()
            layer = "东财指数" if fund_type.startswith("指数型") else "东财权益"
            score = (
                1000
                - LAYER_PRIORITY[layer] * 100
                + name_match_score(name, original_direction, keywords)
                + purchase_weight(row.get("SGZT") or "")
                + share_class_weight(name)
            )
            results.append(
                Candidate(
                    candidate_id=f"eastmoney:{row.get('FCODE','').strip()}",
                    code=(row.get("FCODE") or "").strip(),
                    name=name,
                    manager=(row.get("JJJL") or "").strip(),
                    layer=layer,
                    fund_type=fund_type,
                    label=row_label,
                    purchase_status=(row.get("SGZT") or "").strip(),
                    retrieval_score=score,
                    source_file="东财基金.csv",
                )
            )

        for row in self.pool_rows:
            row_label = (row.get("LABEL_NAME_122") or "").strip()
            name = (row.get("SHORTNAME") or "").strip()
            if row_label != normalized_direction:
                continue
            if not name or "ETF" in name.upper():
                continue

            fund_type = (row.get("ENUM_LABEL_NAME") or "").strip()
            layer = "其他指数" if fund_type.startswith("指数型") else "其他权益"
            score = (
                1000
                - LAYER_PRIORITY[layer] * 100
                + name_match_score(name, original_direction, keywords)
                + purchase_weight(row.get("SGZT") or "")
                + share_class_weight(name)
                + pool_rank_weight(fund_type)
            )
            results.append(
                Candidate(
                    candidate_id=f"pool:{row.get('FUND_CODE','').strip()}",
                    code=(row.get("FUND_CODE") or "").strip(),
                    name=name,
                    manager=(row.get("JJJL") or "").strip(),
                    layer=layer,
                    fund_type=fund_type,
                    label=row_label,
                    purchase_status=(row.get("SGZT") or "").strip(),
                    retrieval_score=score,
                    source_file="基金池.csv",
                )
            )

        return results

    def _build_shortlist(self, direction: str, include_debug: bool = False) -> dict[str, Any]:
        normalized, keywords = normalize_direction(direction)
        if not normalized:
            return {
                "input_direction": direction,
                "normalized_direction_hint": None,
                "keywords_hint": [],
                "candidate_groups": {},
                "candidate_count": 0,
                "warnings": ["未能归一到标准方向，候选召回可能偏弱"],
            }

        grouped: dict[str, list[Candidate]] = {layer: [] for layer in ALLOWED_LAYERS}
        for item in self._iter_candidates(normalized, direction, keywords):
            grouped[item.layer].append(item)

        shortlist_groups: dict[str, list[dict[str, Any]]] = {}
        candidate_count = 0
        for layer in ALLOWED_LAYERS:
            items = grouped[layer]
            items.sort(key=lambda item: (-item.retrieval_score, item.code, item.name))
            deduped: list[Candidate] = []
            seen_codes: set[str] = set()
            seen_names: set[str] = set()
            for item in items:
                if item.code in seen_codes or dedupe_key(item.name) in seen_names:
                    continue
                seen_codes.add(item.code)
                seen_names.add(dedupe_key(item.name))
                deduped.append(item)
                if len(deduped) >= SHORTLIST_PER_LAYER:
                    break
            shortlist_groups[layer] = [candidate.as_dict(include_debug=include_debug) for candidate in deduped]
            candidate_count += len(deduped)

        return {
            "input_direction": direction,
            "normalized_direction_hint": normalized,
            "keywords_hint": keywords,
            "candidate_groups": shortlist_groups,
            "candidate_count": candidate_count,
            "warnings": [],
        }

    def _call_llm_for_direction(
        self,
        direction: str,
        shortlist: dict[str, Any],
        article_context: str,
        limit: int,
        strict_priority: bool,
    ) -> dict[str, Any]:
        if not LLM_API_KEY:
            raise LlmDecisionError("缺少模型 API Key：未找到 FUND_SELECTOR_API_KEY 或 GLM_API_KEY")

        system_prompt = (
            "你是 bot9 的基金筛选决策模型。"
            "你只能从给定候选中选择基金，不允许编造、扩写、替换候选外的基金。"
            "你的任务不是海选，而是在候选集内，根据规则做最终筛选。"
            "必须严格遵守用户提供的 markdown 规则，尤其是来源优先级、不要硬塞、不要跨方向硬配、优先 C 类。"
            "如果高优先级层已经有足够合适基金，不要降级到低优先级层。"
            "若确实没有足够合适候选，可以返回空列表，但要说明原因。"
            "输出必须是 JSON，不要加解释。"
        )

        user_prompt = json.dumps(
            {
                "task": "请根据规则从候选集中为一个方向筛选基金",
                "rules_markdown_digest": self.rules_digest,
                "current_direction": direction,
                "article_context": article_context or "",
                "target_limit": limit,
                "strict_priority": strict_priority,
                "candidate_shortlist": shortlist,
                "required_output_schema": {
                    "input_direction": "string",
                    "normalized_direction": "string|null",
                    "selected_layer": "string|null",
                    "selected_funds": [
                        {
                            "candidate_id": "string",
                            "code": "string",
                            "name": "string",
                            "manager": "string",
                            "layer": "string",
                            "reason": "string",
                        }
                    ],
                    "selection_reason": "string",
                    "confidence": "high|medium|low",
                },
                "hard_constraints": [
                    "只能从 candidate_shortlist 里的候选选择",
                    "不要输出 ETF 名称的基金",
                    "不要重复同一产品线",
                    "如果 selected_funds 非空，selected_layer 必须与主选层一致",
                    "优先级：东财指数 > 东财权益 > 其他指数 > 其他权益",
                    "匹配顺序：跟踪指数（若缺失则跳过） > 基金名称 > 主题",
                ],
            },
            ensure_ascii=False,
        )

        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1200,
        }
        last_error: str | None = None
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            request = urllib.request.Request(
                LLM_API_URL,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
                raise LlmDecisionError(f"模型接口 HTTP {exc.code}: {detail}") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = f"模型接口调用失败: {exc}"
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(0.8 * attempt)
                    continue
                raise LlmDecisionError(last_error) from exc

            choice = body.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = extract_content_text(message.get("content"))
            if not content:
                content = extract_content_text(choice.get("text"))
            if not content:
                content = extract_content_text(body.get("output_text"))
            if not content:
                last_error = (
                    "模型未返回可解析内容，响应键为: "
                    f"{','.join(sorted(str(key) for key in body.keys()))}"
                )
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(0.8 * attempt)
                    continue
                raise LlmDecisionError(last_error)

            try:
                return json.loads(extract_json_block(content))
            except Exception as exc:  # noqa: BLE001
                last_error = f"模型返回不是合法 JSON: {content}"
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(0.8 * attempt)
                    continue
                raise LlmDecisionError(last_error) from exc

        raise LlmDecisionError(last_error or "模型调用失败")

    def _validate_llm_result(
        self,
        result: dict[str, Any],
        shortlist: dict[str, Any],
        limit: int,
    ) -> dict[str, Any]:
        selected = result.get("selected_funds")
        if not isinstance(selected, list):
            raise LlmDecisionError("模型返回缺少 selected_funds 列表")

        candidate_map: dict[str, dict[str, Any]] = {}
        for layer, items in shortlist["candidate_groups"].items():
            for item in items:
                candidate_map[item["candidate_id"]] = item

        validated_funds: list[dict[str, Any]] = []
        used_codes: set[str] = set()
        used_names: set[str] = set()

        for item in selected:
            if not isinstance(item, dict):
                raise LlmDecisionError("selected_funds 中存在非对象项")
            candidate_id = str(item.get("candidate_id") or "").strip()
            if candidate_id not in candidate_map:
                raise LlmDecisionError(f"模型选择了候选集之外的基金: {candidate_id}")
            source = candidate_map[candidate_id]
            code = source["code"]
            name = source["name"]
            if "ETF" in name.upper():
                raise LlmDecisionError(f"模型选择了 ETF 候选: {name}")
            base_key = dedupe_key(name)
            if code in used_codes or base_key in used_names:
                raise LlmDecisionError(f"模型返回了重复产品线: {name}")
            used_codes.add(code)
            used_names.add(base_key)
            validated_funds.append(
                {
                    "candidate_id": candidate_id,
                    "code": code,
                    "name": name,
                    "manager": source["manager"],
                    "layer": source["layer"],
                    "reason": str(item.get("reason") or "").strip(),
                }
            )

        if len(validated_funds) > limit:
            raise LlmDecisionError(f"模型返回数量超限: {len(validated_funds)} > {limit}")

        selected_layer = result.get("selected_layer")
        if selected_layer is not None and selected_layer not in ALLOWED_LAYERS:
            raise LlmDecisionError(f"模型返回了非法层级: {selected_layer}")

        if validated_funds:
            layers = {item["layer"] for item in validated_funds}
            if selected_layer and selected_layer not in layers:
                raise LlmDecisionError("selected_layer 与 selected_funds 实际层级不一致")
            if len(layers) > 1 and selected_layer:
                if LAYER_PRIORITY[selected_layer] != min(LAYER_PRIORITY[layer] for layer in layers):
                    raise LlmDecisionError("selected_layer 不是返回基金中的最高优先级层")

        return {
            "input_direction": str(result.get("input_direction") or shortlist["input_direction"]),
            "normalized_direction": result.get("normalized_direction") or shortlist["normalized_direction_hint"],
            "selected_layer": selected_layer,
            "selected_funds": validated_funds,
            "selection_reason": str(result.get("selection_reason") or "").strip(),
            "confidence": str(result.get("confidence") or "").strip() or "medium",
        }

    def select_for_direction(
        self,
        direction: str,
        article_context: str,
        limit: int,
        strict_priority: bool,
        include_debug: bool = False,
    ) -> dict[str, Any]:
        shortlist = self._build_shortlist(direction, include_debug=include_debug)
        if shortlist["candidate_count"] == 0:
            return {
                "input_direction": direction,
                "normalized_direction": shortlist["normalized_direction_hint"],
                "selected_layer": None,
                "selected_funds": [],
                "selection_reason": "候选召回为空，模型无可选基金",
                "confidence": "low",
                "errors": ["候选召回为空"],
                "debug": shortlist if include_debug else None,
            }

        try:
            llm_result = self._call_llm_for_direction(
                direction=direction,
                shortlist=shortlist,
                article_context=article_context,
                limit=limit,
                strict_priority=strict_priority,
            )
            validated = self._validate_llm_result(llm_result, shortlist, limit)
            if include_debug:
                validated["debug"] = {
                    "shortlist": shortlist,
                    "llm_raw": llm_result,
                }
            return validated
        except LlmDecisionError as exc:
            return {
                "input_direction": direction,
                "normalized_direction": shortlist["normalized_direction_hint"],
                "selected_layer": None,
                "selected_funds": [],
                "selection_reason": "",
                "confidence": "low",
                "errors": [str(exc)],
                "debug": shortlist if include_debug else None,
            }


class FundSelectorServer:
    def __init__(self) -> None:
        self.selector = FundSelector()

    async def run(self) -> None:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                if response is not None:
                    print(json.dumps(response, ensure_ascii=False), flush=True)
            except json.JSONDecodeError:
                continue
            except Exception as exc:  # noqa: BLE001
                print(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32603, "message": str(exc)},
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "select_funds",
                            "description": (
                                "bot9 基金筛选接口。代码只做候选召回与校验，最终筛选由模型依据基金推荐规则.md 决策。"
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "directions": {
                                        "description": "方向列表，传中文逗号分隔字符串或数组。例：'科技,新能源'",
                                        "oneOf": [
                                            {"type": "string"},
                                            {"type": "array", "items": {"type": "string"}},
                                        ],
                                    },
                                    "article_context": {
                                        "type": "string",
                                        "description": "04 后市展望中与这些方向相关的分析文字，可选。用于让模型理解上下文。",
                                    },
                                    "limit_per_direction": {
                                        "type": "integer",
                                        "minimum": 2,
                                        "maximum": 5,
                                        "default": 3,
                                    },
                                    "strict_priority": {
                                        "type": "boolean",
                                        "default": True,
                                        "description": "是否要求模型尽量遵守高优先级层优先。",
                                    },
                                    "include_debug": {
                                        "type": "boolean",
                                        "default": False,
                                        "description": "返回候选召回和模型原始输出，便于排查。",
                                    },
                                },
                                "required": ["directions"],
                            },
                        }
                    ]
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name != "select_funds":
                return self._error(req_id, -32601, f"Tool not found: {tool_name}")
            result = self._select_funds(arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        return None

    def _select_funds(self, args: dict[str, Any]) -> dict[str, Any]:
        directions = split_directions(args.get("directions"))
        if not directions:
            return {
                "content": [{"type": "text", "text": "directions 不能为空"}],
                "isError": True,
            }

        limit = int(args.get("limit_per_direction", DEFAULT_LIMIT))
        limit = max(MIN_LIMIT, min(limit, MAX_LIMIT))
        strict_priority = coerce_bool(args.get("strict_priority"), True)
        include_debug = coerce_bool(args.get("include_debug"), False)
        contexts = split_article_context(args.get("article_context"), directions)

        max_workers = min(len(directions), 4) or 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self.selector.select_for_direction,
                    direction=direction,
                    article_context=contexts.get(direction, ""),
                    limit=limit,
                    strict_priority=strict_priority,
                    include_debug=include_debug,
                )
                for direction in directions
            ]
            results = [future.result() for future in futures]

        payload = {
            "model": LLM_MODEL,
            "directions": directions,
            "limit_per_direction": limit,
            "strict_priority": strict_priority,
            "results": results,
        }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=False, indent=2),
                }
            ]
        }

    def _error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }


if __name__ == "__main__":
    asyncio.run(FundSelectorServer().run())
