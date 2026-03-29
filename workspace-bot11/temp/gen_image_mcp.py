#!/usr/bin/env python3
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def generate():
    async with streamable_http_client("http://localhost:18085/mcp") as client:
        async with ClientSession(client) as session:
            await session.initialize()
            
            # Call generate_image tool
            result = await session.call_tool("generate_image", {
                "style": "hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, deep indigo accent highlights, aerospace palette (cream, navy blue, silver gray, warm brown, star white), deep analysis cover, centered hero illustration layout",
                "content": "Central illustration of Persian Gulf map top-down view, Strait of Hormuz marked with red warning frame, three opposing silhouettes on map: missile launchers and warships on east side, fighter jet formations on west side, blocked strait with oil tanker silhouettes in middle, conflict flames and smoke lines in background, occupying 60% of frame, large bold black Chinese title above illustration: Middle East Situation Deep Analysis | War Spreading Multi-party Conflict, small subtitle below: Strait of Hormuz Becomes Focus of Game Gulf States Change Attitude, two floating label cards on each side of illustration (left side: Houthis Join War, Bush Carrier Deployed, right side: Gulf Six Nations Joint Statement, Iran Blockades Strait), decorative line and small text 2026-03-28 at bottom",
                "size": "1536x1024",
                "model": "banana2"
            })
            
            print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(generate())
