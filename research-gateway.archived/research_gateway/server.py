"""
research-gateway — skill 部门主网关

架构：
  1. 所有聚合工具注册到一个 registry
  2. 根据 permissions.yaml，为每个角色创建独立 FastMCP 实例（只含该角色可用的工具）
  3. 每个 bot 通过 URL 路径接入: /mcp/{bot_id}
  4. 一个进程、一个端口，但每个 bot 看到的工具集不同

bot 的 mcporter.json 只需:
  {"mcpServers": {"skill-gateway": {"url": "http://localhost:18080/mcp/bot7"}}}
"""

import json
import logging
import os
from typing import Callable

import uvicorn
import yaml
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from research_gateway.upstream import (
    UpstreamClient,
    days_ago,
    ensure_index_suffix,
    ensure_stock_code,
    fmt_date,
    today_str,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("research-gateway")

upstream = UpstreamClient()

# ============================================================
# 工具 Registry — 所有聚合工具定义在这里
# ============================================================

# 每个工具是 (name, func, description, input_schema) 的元组
# 用 registry dict 收集，后面按角色选择性注册到 FastMCP 实例

TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(name: str, description: str):
    """装饰器：注册工具到全局 registry"""

    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "name": name,
            "func": func,
            "description": description,
        }
        return func

    return decorator


# ---------- 1. market_snapshot ----------


@register_tool(
    "market_snapshot",
    "全球市场快照。一次获取 A股/港股/美股 主要指数行情、成交额、市场情绪。",
)
def market_snapshot(
    markets: list[str] = ["A", "HK", "US"],
    include_sentiment: bool = True,
) -> str:
    """全球市场快照。

    markets: 市场列表，可选 "A"(A股), "HK"(港股), "US"(美股)
    include_sentiment: 是否包含 A 股恐慌指数和成交额
    """
    result = {}
    if "A" in markets:
        result["A股"] = upstream.call_tool("market_overview", {})
        if include_sentiment:
            result["A股恐慌指数"] = upstream.call_tool(
                "get_ashares_gvix",
                {"start_date": days_ago(5), "end_date": today_str()},
            )
    if "HK" in markets:
        result["港股"] = upstream.call_tool("get_hshares_market_overview", {})
        result["南向资金"] = upstream.call_tool(
            "get_southbound_hkd_turnover",
            {"start_date": days_ago(5), "end_date": today_str()},
        )
    if "US" in markets:
        result["美股"] = upstream.call_tool(
            "get_usstock_index_quote",
            {"symbol": "DJIA.GI,SPX.GI,NDX.GI", "start_date": days_ago(5), "end_date": today_str()},
        )
    return json.dumps(result, ensure_ascii=False)


# ---------- 2. fund_analysis ----------


@register_tool(
    "fund_analysis",
    "基金全面分析。输入基金代码，返回基本信息、业绩、风格、重仓股、行业分布等。",
)
def fund_analysis(
    code: str,
    aspects: list[str] = ["comprehensive"],
    start_date: str = "",
    end_date: str = "",
) -> str:
    """基金分析。

    code: 6位基金代码，如 000001
    aspects: 分析维度，可选: comprehensive(一站式), nav(净值走势), abnormal(异动), manager(经理), rate(费率), bonus(分红)
    start_date: 净值查询起始日期 YYYYMMDD（仅 nav 用）
    end_date: 净值查询结束日期
    """
    result = {}
    if "comprehensive" in aspects:
        result["comprehensive"] = upstream.call_tool("get_fund_comprehensive_analysis", {"fund_code": code})
    if "nav" in aspects:
        sd = fmt_date(start_date) or days_ago(30)
        ed = fmt_date(end_date) or today_str()
        result["nav"] = upstream.call_tool("get_fund_nav_and_return", {"fund_code": code, "start_date": sd, "end_date": ed})
    if "abnormal" in aspects:
        result["abnormal"] = upstream.call_tool("get_fund_abnormal_movement", {"fund_code": code})
    if "manager" in aspects:
        result["manager"] = upstream.call_tool("get_fund_manager_info", {"fund_code": code})
    if "rate" in aspects:
        result["rate"] = upstream.call_tool("fund_rate", {"fcode": code})
    if "bonus" in aspects:
        result["bonus"] = upstream.call_tool("fund_bonus", {"fcode": code})
    return json.dumps(result, ensure_ascii=False)


# ---------- 3. fund_screen ----------


@register_tool(
    "fund_screen",
    "基金筛选。支持按类型、主题板块、持仓股票等方式筛选。",
)
def fund_screen(
    by: str = "type",
    fund_type: str = "",
    theme: str = "",
    stock_code: str = "",
    min_return: float = 0,
    max_drawdown: float = 0,
    limit: int = 10,
) -> str:
    """基金筛选。

    by: 筛选方式 - "type"(按类型), "theme"(按主题), "stock"(按持仓股票)
    fund_type: 基金类型 "股票型"/"混合型"/"债券型"/"指数型"/"QDII"
    theme: 主题名 "半导体"/"新能源"/"消费"/"医药"
    stock_code: 股票代码，筛选重仓该股的基金，如 "600519"
    min_return: 最低收益率
    max_drawdown: 最大回撤限制
    limit: 返回数量
    """
    if by == "theme" and theme:
        return json.dumps(upstream.call_tool("fund_theme_screening", {"sec_name": theme}), ensure_ascii=False)
    if by == "stock" and stock_code:
        return json.dumps(upstream.call_tool("fund_stock_holdings", {"stock_codes": ensure_stock_code(stock_code)}), ensure_ascii=False)
    args = {"limit": limit}
    if fund_type:
        args["fund_type"] = fund_type
    if min_return:
        args["min_return"] = min_return
    if max_drawdown:
        args["max_drawdown"] = max_drawdown
    return json.dumps(upstream.call_tool("simple_fund_search", args), ensure_ascii=False)


# ---------- 4. stock_research ----------


@register_tool(
    "stock_research",
    "个股研究。返回基本面、K线、估值、资金流向、北向持股。",
)
def stock_research(
    code: str,
    aspects: list[str] = ["basic", "quote", "valuation"],
    days: int = 30,
) -> str:
    """个股研究。

    code: 6位股票代码，如 600519(茅台)
    aspects: 维度 basic/quote/valuation/flow/northbound/shareholder/market_value
    days: 行情回溯天数
    """
    sc = ensure_stock_code(code)
    sd = days_ago(days)
    ed = today_str()
    result = {}
    tool_map = {
        "basic": ("get_stock_info", {"stock_code": sc}),
        "quote": ("get_stock_daily_quote", {"stock_code": sc, "start_date": sd, "end_date": ed}),
        "valuation": ("get_stock_valuation", {"stock_code": sc}),
        "flow": ("get_stock_fund_flow", {"stock_code": sc, "start_date": sd, "end_date": ed}),
        "northbound": ("get_stock_northbound_holding", {"stock_code": sc, "start_date": sd, "end_date": ed}),
        "shareholder": ("get_stock_shareholder", {"stock_code": sc}),
        "market_value": ("get_stock_market_value", {"stock_code": sc}),
    }
    for aspect in aspects:
        if aspect in tool_map:
            tool_name, args = tool_map[aspect]
            result[aspect] = upstream.call_tool(tool_name, args)
    return json.dumps(result, ensure_ascii=False)


# ---------- 5. bond_monitor ----------


@register_tool(
    "bond_monitor",
    "债券收益率与利差监测。支持中国/美国国债、信用债、中美利差。",
)
def bond_monitor(
    query: str = "cn_10y",
    days: int = 30,
) -> str:
    """债券监测。

    query: 查询类型 cn_10y/cn_curve/us_10y/us_curve/spread_cn_us/spread_credit/credit_3y
    days: 回溯天数
    """
    sd = days_ago(days)
    ed = today_str()
    dispatch = {
        "cn_10y": ("get_cn_bond_yield", {"maturity": "10Y", "start_date": sd, "end_date": ed}),
        "cn_curve": ("get_cn_bond_yield", {"maturity": "1Y,2Y,5Y,10Y,30Y", "start_date": sd, "end_date": ed}),
        "us_10y": ("get_us_bond_yield", {"maturity": "10Y", "start_date": sd, "end_date": ed}),
        "us_curve": ("get_us_bond_yield", {"maturity": "2Y,5Y,10Y,30Y", "start_date": sd, "end_date": ed}),
        "spread_cn_us": ("get_bond_yield_spread", {"spread_type": "cn_vs_us", "maturity": "10Y"}),
        "spread_credit": ("get_bond_yield_spread", {"spread_type": "credit_vs_cn", "maturity": "5y"}),
        "credit_3y": ("get_credit_bond_yield", {"maturity": "3y", "start_date": sd, "end_date": ed}),
    }
    if query not in dispatch:
        return json.dumps({"error": f"未知查询类型: {query}，可选: {', '.join(dispatch.keys())}"}, ensure_ascii=False)
    tool_name, args = dispatch[query]
    return json.dumps(upstream.call_tool(tool_name, args), ensure_ascii=False)


# ---------- 6. macro_overview ----------


@register_tool(
    "macro_overview",
    "宏观经济数据概览。支持中国(GDP/CPI/PPI/M2等)和美国宏观数据。",
)
def macro_overview(
    region: str = "CN",
    indicators: str = "cpi,ppi,m2,pmi",
) -> str:
    """宏观经济。

    region: "CN"(中国) / "US"(美国) / "ALL"(都查)
    indicators: 中国指标(小写逗号分隔): gdp,cpi,ppi,m1,m2,pmi,export,import,usdcny,fai,iva,retail,afre
    """
    result = {}
    if region in ("CN", "ALL"):
        result["CN"] = upstream.call_tool("get_cn_macro_data", {"category": indicators.lower()})
    if region in ("US", "ALL"):
        result["US"] = upstream.call_tool("us_macro_simple", {})
    return json.dumps(result, ensure_ascii=False)


# ---------- 7. commodity_quote ----------


@register_tool(
    "commodity_quote",
    "商品历史行情。支持黄金、白银等，中文或代码均可。",
)
def commodity_quote(
    symbol: str = "AU9999",
    days: int = 30,
) -> str:
    """商品行情。

    symbol: 商品代码或中文，如 "AU9999"/"黄金9999"/"AG9999"/"白银9999"，多个逗号分隔
    days: 回溯天数
    """
    return json.dumps(
        upstream.call_tool("commodity_data", {"symbol": symbol, "start_date": days_ago(days), "end_date": today_str()}),
        ensure_ascii=False,
    )


# ---------- 8. search_news ----------


@register_tool(
    "search_news",
    "搜索最新财经新闻。语义匹配，返回摘要和相关度评分。",
)
def search_news(
    query: str,
    top_k: int = 5,
    days_ago_limit: int = 7,
) -> str:
    """新闻搜索。

    query: 关键词，如 "黄金 价格"、"半导体 芯片"
    top_k: 返回条数
    days_ago_limit: 搜索多少天内
    """
    args = {"query": query, "top_k": top_k}
    if days_ago_limit:
        args["search_day_ago"] = days_ago_limit
    return json.dumps(upstream.call_tool("news_search", args), ensure_ascii=False)


# ---------- 9. search_report ----------


@register_tool(
    "search_report",
    "搜索券商研报。语义匹配，返回研报内容和相关度评分。",
)
def search_report(
    query: str,
    top_k: int = 3,
    days_ago_limit: int = 30,
) -> str:
    """研报搜索。

    query: 关键词，如 "半导体 行业"、"消费 复苏"
    top_k: 返回条数
    days_ago_limit: 搜索多少天内
    """
    args = {"query": query, "top_k": top_k}
    if days_ago_limit:
        args["search_day_ago"] = days_ago_limit
    return json.dumps(upstream.call_tool("research_search", args), ensure_ascii=False)


# ---------- 10. index_valuation ----------


@register_tool(
    "index_valuation",
    "A股指数估值与行情。查询PE、历史百分位及近期走势。",
)
def index_valuation(
    symbols: str = "000300.SH",
    include_quote: bool = True,
    days: int = 30,
) -> str:
    """指数估值。

    symbols: 指数代码逗号分隔。常用: 000001.SH(上证), 000300.SH(沪深300), 000905.SH(中证500), 399006.SZ(创业板)
    include_quote: 是否包含行情走势
    days: 行情回溯天数
    """
    syms = ",".join(ensure_index_suffix(s.strip()) for s in symbols.split(","))
    result = {}
    result["valuation"] = upstream.call_tool("get_ashares_index_val", {"symbol": syms})
    if include_quote:
        result["quote"] = upstream.call_tool(
            "get_ashares_index_quote",
            {"symbol": syms, "start_date": days_ago(days), "end_date": today_str()},
        )
    return json.dumps(result, ensure_ascii=False)


# ---------- 管理工具（仅 admin 角色可见） ----------


@register_tool(
    "reload_permissions",
    "重载权限配置。skill 部门修改 permissions.yaml 后调用。",
)
def reload_permissions_tool() -> str:
    """重载权限配置，使 yaml 修改生效。需要重启网关才能刷新工具集。"""
    return json.dumps({"message": "请重启网关以刷新权限配置: bash run.sh restart"}, ensure_ascii=False)


# ============================================================
# 动态构建：按角色创建 FastMCP 实例
# ============================================================


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "permissions.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_bot_tool_overrides() -> dict[str, list[str]]:
    """读取 dashboard 写入的 per-bot 工具覆盖配置"""
    override_path = os.path.join(os.path.dirname(__file__), "..", "bot-tool-overrides.json")
    try:
        with open(override_path) as f:
            return json.load(f)
    except Exception:
        return {}


def make_instance(name: str, tool_names: list[str]) -> FastMCP:
    inst = FastMCP(name, instructions="Skill 部门网关。提供金融研究数据查询工具。")
    for tool_name in tool_names:
        if tool_name in TOOL_REGISTRY:
            entry = TOOL_REGISTRY[tool_name]
            inst.add_tool(entry["func"], name=entry["name"], description=entry["description"])
    return inst


def build_instances() -> dict[str, FastMCP]:
    """为每个角色创建一个 FastMCP 实例，只注册该角色允许的工具"""
    config = load_config()
    roles = config.get("roles", {})
    instances = {}

    for role_name, tool_names in roles.items():
        instances[role_name] = make_instance(f"skill-gateway-{role_name}", tool_names)
        logger.info(f"Built instance for role '{role_name}' with {len(tool_names)} tools: {tool_names}")

    return instances


def build_bot_mapping(config: dict) -> dict[str, str]:
    """bot_id → role_name 映射"""
    return config.get("bots", {})


def build_app() -> Starlette:
    """构建 Starlette 应用：每个 bot 路径 → 对应角色的 FastMCP 实例（或自定义工具列表）"""
    from contextlib import asynccontextmanager

    config = load_config()
    role_instances = build_instances()
    bot_mapping = build_bot_mapping(config)
    default_role = bot_mapping.get("default", "content_creator")
    overrides = load_bot_tool_overrides()

    # 为有自定义工具列表的 bot 创建独立实例
    custom_instances: dict[str, FastMCP] = {}
    for bot_id, tool_names in overrides.items():
        if tool_names:
            custom_instances[bot_id] = make_instance(f"skill-gateway-custom-{bot_id}", tool_names)
            logger.info(f"Built custom instance for bot '{bot_id}' with tools: {tool_names}")

    # 所有需要启动 session manager 的实例
    all_instances = {**role_instances, **{f"custom-{k}": v for k, v in custom_instances.items()}}

    # 为每个实例获取 streamable_http_app
    role_apps = {r: inst.streamable_http_app() for r, inst in role_instances.items()}
    custom_apps = {bot_id: inst.streamable_http_app() for bot_id, inst in custom_instances.items()}

    @asynccontextmanager
    async def lifespan(app):
        import contextlib
        async with contextlib.AsyncExitStack() as stack:
            for name, inst in all_instances.items():
                if inst._session_manager is not None:
                    await stack.enter_async_context(inst._session_manager.run())
                    logger.info(f"Session manager started for '{name}'")
            yield

    routes = []
    registered_bots = set()

    for bot_id, role_name in bot_mapping.items():
        if bot_id == "default":
            continue
        # 优先使用自定义工具列表，否则用角色
        if bot_id in custom_apps:
            routes.append(Mount(f"/mcp/{bot_id}", app=custom_apps[bot_id]))
            registered_bots.add(bot_id)
            logger.info(f"Mounted /mcp/{bot_id} → custom tools {overrides[bot_id]}")
        elif role_name in role_apps:
            routes.append(Mount(f"/mcp/{bot_id}", app=role_apps[role_name]))
            registered_bots.add(bot_id)
            logger.info(f"Mounted /mcp/{bot_id} → role '{role_name}'")
        else:
            logger.warning(f"Bot '{bot_id}' maps to unknown role '{role_name}', skipping")

    if default_role in role_apps:
        routes.append(Mount("/mcp/default", app=role_apps[default_role]))
        logger.info(f"Mounted /mcp/default → role '{default_role}'")

    # 健康检查
    async def health(request: Request):
        return JSONResponse({
            "status": "healthy",
            "service": "skill-gateway",
            "registered_bots": sorted(registered_bots),
            "roles": list(role_instances.keys()),
            "tools_per_role": {r: len(config["roles"].get(r, [])) for r in role_instances},
            "custom_bots": list(custom_instances.keys()),
        })

    # 根路由
    async def index(request: Request):
        lines = ["Skill 部门主网关", "", "连接方式: /mcp/{bot_id}", "", "已注册的 bot:"]
        for bot_id in sorted(registered_bots):
            if bot_id in custom_instances:
                tools = overrides[bot_id]
                lines.append(f"  /mcp/{bot_id} → custom ({len(tools)} tools: {', '.join(tools)})")
            else:
                role = bot_mapping.get(bot_id, default_role)
                tool_count = len(config["roles"].get(role, []))
                lines.append(f"  /mcp/{bot_id} → {role} ({tool_count} tools)")
        lines.append(f"  /mcp/default → {default_role}")
        lines.append("")
        lines.append("健康检查: /health")
        return PlainTextResponse("\n".join(lines))

    routes.append(Route("/health", health))
    routes.append(Route("/", index))

    return Starlette(routes=routes, lifespan=lifespan)


# ============================================================
# 入口
# ============================================================


def main():
    port = int(os.environ.get("GATEWAY_PORT", "18080"))
    logger.info(f"Starting skill-gateway on port {port}")
    app = build_app()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
