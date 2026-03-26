#!/usr/bin/env python3
"""
调用小红书 MCP 工具获取登录二维码
"""
import json
import requests
import time

MCP_URL = "http://localhost:18072/mcp"

def main():
    session = requests.Session()
    
    # 1. 初始化
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bot12", "version": "1.0"}
        }
    }
    response = session.post(MCP_URL, json=init_payload, headers={"Content-Type": "application/json"})
    print("初始化结果:", response.json())
    
    # 2. 发送 initialized 通知
    notify_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    session.post(MCP_URL, json=notify_payload, headers={"Content-Type": "application/json"})
    time.sleep(0.5)  # 等待一下
    
    # 3. 列出工具
    list_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    response = session.post(MCP_URL, json=list_payload, headers={"Content-Type": "application/json"})
    print("\n工具列表:", json.dumps(response.json(), indent=2, ensure_ascii=False)[:500])
    
    # 4. 调用获取二维码工具
    call_payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "xiaohongshu-mcp.get_both_login_qrcodes",
            "arguments": {}
        }
    }
    response = session.post(MCP_URL, json=call_payload, headers={"Content-Type": "application/json"})
    result = response.json()
    print("\n获取二维码结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 如果有结果，保存图片
    if "result" in result and "content" in result["result"]:
        for item in result["result"]["content"]:
            if item.get("type") == "image":
                # 保存 base64 图片
                import base64
                data = item.get("data", "")
                if data.startswith("data:image"):
                    data = data.split(",")[1]
                img_data = base64.b64decode(data)
                filename = item.get("name", "qrcode.png")
                with open(f"/home/rooot/.openclaw/media/{filename}", "wb") as f:
                    f.write(img_data)
                print(f"\n已保存图片: {filename}")

if __name__ == "__main__":
    main()
