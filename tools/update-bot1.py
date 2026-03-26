#!/usr/bin/env python3
"""更新 bot1 brain.db：导入 小红书发帖记录/ 目录"""
import sqlite3, os, re, json

OPENCLAW = "/home/rooot/.openclaw"
DB = os.path.join(OPENCLAW, "workspace-bot1/memory/brain.db")
POST_DIR = os.path.join(OPENCLAW, "workspace-bot1/memory/ 小红书发帖记录")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def parse_tags(text):
    tags = re.findall(r"#([\w\u4e00-\u9fff]+)", text)
    return json.dumps(tags, ensure_ascii=False) if tags else None

# 分类文件
files = [f for f in os.listdir(POST_DIR) if f.endswith(".md")]
files.sort()

post_count = 0
research_count = 0

for fname in files:
    path = os.path.join(POST_DIR, fname)
    content = read(path)
    date = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    date_str = date.group(1) if date else None

    if "帖子内容" in fname or "小红书帖子" in fname:
        # → posts 表：这是实际发布的帖子内容
        # 提取标题（第一个 # 开头行）
        title_m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else fname.replace(".md", "")
        tags = parse_tags(content)

        conn.execute(
            """INSERT INTO posts (title, content, post_type, tags, status, published_at, created_at)
               VALUES (?, ?, ?, ?, 'published', ?, COALESCE(?, datetime('now','localtime')))""",
            (title, content, "每日复盘", tags, date_str, f"{date_str} 00:00" if date_str else None)
        )
        post_count += 1
        print(f"  [post] {fname} → {title[:40]}")

    else:
        # → research 表：热点解读报告 / 雪球讨论整理
        title_m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        topic = title_m.group(1).strip() if title_m else fname.replace(".md", "")

        # 判断类型
        if "雪球" in content[:200] or "讨论" in fname:
            category = "雪球讨论"
        else:
            category = "热点解读"

        tags_list = ["每日复盘"]
        if date_str:
            tags_list.append(date_str)
        tags = json.dumps(tags_list, ensure_ascii=False)

        conn.execute(
            """INSERT INTO research (topic, category, content, tags, created_at)
               VALUES (?, ?, ?, ?, COALESCE(?, datetime('now','localtime')))""",
            (topic, category, content, tags, f"{date_str} 00:00" if date_str else None)
        )
        research_count += 1
        print(f"  [research/{category}] {fname} → {topic[:40]}")

conn.commit()

# 打印汇总
print(f"\n=== bot1 更新完成 ===")
for table in ["conversations", "posts", "research", "events", "long_term"]:
    c = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {c}")

print(f"\n  新增: posts +{post_count}, research +{research_count}")
size = os.path.getsize(DB)
print(f"  File size: {size/1024:.1f} KB")
conn.close()
