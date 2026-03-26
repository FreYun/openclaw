"""
upstream.py — 上游 research-mcp 客户端

通过 Streamable HTTP 调用上游 MCP 的工具，处理 SSE 响应。
自动管理 session，自动重连。
"""

import json
import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger("research-gateway")

UPSTREAM_URL = "http://research-mcp.jijinmima.cn/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream, application/json",
}


class UpstreamClient:
    """上游 MCP 客户端，自动管理 session"""

    def __init__(self, url: str = UPSTREAM_URL):
        self.url = url
        self.session_id: str | None = None
        self._req_id = 0
        self._client = httpx.Client(timeout=60)

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _parse_sse(self, text: str) -> dict | None:
        for line in text.split("\n"):
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        try:
            return json.loads(text)
        except Exception:
            return None

    def _ensure_session(self):
        if self.session_id:
            return
        headers = {**HEADERS}
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "research-gateway", "version": "0.1.0"},
            },
        }
        r = self._client.post(self.url, headers=headers, json=body)
        self.session_id = r.headers.get("Mcp-Session-Id")
        logger.info(f"Upstream session initialized: {self.session_id}")

    def call_tool(self, name: str, arguments: dict) -> dict:
        """调用上游工具，返回解析后的结果 dict"""
        self._ensure_session()
        headers = {**HEADERS}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        try:
            r = self._client.post(self.url, headers=headers, json=body)
        except Exception as e:
            # Session 可能过期，重新初始化
            self.session_id = None
            self._ensure_session()
            headers["Mcp-Session-Id"] = self.session_id
            r = self._client.post(self.url, headers=headers, json=body)

        data = self._parse_sse(r.text)
        if not data:
            return {"error": f"Failed to parse response: {r.text[:200]}"}

        result = data.get("result", {})
        is_err = result.get("isError", False)
        content = result.get("content", [{}])[0].get("text", "")

        if is_err:
            return {"error": content}

        # 尝试解析 JSON 内容
        try:
            return json.loads(content)
        except Exception:
            return {"raw": content}


# ============ 日期/代码格式化工具 ============


def fmt_date(d: str | None) -> str | None:
    """将各种日期格式统一为 YYYYMMDD"""
    if not d:
        return None
    d = d.replace("-", "").replace("/", "").strip()
    if len(d) == 8 and d.isdigit():
        return d
    return None


def today_str() -> str:
    return date.today().strftime("%Y%m%d")


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).strftime("%Y%m%d")


def ensure_stock_code(code: str) -> str:
    """确保股票代码是 6 位纯数字"""
    return code.strip().split(".")[0]


def ensure_index_suffix(symbol: str) -> str:
    """确保 A 股指数带 .SH/.SZ 后缀"""
    s = symbol.strip()
    if "." in s:
        return s
    if s.startswith(("000", "880", "990")):
        return f"{s}.SH"
    if s.startswith(("399",)):
        return f"{s}.SZ"
    return f"{s}.SH"
