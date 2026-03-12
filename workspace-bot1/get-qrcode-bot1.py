#!/usr/bin/env python3
import base64
import json
import requests

BASE_URL = "http://localhost:18061"

# 初始化 MCP Session
resp = requests.post(
    f"{BASE_URL}/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "get-qrcode", "version": "1.0"},
        },
    },
    timeout=15,
)
resp.raise_for_status()
session_id = resp.headers.get("Mcp-Session-Id")
print(f"Session ID: {session_id}")

# 调用 get_login_qrcode
resp = requests.post(
    f"{BASE_URL}/mcp",
    headers={"Mcp-Session-Id": session_id},
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "get_login_qrcode", "arguments": {"account_id": "bot1"}},
    },
    timeout=60,
)
resp.raise_for_status()
data = resp.json()
print(json.dumps(data, indent=2))

if "error" in data:
    print(f"Error: {data['error']}")
    exit(1)

result = data.get("result", {})
image_data = ""
for item in result.get("content", []):
    if item.get("type") == "image":
        image_data = item.get("data", "")
        break

if not image_data:
    print("No image data found")
    exit(1)

# 解码并保存
if "," in image_data and image_data.startswith("data:"):
    image_data = image_data.split(",", 1)[1]

raw = base64.b64decode(image_data)
output_path = "/home/rooot/.openclaw/media/xhs-qrcode-bot1.png"
with open(output_path, "wb") as f:
    f.write(raw)

print(f"QR code saved to: {output_path}")
