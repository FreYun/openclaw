#!/usr/bin/env python3
import json
import urllib.request
import urllib.error

# MCP server endpoint
url = "http://localhost:18085/mcp/tools/call"

# Request payload
payload = {
    "name": "generate_image",
    "arguments": {
        "style": "hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, deep indigo accent highlights, aerospace palette (cream, navy blue, silver gray, warm brown, star white), deep analysis cover, centered hero illustration layout",
        "content": "Central illustration of Persian Gulf map top-down view, Strait of Hormuz marked with red warning frame, three opposing silhouettes on map: missile launchers and warships on east side, fighter jet formations on west side, blocked strait with oil tanker silhouettes in middle, conflict flames and smoke lines in background, occupying 60% of frame, large bold black Chinese title above illustration: Middle East Situation Deep Analysis | War Spreading Multi-party Conflict, small subtitle below: Strait of Hormuz Becomes Focus of Game Gulf States Change Attitude, two floating label cards on each side of illustration (left side: Houthis Join War, Bush Carrier Deployed, right side: Gulf Six Nations Joint Statement, Iran Blockades Strait), decorative line and small text 2026-03-28 at bottom",
        "size": "1536x1024",
        "model": "banana2"
    }
}

# Send request
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
