#!/usr/bin/env python3
import json
import subprocess

# 尝试不同的引号组合
attempts = [
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_book_info', 'book_id="3300192225"'],
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_book_info', "book_id=\"3300192225\""],
]

for i, cmd in enumerate(attempts):
    print(f"\n尝试 {i+1}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("stdout:", result.stdout[:500] if len(result.stdout) > 500 else result.stdout)
    if result.stderr:
        print("stderr:", result.stderr[:500] if len(result.stderr) > 500 else result.stderr)
