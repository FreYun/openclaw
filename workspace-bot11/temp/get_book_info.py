#!/usr/bin/env python3
import json
import subprocess

# 调用 weread_book_info 获取书籍详情和目录
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_book_info', 
     "book_id='3300192225'"],
    capture_output=True,
    text=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
