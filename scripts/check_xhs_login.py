#!/usr/bin/env python3
"""
检查所有 bot 的小红书登录状态。

用法:
  python3 check_xhs_login.py
  python3 check_xhs_login.py --url http://localhost:18060
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

DEFAULT_URL = "http://localhost:18060"
XHS_PROFILES_DIR = Path("/home/rooot/.xhs-profiles")
OPENCLAW_DIR = Path("/home/rooot/.openclaw")


def get_all_bots():
    """从 openclaw.json 读取所有 agent id，再加上 xhs-profiles 目录里的。"""
    bots = set()

    # 从 xhs-profiles 目录发现
    if XHS_PROFILES_DIR.exists():
        for p in XHS_PROFILES_DIR.iterdir():
            if p.is_dir() and not p.name.startswith(".") and p.name != "--json":
                bots.add(p.name)

    # 从 openclaw.json 发现
    config_path = OPENCLAW_DIR / "openclaw.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            for agent in data.get("agents", {}).get("list", []):
                if isinstance(agent, dict) and "id" in agent:
                    bots.add(agent["id"])
        except Exception:
            pass

    return sorted(bots)


def init_mcp_session(base_url: str) -> str:
    resp = requests.post(
        f"{base_url}/mcp",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "check_xhs_login", "version": "1.0"},
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    session_id = resp.headers.get("Mcp-Session-Id")
    if not session_id:
        raise RuntimeError("服务器未返回 Mcp-Session-Id")
    return session_id


def check_login(base_url: str, session_id: str, bot_id: str) -> str:
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
        return f"❌ 错误: {data['error']}"
    for item in data.get("result", {}).get("content", []):
        text = item.get("text", "")
        if "已登录" in text:
            return "✅ 已登录"
        if "未登录" in text:
            return "❌ 未登录"
    return "⚠️  状态未知"


def main():
    parser = argparse.ArgumentParser(description="检查所有 bot 的小红书登录状态")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"MCP 服务地址 (默认: {DEFAULT_URL})")
    parser.add_argument("--bots", nargs="+", help="指定要检查的 bot（不填则自动发现所有）")
    args = parser.parse_args()

    # 检查服务是否在线
    try:
        r = requests.get(f"{args.url}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ 服务不可用 ({args.url}): {e}", file=sys.stderr)
        sys.exit(1)

    bots = args.bots if args.bots else get_all_bots()
    if not bots:
        print("未发现任何 bot")
        return

    print(f"{'Bot':<12} 状态")
    print("-" * 25)

    try:
        session_id = init_mcp_session(args.url)
    except Exception as e:
        print(f"初始化 MCP session 失败: {e}", file=sys.stderr)
        sys.exit(1)

    logged_in, not_logged_in = [], []
    for bot in bots:
        try:
            status = check_login(args.url, session_id, bot)
        except Exception as e:
            status = f"⚠️  请求失败: {e}"
        print(f"{bot:<12} {status}")
        if "已登录" in status:
            logged_in.append(bot)
        else:
            not_logged_in.append(bot)

    print("-" * 25)
    print(f"已登录: {len(logged_in)}  未登录: {len(not_logged_in)}")
    if not_logged_in:
        print(f"需要扫码: {', '.join(not_logged_in)}")


if __name__ == "__main__":
    main()
