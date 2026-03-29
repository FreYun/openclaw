#!/usr/bin/env python3
import json
import subprocess

# 调用 weread_read_page
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_read_page', 
     "book_id='3300192225'", 'chapter_index=0'],
    capture_output=True,
    text=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)

# 如果成功，解析结果
try:
    data = json.loads(result.stdout)
    if 'screenshotPath' in data:
        print(f"\n截图路径: {data['screenshotPath']}")
        print(f"章节标题: {data.get('chapterTitle', 'N/A')}")
except:
    pass
