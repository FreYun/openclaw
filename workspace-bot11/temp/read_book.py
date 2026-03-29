#!/usr/bin/env python3
import json
import subprocess

# 调用 weread-mcp 的 weread_read_page 工具
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_read_page', 
     '--data', json.dumps({"book_id": "3300192225", "chapter_index": 0})],
    capture_output=True,
    text=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
