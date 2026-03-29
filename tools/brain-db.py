#!/usr/bin/env python3
"""
brain-db.py — Bot 记忆数据库 CLI 工具
用法:
  python3 tools/brain-db.py <bot_id> <command> [args...]

命令:
  add-research   --topic <topic> --category <cat> --content <content> [--sources <json>] [--confidence <0-1>] [--tags <json>]
  add-post       --title <title> --content <content> --status <status> [--post-type <type>] [--tags <json>] [--published-at <time>]
  add-event      --type <type> --title <title> [--detail <detail>] [--result <result>] [--severity <sev>]
  add-conversation --started-at <time> --summary <summary> [--session-id <id>] [--key-decisions <json>] [--directives <json>]
  add-long-term  --category <cat> --content <content> [--importance <1-10>] [--source <src>]
  query          --table <table> [--where <condition>] [--limit <n>] [--order <col>]
  recent         --table <table> [--days <n>] [--limit <n>]
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta


OPENCLAW_ROOT = "/home/rooot/.openclaw"


def get_db_path(bot_id: str) -> str:
    if bot_id.startswith("bot") and bot_id != "bot_main":
        workspace = f"workspace-{bot_id}"
    elif bot_id == "bot_main":
        workspace = "workspace-mag1"
    else:
        workspace = f"workspace-{bot_id}"
    path = os.path.join(OPENCLAW_ROOT, workspace, "memory", "brain.db")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    return path


def connect(bot_id: str) -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(bot_id))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def add_research(conn, args):
    c = conn.cursor()
    c.execute("""
        INSERT INTO research (topic, category, content, sources, confidence, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (args.topic, args.category, args.content, args.sources, args.confidence, args.tags))
    conn.commit()
    row_id = c.lastrowid
    print(json.dumps({"ok": True, "id": row_id, "table": "research"}, ensure_ascii=False))


def add_post(conn, args):
    c = conn.cursor()
    c.execute("""
        INSERT INTO posts (title, content, post_type, tags, status, visibility, published_at,
                           cover_description, persona_notes, engagement_hooks, continuity_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (args.title, args.content, args.post_type, args.tags, args.status,
          args.visibility, args.published_at, args.cover_description,
          args.persona_notes, args.engagement_hooks, args.continuity_notes))
    conn.commit()
    row_id = c.lastrowid
    print(json.dumps({"ok": True, "id": row_id, "table": "posts"}, ensure_ascii=False))


def add_event(conn, args):
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (event_type, severity, title, detail, result, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (args.type, args.severity, args.title, args.detail, args.result, args.metadata))
    conn.commit()
    row_id = c.lastrowid
    print(json.dumps({"ok": True, "id": row_id, "table": "events"}, ensure_ascii=False))


def add_conversation(conn, args):
    c = conn.cursor()
    c.execute("""
        INSERT INTO conversations (session_id, started_at, ended_at, summary, key_decisions, directives, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (args.session_id, args.started_at, args.ended_at, args.summary,
          args.key_decisions, args.directives, args.tags))
    conn.commit()
    row_id = c.lastrowid
    print(json.dumps({"ok": True, "id": row_id, "table": "conversations"}, ensure_ascii=False))


def add_long_term(conn, args):
    c = conn.cursor()
    c.execute("""
        INSERT INTO long_term (category, content, source, importance)
        VALUES (?, ?, ?, ?)
    """, (args.category, args.content, args.source, args.importance))
    conn.commit()
    row_id = c.lastrowid
    print(json.dumps({"ok": True, "id": row_id, "table": "long_term"}, ensure_ascii=False))


def query(conn, args):
    sql = f"SELECT * FROM {args.table}"
    params = []
    if args.where:
        sql += f" WHERE {args.where}"
    sql += f" ORDER BY {args.order} DESC"
    sql += f" LIMIT {args.limit}"
    c = conn.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def recent(conn, args):
    cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d %H:%M:%S")
    sql = f"SELECT * FROM {args.table} WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?"
    c = conn.execute(sql, (cutoff, args.limit))
    rows = [dict(r) for r in c.fetchall()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Bot Brain DB CLI")
    parser.add_argument("bot_id", help="e.g. bot10, bot5, bot_main")
    sub = parser.add_subparsers(dest="command", required=True)

    # add-research
    p = sub.add_parser("add-research")
    p.add_argument("--topic", required=True)
    p.add_argument("--category", default=None)
    p.add_argument("--content", required=True)
    p.add_argument("--sources", default=None)
    p.add_argument("--confidence", type=float, default=None)
    p.add_argument("--tags", default=None)

    # add-post
    p = sub.add_parser("add-post")
    p.add_argument("--title", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--post-type", default=None)
    p.add_argument("--tags", default=None)
    p.add_argument("--status", default="draft")
    p.add_argument("--visibility", default="public")
    p.add_argument("--published-at", default=None)
    p.add_argument("--cover-description", default=None)
    p.add_argument("--persona-notes", default=None)
    p.add_argument("--engagement-hooks", default=None)
    p.add_argument("--continuity-notes", default=None)

    # add-event
    p = sub.add_parser("add-event")
    p.add_argument("--type", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--detail", default=None)
    p.add_argument("--result", default=None)
    p.add_argument("--severity", default="info")
    p.add_argument("--metadata", default=None)

    # add-conversation
    p = sub.add_parser("add-conversation")
    p.add_argument("--session-id", default=None)
    p.add_argument("--started-at", required=True)
    p.add_argument("--ended-at", default=None)
    p.add_argument("--summary", required=True)
    p.add_argument("--key-decisions", default=None)
    p.add_argument("--directives", default=None)
    p.add_argument("--tags", default=None)

    # add-long-term
    p = sub.add_parser("add-long-term")
    p.add_argument("--category", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--source", default=None)
    p.add_argument("--importance", type=int, default=5)

    # query
    p = sub.add_parser("query")
    p.add_argument("--table", required=True)
    p.add_argument("--where", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--order", default="created_at")

    # recent
    p = sub.add_parser("recent")
    p.add_argument("--table", required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    conn = connect(args.bot_id)

    commands = {
        "add-research": add_research,
        "add-post": add_post,
        "add-event": add_event,
        "add-conversation": add_conversation,
        "add-long-term": add_long_term,
        "query": query,
        "recent": recent,
    }
    commands[args.command](conn, args)
    conn.close()


if __name__ == "__main__":
    main()
