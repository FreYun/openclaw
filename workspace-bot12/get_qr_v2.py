#!/usr/bin/env python3
"""
使用 Streamable HTTP 方式调用 MCP 工具
"""
import json
import requests
import time

MCP_URL = "http://localhost:18072/mcp"

def main():
    session = requests.Session()
    
    # 使用 streamable HTTP 方式
    # 发送初始化请求
    init_id = int(time.time() * 1000)
    init_payload = {
        "jsonrpc": "2.0",
        "id": init_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True}
            },
            "clientInfo": {"name": "bot12", "version": "1.0"}
        }
    }
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    # 初始化
    response = session.post(MCP_URL, json=init_payload, headers=headers)
    init_result = response.json()
    print("初始化结果:", json.dumps(init_result, indent=2, ensure_ascii=False))
    
    # 发送 initialized 通知
    session.post(MCP_URL, json={
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }, headers=headers)
    
    # 直接调用工具（不使用 tools/call 方法，直接 POST 到工具端点）
    call_id = init_id + 1
    tool_payload = {
        "jsonrpc": "2.0",
        "id": call_id,
        "method": "tools/call",
        "params": {
            "name": "get_both_login_qrcodes",
            "arguments": {}
        }
    }
    
    response = session.post(MCP_URL, json=tool_payload, headers=headers, timeout=60)
    result = response.json()
    print("\n获取二维码结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 如果有图片数据，保存
    if "result" in result and "content" in result["result"]:
        for item in result["result"]["content"]:
            if item.get("type") == "image":
                import base64
                data = item.get("data", "")
                if data.startswith("data:image"):
                    data = data.split(",")[1]
                img_data = base64.b64decode(data)
                filename = item.get("name", f"qr-{int(time.time())}.png")
                with open(f"/home/rooot/.openclaw/media/{filename}", "wb") as f:
                    f.write(img_data)
                print(f"\n已保存图片: /home/rooot/.openclaw/media/{filename}")

if __name__ == "__main__":
    main()
