#!/usr/bin/env python3
import json
import subprocess

# 直接调用 weread-mcp 的 weread_read_page 工具
# 根据之前成功的 weread_search 调用方式
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_read_page', 
     'book_id=3300192225', 'chapter_index=0'],
    capture_output=True,
    text=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
