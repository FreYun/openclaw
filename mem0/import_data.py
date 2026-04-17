#!/usr/bin/env python3
"""OpenClaw 数据导入 mem0

用法:
  python import_data.py --source research --bot all     # 导入所有 research 文件
  python import_data.py --source sessions --bot bot7    # 导入 bot7 的 session
  python import_data.py --source sessions --bot all     # 导入所有 bot 的 session
  python import_data.py --source all --bot all          # 全部导入
"""

import argparse
import glob
import json
import logging
import os
import re
import sys
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MEM0_URL = "http://localhost:18095"
OPENCLAW_DIR = "/home/rooot/.openclaw"
AGENTS_DIR = os.path.join(OPENCLAW_DIR, "agents")
PROGRESS_FILE = os.path.join(OPENCLAW_DIR, "mem0", "import_progress.json")

# 导入间隔（秒），避免打爆 API
ADD_DELAY = 0.3


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"sessions": {}, "research": {}}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def mem0_add(messages, user_id, agent_id, run_id=None, infer=True, metadata=None):
    """调用 mem0 REST API 添加记忆"""
    payload = {
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "user_id": user_id,
        "agent_id": agent_id,
        "infer": infer,
    }
    if run_id:
        payload["run_id"] = run_id
    if metadata:
        payload["metadata"] = metadata

    for attempt in range(3):
        try:
            r = requests.post(f"{MEM0_URL}/memories", json=payload, timeout=120)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    return None


# ============================================================
# Session 导入
# ============================================================

def clean_user_message(text):
    """清洗 user 消息中的系统前缀"""
    # 去掉 Skill-first 前缀
    text = re.sub(r'^⚡ Skill-first.*?\n\n', '', text, flags=re.DOTALL)
    # 提取飞书 DM 的实际内容
    m = re.search(r'(?:DM from \S+:|Group message:)\s*(.*)', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # 去掉 Conversation info 块
    text = re.sub(r'\nConversation info.*$', '', text, flags=re.DOTALL)
    # 去掉 message_id 行
    text = re.sub(r'\[message_id:.*?\]\n?', '', text)
    # 去掉发送者前缀（如 "顾云峰: "）
    text = re.sub(r'^[\u4e00-\u9fff\w]+:\s*', '', text)
    return text.strip()


def clean_assistant_message(text):
    """清洗 assistant 消息"""
    text = text.replace("[[reply_to_current]]", "").strip()
    return text


def parse_session(jsonl_path):
    """解析 session JSONL，返回清洗后的消息列表"""
    messages = []
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("type") != "message":
                    continue
                msg = record.get("message", {})
                role = msg.get("role")
                if role not in ("user", "assistant"):
                    continue

                # 只取 text 类型内容
                texts = []
                for c in msg.get("content", []):
                    if c.get("type") == "text":
                        texts.append(c["text"])

                if not texts:
                    continue
                text = "\n".join(texts)

                # 过滤噪音
                if len(text) < 30:
                    continue
                if text.startswith("data:image/"):
                    continue
                if "Exec completed" in text and len(text) < 200:
                    continue
                # 跳过 base64 数据块
                if "base64," in text and len(text) > 5000:
                    continue
                # 跳过纯心跳/状态消息
                if re.match(r'^(HEARTBEAT_OK|/status|/help)\s*$', text.strip()):
                    continue

                # 清洗
                if role == "user":
                    text = clean_user_message(text)
                else:
                    text = clean_assistant_message(text)

                if len(text) < 20:
                    continue

                messages.append({"role": role, "content": text})
    except Exception as e:
        logger.error(f"Error parsing {jsonl_path}: {e}")

    return messages


def extract_bot_id(path):
    """从路径提取 bot ID"""
    m = re.search(r'agents/(bot\d+)/', path)
    return m.group(1) if m else None


def extract_session_id(path):
    """从文件名提取 session ID"""
    basename = os.path.basename(path)
    return basename.replace(".jsonl", "")


def import_sessions(bot_filter="all"):
    """导入 session 历史"""
    progress = load_progress()
    pattern = os.path.join(AGENTS_DIR, "bot*/sessions/*.jsonl")
    files = sorted(glob.glob(pattern))
    logger.info(f"Found {len(files)} session files")

    total_added = 0
    total_skipped = 0

    for filepath in files:
        bot_id = extract_bot_id(filepath)
        if not bot_id:
            continue
        if bot_filter != "all" and bot_id != bot_filter:
            continue

        session_id = extract_session_id(filepath)
        progress_key = f"{bot_id}/{session_id}"

        if progress_key in progress.get("sessions", {}):
            total_skipped += 1
            continue

        # 跳过太小的文件
        if os.path.getsize(filepath) < 500:
            continue

        messages = parse_session(filepath)
        if not messages:
            progress.setdefault("sessions", {})[progress_key] = {"status": "empty", "count": 0}
            save_progress(progress)
            continue

        logger.info(f"[{bot_id}] Session {session_id}: {len(messages)} messages")

        # 分 batch 导入，每 10 条一组
        batch_size = 10
        session_facts = 0
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            result = mem0_add(
                messages=batch,
                user_id="研究部",
                agent_id=bot_id,
                run_id=session_id,
                infer=True,
            )
            if result and result.get("results"):
                n = len(result["results"])
                session_facts += n
                total_added += n
                logger.info(f"  Batch {i // batch_size + 1}: extracted {n} facts")
            time.sleep(ADD_DELAY)

        progress.setdefault("sessions", {})[progress_key] = {
            "status": "done",
            "messages": len(messages),
            "facts": session_facts,
        }
        save_progress(progress)

    logger.info(f"Sessions import done: {total_added} facts added, {total_skipped} files skipped")


# ============================================================
# Research 文件导入
# ============================================================

def split_markdown_by_section(content, max_chars=4000):
    """按 ## 标题切分 Markdown，每段不超过 max_chars"""
    sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > max_chars and current:
            chunks.append(current.strip())
            current = section
        else:
            current += section
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [content]


def import_research(bot_filter="all"):
    """导入 research 文件"""
    progress = load_progress()
    pattern = os.path.join(OPENCLAW_DIR, "workspace-bot*/memory/research/*.md")
    files = sorted(glob.glob(pattern))
    logger.info(f"Found {len(files)} research files")

    total_added = 0

    for filepath in files:
        m = re.search(r'workspace-(bot\d+)/', filepath)
        if not m:
            continue
        bot_id = m.group(1)
        if bot_filter != "all" and bot_id != bot_filter:
            continue

        filename = os.path.basename(filepath)
        progress_key = f"{bot_id}/{filename}"

        if progress_key in progress.get("research", {}):
            logger.info(f"  Skipping {progress_key} (already imported)")
            continue

        with open(filepath, "r") as f:
            content = f.read()

        if len(content) < 50:
            continue

        # 提取日期
        date_match = re.search(r'(\d{4}-?\d{2}-?\d{2})', filename)
        date_str = date_match.group(1) if date_match else None

        chunks = split_markdown_by_section(content)
        logger.info(f"[{bot_id}] Research {filename}: {len(content)} chars, {len(chunks)} chunks")

        chunk_added = 0
        for j, chunk in enumerate(chunks):
            result = mem0_add(
                messages=[{"role": "user", "content": chunk}],
                user_id="研究部",
                agent_id=bot_id,
                infer=False,
                metadata={
                    "source": "research",
                    "filename": filename,
                    "date": date_str,
                },
            )
            if result and result.get("results"):
                chunk_added += len(result["results"])
            time.sleep(ADD_DELAY)

        total_added += chunk_added
        progress.setdefault("research", {})[progress_key] = {
            "status": "done",
            "chunks": len(chunks),
            "added": chunk_added,
        }
        save_progress(progress)

    logger.info(f"Research import done: {total_added} entries added")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Import OpenClaw data into mem0")
    parser.add_argument("--source", choices=["sessions", "research", "all"], default="all")
    parser.add_argument("--bot", default="all", help="Bot ID (e.g. bot7) or 'all'")
    args = parser.parse_args()

    # 健康检查
    try:
        r = requests.get(f"{MEM0_URL}/health", timeout=5)
        r.raise_for_status()
        logger.info(f"mem0 server OK: {r.json()}")
    except Exception as e:
        logger.error(f"mem0 server not reachable at {MEM0_URL}: {e}")
        sys.exit(1)

    if args.source in ("research", "all"):
        import_research(args.bot)

    if args.source in ("sessions", "all"):
        import_sessions(args.bot)


if __name__ == "__main__":
    main()
