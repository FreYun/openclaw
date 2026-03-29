#!/usr/bin/env python3
import json
import subprocess

# 获取书架列表
result = subprocess.run(
    ['npx', 'mcporter', 'call', 'weread-mcp', 'weread_shelf'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
# 查找特定书籍
target_book_id = '3300192225'
found = False
for book in data.get('books', []):
    if str(book.get('bookId')) == target_book_id:
        print(f"找到书籍: {book.get('title')}")
        print(f"bookId: {book.get('bookId')}")
        print(json.dumps(book, indent=2, ensure_ascii=False))
        found = True
        break

if not found:
    print(f"未在书架中找到 bookId={target_book_id} 的书籍")
    print(f"书架上共有 {len(data.get('books', []))} 本书")
    print("书架书籍列表:")
    for book in data.get('books', []):
        print(f"  - {book.get('title')} (bookId: {book.get('bookId')})")
