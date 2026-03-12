#!/usr/bin/env python3
"""
Bot 巡检脚本 — 检查所有 bot 的 MCP 服务状态和小红书登录状态。

用法:
  python3 check_bots.py
  python3 check_bots.py --xhs-url http://localhost:18060
  python3 check_bots.py --bots bot1 bot2 bot5
  python3 check_bots.py --skip-login   # 只检查 MCP 服务，不检查登录
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

XHS_MCP_URL = "http://localhost:18060"
FINANCE_MCP_URL = "http://localhost:8000"
OPENCLAW_DIR = Path("/home/rooot/.openclaw")
XHS_PROFILES_DIR = Path("/home/rooot/.xhs-profiles")

# 活跃 bot 列表
ACTIVE_BOTS = {
    "bot1": "来财妹妹",
    "bot2": "狗哥说财",
    "bot3": "meme爱基金",
    "bot4": "研报搬运工阿泽",
    "bot5": "宣妈慢慢变富",
    "bot6": "爱理财的James",
    "bot7": "老K投资笔记",
}


def check_mcp_services(xhs_url: str) -> dict:
    """检查各 MCP 服务健康状态。"""
    services = {}

    # xiaohongshu-mcp
    try:
        r = requests.get(f"{xhs_url}/health", timeout=5)
        services["xiaohongshu-mcp"] = r.status_code == 200
    except Exception:
        services["xiaohongshu-mcp"] = False

    # finance-data
    try:
        r = requests.get(f"{FINANCE_MCP_URL}/sse", timeout=5, stream=True)
        services["finance-data"] = r.status_code == 200
        r.close()
    except Exception:
        services["finance-data"] = False

    return services


def check_bot_mcp_config() -> dict:
    """检查每个 bot workspace 的 mcporter.json 是否配了 xiaohongshu-mcp。"""
    results = {}
    for bot_id in ACTIVE_BOTS:
        config_path = OPENCLAW_DIR / f"workspace-{bot_id}" / "config" / "mcporter.json"
        if not config_path.exists():
            results[bot_id] = False
            continue
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            results[bot_id] = "xiaohongshu-mcp" in data.get("mcpServers", {})
        except Exception:
            results[bot_id] = False
    return results


def init_mcp_session(base_url: str) -> str:
    """初始化 MCP session。"""
    resp = requests.post(
        f"{base_url}/mcp",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "check_bots", "version": "1.0"},
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    session_id = resp.headers.get("Mcp-Session-Id")
    if not session_id:
        raise RuntimeError("服务器未返回 Mcp-Session-Id")
    return session_id


def check_xhs_login(base_url: str, session_id: str, bot_id: str) -> str:
    """检查单个 bot 的小红书登录状态。"""
    resp = requests.post(
        f"{base_url}/mcp",
        headers={"Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "check_login_status", "arguments": {"account_id": bot_id}},
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        return "error"
    for item in data.get("result", {}).get("content", []):
        text = item.get("text", "")
        if "已登录" in text:
            return "logged_in"
        if "未登录" in text:
            return "not_logged_in"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Bot 巡检：MCP + 小红书登录")
    parser.add_argument("--xhs-url", default=XHS_MCP_URL, help="xiaohongshu-mcp 地址")
    parser.add_argument("--bots", nargs="+", help="只检查指定 bot")
    parser.add_argument("--skip-login", action="store_true", help="跳过登录检查")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    bots = args.bots if args.bots else list(ACTIVE_BOTS.keys())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    result = {
        "time": now,
        "mcp_services": {},
        "mcp_config": {},
        "xhs_login": {},
    }

    # === 1. MCP 服务状态 ===
    mcp_status = check_mcp_services(args.xhs_url)
    result["mcp_services"] = mcp_status

    # === 2. Bot MCP 配置 ===
    mcp_config = check_bot_mcp_config()
    result["mcp_config"] = {k: v for k, v in mcp_config.items() if k in bots}

    # === 3. 小红书登录状态 ===
    if not args.skip_login and mcp_status.get("xiaohongshu-mcp"):
        try:
            session_id = init_mcp_session(args.xhs_url)
            for bot_id in bots:
                try:
                    status = check_xhs_login(args.xhs_url, session_id, bot_id)
                except Exception as e:
                    status = f"error:{e}"
                result["xhs_login"][bot_id] = status
        except Exception as e:
            result["xhs_login"]["_error"] = str(e)
    elif not mcp_status.get("xiaohongshu-mcp"):
        result["xhs_login"]["_error"] = "xiaohongshu-mcp 服务未运行，跳过登录检查"

    # === 输出 ===
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 文本报告
    print(f"========== Bot 巡检报告 ==========")
    print(f"时间：{now}")
    print()

    # MCP 服务
    print("【MCP 服务】")
    for svc, ok in mcp_status.items():
        icon = "✅" if ok else "❌"
        print(f"  {svc}: {icon}")
    print()

    # MCP 配置
    print("【Bot MCP 配置】")
    missing = [b for b in bots if not mcp_config.get(b, False)]
    if missing:
        for b in missing:
            name = ACTIVE_BOTS.get(b, b)
            print(f"  ❌ {b}({name}): 未配置 xiaohongshu-mcp")
    else:
        print(f"  ✅ 全部已配置")
    print()

    # 登录状态
    print("【小红书登录】")
    login_data = result["xhs_login"]
    if "_error" in login_data:
        print(f"  ⚠️  {login_data['_error']}")
    else:
        logged_in = []
        not_logged_in = []
        errors = []
        for bot_id in bots:
            status = login_data.get(bot_id, "unknown")
            name = ACTIVE_BOTS.get(bot_id, bot_id)
            if status == "logged_in":
                logged_in.append(f"{bot_id}({name})")
            elif status == "not_logged_in":
                not_logged_in.append(f"{bot_id}({name})")
            else:
                errors.append(f"{bot_id}({name}): {status}")

        if logged_in:
            print(f"  ✅ 已登录 ({len(logged_in)}): {', '.join(logged_in)}")
        if not_logged_in:
            print(f"  ❌ 未登录 ({len(not_logged_in)}): {', '.join(not_logged_in)}")
        if errors:
            for e in errors:
                print(f"  ⚠️  {e}")
    print()

    # 需要处理
    issues = []
    if not mcp_status.get("xiaohongshu-mcp"):
        issues.append("xiaohongshu-mcp 服务未运行，需要重启")
    if not mcp_status.get("finance-data"):
        issues.append("finance-data 服务未运行")
    if missing:
        issues.append(f"{', '.join(missing)} 未配置 xiaohongshu-mcp")
    not_logged = [b for b in bots if login_data.get(b) == "not_logged_in"]
    if not_logged:
        names = [f"{b}({ACTIVE_BOTS.get(b, b)})" for b in not_logged]
        issues.append(f"{', '.join(names)} 需要重新扫码登录小红书")

    if issues:
        print("【需要处理】")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("【状态】全部正常 ✅")

    print("=" * 34)


if __name__ == "__main__":
    main()
