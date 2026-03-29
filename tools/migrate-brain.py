#!/usr/bin/env python3
"""
migrate-brain.py — 为 bot1/bot2/bot4 创建 brain.db 并导入现有 MD 内容
"""

import sqlite3
import os
import re
import json
from datetime import datetime

OPENCLAW = "/home/rooot/.openclaw"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT NOT NULL,
    key_decisions TEXT,
    directives TEXT,
    mood TEXT,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL DEFAULT 'xiaohongshu',
    post_id TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    post_type TEXT,
    tags TEXT,
    cover_description TEXT,
    images TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    visibility TEXT DEFAULT 'public',
    persona_notes TEXT,
    engagement_hooks TEXT,
    continuity_notes TEXT,
    published_at TEXT,
    metrics TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    sources TEXT,
    confidence REAL,
    status TEXT DEFAULT 'active',
    related_post_id INTEGER,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (related_post_id) REFERENCES posts(id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    title TEXT NOT NULL,
    detail TEXT,
    result TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS long_term (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    importance INTEGER DEFAULT 5,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations(started_at);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_at);
CREATE INDEX IF NOT EXISTS idx_research_category ON research(category);
CREATE INDEX IF NOT EXISTS idx_research_topic ON research(topic);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
CREATE INDEX IF NOT EXISTS idx_long_term_category ON long_term(category);
CREATE INDEX IF NOT EXISTS idx_long_term_active ON long_term(is_active);
"""


def create_db(bot_id, bot_name):
    if bot_id == "bot_main":
        ws = "workspace-mag1"
    else:
        ws = f"workspace-{bot_id}"
    db_path = os.path.join(OPENCLAW, ws, "memory", "brain.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        print(f"  [skip] {db_path} already exists")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, db_path

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '1.0')")
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('bot_id', ?)", (bot_id,))
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('bot_name', ?)", (bot_name,))
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('created_at', datetime('now', 'localtime'))")
    conn.commit()
    print(f"  [created] {db_path}")
    return conn, db_path


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None


def extract_date_from_filename(fname):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    return m.group(1) if m else None


def parse_tags_from_text(text):
    """Extract #tag patterns from text"""
    tags = re.findall(r"#([\w\u4e00-\u9fff]+)", text)
    return json.dumps(tags, ensure_ascii=False) if tags else None


def parse_metrics_from_text(text):
    """Extract 浏览/点赞/收藏/评论/分享 from post records"""
    metrics = {}
    patterns = {
        "views": r"浏览量[：:]\s*\*{0,2}(\d+)",
        "likes": r"点赞数[：:]\s*\*{0,2}(\d+)",
        "collects": r"收藏数[：:]\s*\*{0,2}(\d+)",
        "comments": r"评论数[：:]\s*\*{0,2}(\d+)",
        "shares": r"分享数[：:]\s*\*{0,2}(\d+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            metrics[key] = int(m.group(1))
    return json.dumps(metrics, ensure_ascii=False) if metrics else None


def parse_post_status(text):
    if "发布成功" in text or "已发布" in text:
        return "published"
    if "待发布" in text or "等待" in text:
        return "pending"
    if "审核未通过" in text:
        return "rejected"
    return "draft"


def parse_published_at(text, date_str):
    # Try to find explicit publish time
    m = re.search(r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{2}:\d{2})\s*发布", text)
    if m and date_str:
        return f"{date_str} {m.group(1)}"
    if date_str and ("发布成功" in text or "已发布" in text):
        return date_str
    return None


# ============================================================
# Bot1: 来财妹妹
# ============================================================
def migrate_bot1(conn):
    ws = os.path.join(OPENCLAW, "workspace-bot1")

    # 1. Conversations from diary/
    diary_dir = os.path.join(ws, "memory", "diary")
    count = 0
    for fname in sorted(os.listdir(diary_dir)):
        if not fname.endswith(".md"):
            continue
        date = extract_date_from_filename(fname)
        if not date:
            continue
        content = read_file(os.path.join(diary_dir, fname))
        if not content or "无记录" in content[:50]:
            continue
        conn.execute(
            "INSERT INTO conversations (started_at, summary, tags) VALUES (?, ?, ?)",
            (f"{date} 00:00", content, json.dumps(["日记"], ensure_ascii=False))
        )
        count += 1
    print(f"  conversations: {count} diary entries")

    # 2. Long-term memory from MEMORY.md
    memory_content = read_file(os.path.join(ws, "MEMORY.md"))
    if memory_content and "暂无" not in memory_content[:50]:
        conn.execute(
            "INSERT INTO long_term (category, content, source, importance) VALUES (?, ?, ?, ?)",
            ("工具规范", memory_content, "MEMORY.md", 8)
        )
        print(f"  long_term: 1 (MEMORY.md)")

    # 3. Long-term from xiaohongshu/ reference docs
    xhs_dir = os.path.join(ws, "memory", "xiaohongshu")
    lt_count = 0
    if os.path.isdir(xhs_dir):
        for fname in os.listdir(xhs_dir):
            if not fname.endswith(".md"):
                continue
            content = read_file(os.path.join(xhs_dir, fname))
            if not content:
                continue
            conn.execute(
                "INSERT INTO long_term (category, content, source, importance) VALUES (?, ?, ?, ?)",
                ("小红书运营", content, f"xiaohongshu/{fname}", 7)
            )
            lt_count += 1
    print(f"  long_term: +{lt_count} (xiaohongshu ops)")

    conn.commit()


# ============================================================
# Bot2: 狗哥说财
# ============================================================
def migrate_bot2(conn):
    ws = os.path.join(OPENCLAW, "workspace-bot2")
    mem = os.path.join(ws, "memory")

    # 1. Conversations from diary files
    conv_count = 0
    for fname in sorted(os.listdir(mem)):
        if not fname.endswith(".md"):
            continue
        date = extract_date_from_filename(fname)
        if not date:
            continue
        content = read_file(os.path.join(mem, fname))
        if not content or "暂无" in content[:50]:
            continue
        conn.execute(
            "INSERT INTO conversations (started_at, summary, tags) VALUES (?, ?, ?)",
            (f"{date} 00:00", content, json.dumps(["日记", "研究"], ensure_ascii=False))
        )
        conv_count += 1
    print(f"  conversations: {conv_count} diary entries")

    # 2. Posts from drafts/
    drafts_dir = os.path.join(mem, "drafts")
    post_count = 0
    if os.path.isdir(drafts_dir):
        for fname in sorted(os.listdir(drafts_dir)):
            if not fname.endswith(".md"):
                continue
            content = read_file(os.path.join(drafts_dir, fname))
            if not content:
                continue
            # Extract title
            title_m = re.search(r"##\s*标题.*?\n+(.+?)(?:\n|$)", content)
            title = title_m.group(1).strip() if title_m else fname.replace(".md", "")
            tags = parse_tags_from_text(content)
            status = parse_post_status(content)

            conn.execute(
                "INSERT INTO posts (title, content, post_type, tags, status) VALUES (?, ?, ?, ?, ?)",
                (title, content, "产业链拆解", tags, status)
            )
            post_count += 1
    print(f"  posts: {post_count} drafts")

    # 3. Research from research/
    research_dir = os.path.join(mem, "research")
    res_count = 0
    if os.path.isdir(research_dir):
        for fname in sorted(os.listdir(research_dir)):
            if not fname.endswith(".md"):
                continue
            content = read_file(os.path.join(research_dir, fname))
            if not content:
                continue
            topic = fname.replace(".md", "")
            conn.execute(
                "INSERT INTO research (topic, category, content, tags) VALUES (?, ?, ?, ?)",
                (topic, "研究方法论", content, json.dumps(["流程", "方法论"], ensure_ascii=False))
            )
            res_count += 1
    print(f"  research: {res_count}")

    conn.commit()


# ============================================================
# Bot4: 研报搬运工阿泽
# ============================================================
def migrate_bot4(conn):
    ws = os.path.join(OPENCLAW, "workspace-bot4")
    mem = os.path.join(ws, "memory")

    # 1. Conversations from diary/ + root-level date md
    conv_count = 0
    # Root level dated files
    for fname in sorted(os.listdir(mem)):
        fpath = os.path.join(mem, fname)
        if not fname.endswith(".md") or not os.path.isfile(fpath):
            continue
        date = extract_date_from_filename(fname)
        if not date:
            continue
        content = read_file(fpath)
        if not content or "无记录" in content[:50]:
            continue
        conn.execute(
            "INSERT INTO conversations (started_at, summary, tags) VALUES (?, ?, ?)",
            (f"{date} 00:00", content, json.dumps(["日记"], ensure_ascii=False))
        )
        conv_count += 1

    # diary/ subdirectory
    diary_dir = os.path.join(mem, "diary")
    if os.path.isdir(diary_dir):
        for fname in sorted(os.listdir(diary_dir)):
            if not fname.endswith(".md"):
                continue
            date = extract_date_from_filename(fname)
            if not date:
                continue
            content = read_file(os.path.join(diary_dir, fname))
            if not content or "无记录" in content[:50] or "本日无记录" in content:
                continue
            conn.execute(
                "INSERT INTO conversations (started_at, summary, tags) VALUES (?, ?, ?)",
                (f"{date} 00:00", content, json.dumps(["日记"], ensure_ascii=False))
            )
            conv_count += 1
    print(f"  conversations: {conv_count} diary entries")

    # 2. Research from 研报解读/
    research_dir = os.path.join(mem, "研报解读")
    res_count = 0
    research_topics = {}  # topic -> research_id, for linking posts
    if os.path.isdir(research_dir):
        for fname in sorted(os.listdir(research_dir)):
            if not fname.endswith(".md"):
                continue
            content = read_file(os.path.join(research_dir, fname))
            if not content:
                continue

            # Parse topic from filename: 2026-03-13-化工行业.md -> 化工行业
            date = extract_date_from_filename(fname)
            topic_m = re.match(r"\d{4}-\d{2}-\d{2}[- ](.+)\.md", fname)
            topic = topic_m.group(1) if topic_m else fname.replace(".md", "")

            # Parse sources from content
            source_m = re.search(r"研报来源[：:]\s*(.+?)(?:\n|$)", content)
            sources = source_m.group(1).strip() if source_m else None

            tags_list = ["研报解读"]
            if date:
                tags_list.append(date)
            tags = json.dumps(tags_list, ensure_ascii=False)

            created = f"{date} 00:00" if date else None

            cursor = conn.execute(
                "INSERT INTO research (topic, category, content, sources, tags, created_at) VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now', 'localtime')))",
                (topic, "研报解读", content, json.dumps([sources], ensure_ascii=False) if sources else None, tags, created)
            )
            research_topics[topic] = cursor.lastrowid
            res_count += 1
    print(f"  research: {res_count} 研报解读")

    # 3. Posts from 发帖记录/
    post_dir = os.path.join(mem, "发帖记录")
    post_count = 0
    if os.path.isdir(post_dir):
        for fname in sorted(os.listdir(post_dir)):
            if not fname.endswith(".md"):
                continue
            content = read_file(os.path.join(post_dir, fname))
            if not content:
                continue

            date = extract_date_from_filename(fname)

            # Parse title
            title_m = re.search(r"\*{0,2}标题[：:]\*{0,2}\s*(.+?)(?:\n|$)", content)
            title = title_m.group(1).strip() if title_m else fname.replace(".md", "")

            # Parse type
            type_m = re.search(r"发布形式[：:]\s*(.+?)(?:\n|$)", content)
            post_type = type_m.group(1).strip() if type_m else None

            tags = parse_tags_from_text(content)
            status = parse_post_status(content)
            published_at = parse_published_at(content, date)
            metrics = parse_metrics_from_text(content)

            created = f"{date} 00:00" if date else None

            cursor = conn.execute(
                """INSERT INTO posts (title, content, post_type, tags, status, published_at, metrics, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now', 'localtime')))""",
                (title, content, post_type, tags, status, published_at, metrics, created)
            )
            post_id = cursor.lastrowid

            # Link research to post if topic matches
            topic_m = re.match(r"\d{4}-\d{2}-\d{2}[- ](.+)\.md", fname)
            if topic_m:
                topic_key = topic_m.group(1)
                # Try to find matching research
                for rtopic, rid in research_topics.items():
                    if topic_key in rtopic or rtopic in topic_key:
                        conn.execute(
                            "UPDATE research SET related_post_id = ? WHERE id = ?",
                            (post_id, rid)
                        )
                        break

            post_count += 1
    print(f"  posts: {post_count} 发帖记录")

    conn.commit()


# ============================================================
# Main
# ============================================================
def main():
    bots = [
        ("bot1", "来财妹妹", migrate_bot1),
        ("bot2", "狗哥说财", migrate_bot2),
        ("bot4", "研报搬运工阿泽", migrate_bot4),
    ]

    for bot_id, bot_name, migrate_fn in bots:
        print(f"\n=== {bot_id} ({bot_name}) ===")
        conn, db_path = create_db(bot_id, bot_name)

        # Check if already has data
        existing = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        if existing > 0:
            print(f"  [skip migration] already has {existing} conversations")
            conn.close()
            continue

        migrate_fn(conn)

        # Print summary
        for table in ["conversations", "posts", "research", "events", "long_term"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count > 0:
                print(f"  TOTAL {table}: {count}")

        size = os.path.getsize(db_path)
        print(f"  File size: {size/1024:.1f} KB")
        conn.close()


if __name__ == "__main__":
    main()
