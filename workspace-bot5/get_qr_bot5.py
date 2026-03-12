#!/usr/bin/env python3
"""获取 bot5 的登录二维码"""
import requests
import base64

BASE_URL = "http://localhost:18060"

# 1. 初始化 session
resp = requests.post(f"{BASE_URL}/mcp", json={
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "get_qr", "version": "1.0"},
    }
}, timeout=15)
session_id = resp.headers.get("Mcp-Session-Id")
print(f"Session ID: {session_id}")

# 2. 检查登录状态
resp = requests.post(f"{BASE_URL}/mcp", headers={"Mcp-Session-Id": session_id}, json={
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "check_login_status", "arguments": {"account_id": "bot5"}}
}, timeout=30)
print("登录状态:", resp.json())

# 3. 获取二维码
resp = requests.post(f"{BASE_URL}/mcp", headers={"Mcp-Session-Id": session_id}, json={
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {"name": "get_login_qrcode", "arguments": {"account_id": "bot5"}}
}, timeout=60)
result = resp.json()
print("二维码结果:", result)

# 4. 保存图片
for item in result.get("result", {}).get("content", []):
    if item.get("type") == "image":
        img_data = item.get("data", "")
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]
        with open("/home/rooot/.openclaw/workspace-bot5/xhs-qrcode-bot5.png", "wb") as f:
            f.write(base64.b64decode(img_data))
        print("二维码已保存到 /home/rooot/.openclaw/workspace-bot5/xhs-qrcode-bot5.png")
        break
