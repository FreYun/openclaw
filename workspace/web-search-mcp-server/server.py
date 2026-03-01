#!/usr/bin/env python3
"""
Web Search MCP Server (SSE) + REST Facade

- MCP over HTTP/SSE for MCP-compatible clients:
    • GET  /sse            -> server-sent events stream (server -> client)
    • POST /messages       -> MCP client -> server messages

- REST API:
    • POST /api/search           -> general web search
    • POST /api/quick_search     -> quick search with compact results
    • POST /api/structured_search -> search with structured facts extraction
    • GET  /healthz
    • GET  /metrics

Design goals:
    - Shared core handlers (no duplication between MCP and REST)
    - Structured JSON errors with request_id
    - Per-request logging and timing
    - Integration with SearXNG backend
    - LLM-optimized response formatting
"""

import os
import sys
import json
import time
import uuid
import asyncio
import logging
import httpx
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, PlainTextResponse
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# -------------------------
# Configuration
# -------------------------
# duckduckgo = 用 DuckDuckGo（免 API、国内可用）；searxng = 用 SearXNG
SEARCH_BACKEND = os.getenv("SEARCH_BACKEND", "duckduckgo").lower()
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "30.0"))

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


# 让所有 logger（含 mcp/uvicorn）的 record 都有 request_id，避免 KeyError
for h in logging.root.handlers:
    h.addFilter(RequestIdFilter())

logger = logging.getLogger("websearch-mcp")
logger.addFilter(RequestIdFilter())

# -------------------------
# Globals / Singletons
# -------------------------
mcp_server = Server("web-search-service")
sse_transport = SseServerTransport("/messages")
http_client: Optional[httpx.AsyncClient] = None

# Simple in-memory metrics
METRICS = {
    "api_search_calls": 0,
    "api_quick_search_calls": 0,
    "api_structured_search_calls": 0,
    "mcp_call_tool_calls": 0,
    "searxng_requests": 0,
    "errors_total": 0,
}


def get_http_client() -> httpx.AsyncClient:
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=SEARXNG_TIMEOUT)
        logger.info("HTTP client initialized", extra={"request_id": "-"})
    return http_client


# -------------------------
# Utilities
# -------------------------
def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def json_error(message: str, status_code: int = 400, request_id: str = "-") -> JSONResponse:
    METRICS["errors_total"] += 1
    payload = {
        "ok": False,
        "error": {
            "code": status_code,
            "message": message,
        },
        "request_id": request_id,
    }
    return JSONResponse(payload, status_code=status_code)


# -------------------------
# SearXNG Integration
# -------------------------
def _query_duckduckgo_sync(query: str, max_results: int = 10) -> Dict[str, Any]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            items = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        raise Exception(f"DuckDuckGo search failed: {e}")
    results = []
    for i, r in enumerate(items):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("href", r.get("url", "")),
            "content": r.get("body", r.get("snippet", "")),
            "score": 1.0 - (i * 0.05),
            "engines": ["duckduckgo"],
        })
    return {"query": query, "results": results, "infoboxes": [], "suggestions": [], "answers": []}


async def _fetch_search_results(query: str, categories: str = "general", pageno: int = 1) -> Dict[str, Any]:
    """统一入口：按 SEARCH_BACKEND 选 DuckDuckGo 或 SearXNG"""
    if SEARCH_BACKEND == "duckduckgo":
        METRICS["searxng_requests"] += 1
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: _query_duckduckgo_sync(query, max_results=min(10 * pageno, 30)))
    return await query_searxng(query, categories, pageno)


async def query_searxng(query: str, categories: str = "general", pageno: int = 1) -> Dict[str, Any]:
    """Query SearXNG and return raw JSON response"""
    METRICS["searxng_requests"] += 1
    client = get_http_client()

    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "pageno": pageno,
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        # 公网实例常用 GET；POST 可能被拒或返回空
        response = await client.get(
            f"{SEARXNG_URL}/search",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"SearXNG request failed: {e}")
        raise Exception(f"Search backend error: {str(e)}")


def format_for_llm_compact(searxng_response: Dict[str, Any]) -> Dict[str, Any]:
    """Format search response in compact LLM-friendly format"""
    results = searxng_response.get("results", [])
    infoboxes = searxng_response.get("infoboxes", [])

    # Extract top results sorted by score
    top_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)[:10]

    formatted_results = []
    for idx, r in enumerate(top_results, 1):
        formatted_results.append({
            "rank": idx,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            "score": round(r.get("score", 0.0), 2),
            "engines": r.get("engines", []),
            "published": r.get("publishedDate"),
        })

    # Extract knowledge base from infobox
    knowledge_base = None
    if infoboxes:
        infobox = infoboxes[0]
        knowledge_base = {
            "entity": infobox.get("infobox", ""),
            "description": infobox.get("content", ""),
            "image": infobox.get("img_src", ""),
            "attributes": {
                attr.get("label", ""): attr.get("value", "")
                for attr in infobox.get("attributes", [])
            },
            "urls": infobox.get("urls", []),
        }

    return {
        "query": searxng_response.get("query", ""),
        "total_results": len(results),
        "knowledge_base": knowledge_base,
        "top_results": formatted_results,
        "engines_used": list(set([
            engine
            for r in results
            for engine in r.get("engines", [])
        ])),
    }


def format_for_llm_structured(searxng_response: Dict[str, Any]) -> Dict[str, Any]:
    """Format search response with structured facts extraction"""
    compact = format_for_llm_compact(searxng_response)
    results = searxng_response.get("results", [])

    # Extract context snippets from top results
    context_snippets = [
        r.get("content", "")
        for r in sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)[:5]
        if r.get("content")
    ]

    # Build structured output
    return {
        **compact,
        "context_snippets": context_snippets,
        "suggestions": searxng_response.get("suggestions", []),
        "answers": searxng_response.get("answers", []),
    }


# -------------------------
# Core Handlers (shared by MCP & REST)
# -------------------------
async def core_web_search(
    *,
    query: str,
    categories: str = "general",
    pageno: int = 1,
    request_id: str = "-",
) -> Dict[str, Any]:
    """General web search - returns full SearXNG response"""
    searxng_resp = await _fetch_search_results(query, categories, pageno)

    return {
        "ok": True,
        "request_id": request_id,
        "query": query,
        "categories": categories,
        "results_count": len(searxng_resp.get("results", [])),
        "data": searxng_resp,
    }


async def core_quick_search(
    *,
    query: str,
    categories: str = "general",
    request_id: str = "-",
) -> Dict[str, Any]:
    """Quick search - returns compact LLM-friendly format"""
    searxng_resp = await _fetch_search_results(query, categories, 1)
    formatted = format_for_llm_compact(searxng_resp)

    return {
        "ok": True,
        "request_id": request_id,
        **formatted,
    }


async def core_structured_search(
    *,
    query: str,
    categories: str = "general",
    request_id: str = "-",
) -> Dict[str, Any]:
    """Structured search - returns facts-optimized format for LLM"""
    searxng_resp = await _fetch_search_results(query, categories, 1)
    formatted = format_for_llm_structured(searxng_resp)

    return {
        "ok": True,
        "request_id": request_id,
        **formatted,
    }


# -------------------------
# MCP Tool Registry
# -------------------------
@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="web_search",
            description=(
                "Perform a general web search and return comprehensive results. "
                "Returns full SearXNG response with all metadata, infoboxes, and suggestions. "
                "Use this when you need complete search results with all details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "categories": {
                        "type": "string",
                        "description": "Search categories (e.g., 'general', 'news', 'images', 'videos')",
                        "default": "general",
                    },
                    "pageno": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                        "minimum": 1,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="quick_search",
            description=(
                "Perform a quick web search optimized for LLM consumption. "
                "Returns top 10 results in compact format with knowledge base, "
                "relevance scores, and source attribution. Perfect for answering "
                "user questions with verified web sources."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "categories": {
                        "type": "string",
                        "description": "Search categories",
                        "default": "general",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="structured_search",
            description=(
                "Perform a structured web search with facts extraction for LLM reasoning. "
                "Returns ranked results, knowledge base with structured attributes, "
                "context snippets, and related suggestions. Ideal for detailed research "
                "and fact-checking tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "categories": {
                        "type": "string",
                        "description": "Search categories",
                        "default": "general",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    METRICS["mcp_call_tool_calls"] += 1
    req_id = new_request_id()
    start = time.time()
    try:
        logger.info(f"MCP call_tool '{name}' started", extra={"request_id": req_id})

        if name == "web_search":
            resp = await core_web_search(
                query=arguments["query"],
                categories=arguments.get("categories", "general"),
                pageno=int(arguments.get("pageno", 1)),
                request_id=req_id,
            )
        elif name == "quick_search":
            resp = await core_quick_search(
                query=arguments["query"],
                categories=arguments.get("categories", "general"),
                request_id=req_id,
            )
        elif name == "structured_search":
            resp = await core_structured_search(
                query=arguments["query"],
                categories=arguments.get("categories", "general"),
                request_id=req_id,
            )
        else:
            return [TextContent(type="text", text=json.dumps({
                "ok": False,
                "request_id": req_id,
                "error": {"code": 400, "message": f"Unknown tool: {name}"},
            }, ensure_ascii=False))]

        elapsed = (time.time() - start) * 1000.0
        logger.info(f"MCP call_tool '{name}' finished in {elapsed:.1f} ms", extra={"request_id": req_id})
        return [TextContent(type="text", text=json.dumps(resp, indent=2, ensure_ascii=False))]
    except Exception as e:
        logger.exception(f"MCP tool error: {e}", extra={"request_id": req_id})
        return [TextContent(type="text", text=json.dumps({
            "ok": False,
            "request_id": req_id,
            "error": {"code": 500, "message": str(e)},
        }, ensure_ascii=False))]


# -------------------------
# HTTP/SSE Endpoints
# -------------------------
async def handle_sse(request: Request):
    """Handle SSE connection for MCP (server -> client stream)."""
    req_id = new_request_id()
    extra = {"request_id": req_id}
    logger.info("SSE connect", extra=extra)

    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )

    logger.info("SSE disconnect", extra=extra)
    return Response()


# -------------------------
# REST API Endpoints
# -------------------------
async def api_search(request: Request):
    METRICS["api_search_calls"] += 1
    req_id = new_request_id()
    extra = {"request_id": req_id}

    try:
        payload = await request.json()
    except Exception:
        return json_error("Invalid JSON body", 400, req_id)

    query = payload.get("query")
    categories = payload.get("categories", "general")
    pageno = payload.get("pageno", 1)

    if not isinstance(query, str) or not query.strip():
        return json_error("Field 'query' (non-empty string) is required.", 400, req_id)

    try:
        pageno = int(pageno)
        if pageno < 1:
            return json_error("Field 'pageno' must be >= 1.", 400, req_id)
    except Exception:
        return json_error("Field 'pageno' must be an integer.", 400, req_id)

    start = time.time()
    try:
        resp = await core_web_search(
            query=query.strip(),
            categories=categories,
            pageno=pageno,
            request_id=req_id,
        )
        elapsed = (time.time() - start) * 1000.0
        logger.info(f"REST /api/search -> {resp['results_count']} results in {elapsed:.1f} ms", extra=extra)
        return JSONResponse(resp, status_code=200)
    except Exception as e:
        logger.exception(f"/api/search error: {e}", extra=extra)
        return json_error(str(e), 500, req_id)


async def api_quick_search(request: Request):
    METRICS["api_quick_search_calls"] += 1
    req_id = new_request_id()
    extra = {"request_id": req_id}

    try:
        payload = await request.json()
    except Exception:
        return json_error("Invalid JSON body", 400, req_id)

    query = payload.get("query")
    categories = payload.get("categories", "general")

    if not isinstance(query, str) or not query.strip():
        return json_error("Field 'query' (non-empty string) is required.", 400, req_id)

    start = time.time()
    try:
        resp = await core_quick_search(
            query=query.strip(),
            categories=categories,
            request_id=req_id,
        )
        elapsed = (time.time() - start) * 1000.0
        logger.info(f"REST /api/quick_search -> {resp['total_results']} results in {elapsed:.1f} ms", extra=extra)
        return JSONResponse(resp, status_code=200)
    except Exception as e:
        logger.exception(f"/api/quick_search error: {e}", extra=extra)
        return json_error(str(e), 500, req_id)


async def api_structured_search(request: Request):
    METRICS["api_structured_search_calls"] += 1
    req_id = new_request_id()
    extra = {"request_id": req_id}

    try:
        payload = await request.json()
    except Exception:
        return json_error("Invalid JSON body", 400, req_id)

    query = payload.get("query")
    categories = payload.get("categories", "general")

    if not isinstance(query, str) or not query.strip():
        return json_error("Field 'query' (non-empty string) is required.", 400, req_id)

    start = time.time()
    try:
        resp = await core_structured_search(
            query=query.strip(),
            categories=categories,
            request_id=req_id,
        )
        elapsed = (time.time() - start) * 1000.0
        logger.info(f"REST /api/structured_search -> {resp['total_results']} results in {elapsed:.1f} ms", extra=extra)
        return JSONResponse(resp, status_code=200)
    except Exception as e:
        logger.exception(f"/api/structured_search error: {e}", extra=extra)
        return json_error(str(e), 500, req_id)


async def list_tools_rest(_: Request):
    tools = await list_tools()
    return JSONResponse([t.model_dump() for t in tools], status_code=200)


async def healthz(_: Request):
    return PlainTextResponse("ok\n", status_code=200)


async def metrics(_: Request):
    return JSONResponse({"ok": True, "metrics": METRICS}, status_code=200)


# -------------------------
# App & Routing
# -------------------------
routes = [
    # MCP transport endpoints
    Route("/sse", endpoint=handle_sse, methods=["GET"]),
    Mount("/messages", app=sse_transport.handle_post_message),

    # REST API
    Route("/api/search", endpoint=api_search, methods=["POST"]),
    Route("/api/quick_search", endpoint=api_quick_search, methods=["POST"]),
    Route("/api/structured_search", endpoint=api_structured_search, methods=["POST"]),

    # Health & Metrics
    Route("/healthz", endpoint=healthz, methods=["GET"]),
    Route("/metrics", endpoint=metrics, methods=["GET"]),

    # Tool listing
    Route("/tools", endpoint=list_tools_rest, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)


# -------------------------
# Startup / Main
# -------------------------
if __name__ == "__main__":
    import uvicorn

    try:
        if SEARCH_BACKEND == "searxng":
            get_http_client()
            logger.info(f"MCP server ready, backend=SearXNG at {SEARXNG_URL}", extra={"request_id": "-"})
        else:
            logger.info("MCP server ready, backend=DuckDuckGo (no API key)", extra={"request_id": "-"})
    except Exception as e:
        logger.exception(f"Failed to initialize: {e}", extra={"request_id": "-"})
        raise

    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
