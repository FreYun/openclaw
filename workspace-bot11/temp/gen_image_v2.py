#!/usr/bin/env python3
import requests
import json
import time

# MCP endpoint
url = "http://localhost:18085/mcp"

# Step 1: Initialize to get session ID
init_payload = {
    "jsonrpc": "2.0",
    "id": str(int(time.time())),
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

# Get session ID from response headers
response = requests.post(url, json=init_payload, headers=headers, timeout=30)
session_id = response.headers.get('Mcp-Session-Id')
print(f"Session ID: {session_id}")

# Now make the tool call with session ID
tool_payload = {
    "jsonrpc": "2.0",
    "id": str(int(time.time())),
    "method": "tools/call",
    "params": {
        "name": "generate_image",
        "arguments": {
            "style": "hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, deep indigo accent highlights, aerospace palette (cream, navy blue, silver gray, warm brown, star white), deep analysis cover, centered hero illustration layout",
            "content": "Central illustration of Persian Gulf map top-down view, Strait of Hormuz marked with red warning frame, three opposing silhouettes on map: missile launchers and warships on east side, fighter jet formations on west side, blocked strait with oil tanker silhouettes in middle, conflict flames and smoke lines in background, occupying 60% of frame, large bold black Chinese title above illustration: Middle East Situation | War Spreading Multi-party Conflict, small subtitle below: Strait of Hormuz Becomes Focus of Game Gulf States Change Attitude, two floating label cards on each side of illustration (left side: Houthis Join War, Bush Carrier Deployed, right side: Gulf Six Nations Joint Statement, Iran Blockades Strait), bottom decorative line only",
            "size": "1536x1024",
            "model": "banana2",
            "workspace": "/home/rooot/.openclaw/workspace-bot11"
        }
    }
}

headers_with_session = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id
}

response2 = requests.post(url, json=tool_payload, headers=headers_with_session, timeout=300, stream=True)
print(f"Status: {response2.status_code}")

# Handle SSE stream
for line in response2.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            data_str = decoded[6:]
            try:
                data = json.loads(data_str)
                print(json.dumps(data, indent=2, ensure_ascii=False))
                if 'result' in data:
                    break
            except:
                print(decoded)
