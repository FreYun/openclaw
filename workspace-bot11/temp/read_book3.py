#!/usr/bin/env python3
import json
import subprocess

# 尝试用不同的方式传递字符串参数
# 尝试在值周围加单引号
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_read_page', 
     "book_id='3300192225'", 'chapter_index=0'],
    capture_output=True,
    text=True
)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
