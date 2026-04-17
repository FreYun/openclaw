#!/usr/bin/env python3
"""快速导入 OpenClaw session 到 mem0

优化策略：
1. 先用 GLM-5 一次性从整个 session 提取事实（1 次 LLM 调用/session）
2. 用 infer=False 直接存向量（只做 embedding，跳过去重 LLM）
3. 多线程并发 embedding 存储

对比原版：原来每 10 条消息要 2 次 LLM 调用（提取 + 去重），现在整个 session 只要 1 次。

用法:
  python import_fast.py --bot all          # 导入所有 bot
  python import_fast.py --bot bot7         # 只导入 bot7
  python import_fast.py --bot bot7 --dry   # 只提取不存储（预览）
  python import_fast.py --workers 4        # 4 线程并发处理 session
"""

import argparse
import glob
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MEM0_URL = "http://localhost:18095"
OPENCLAW_DIR = "/home/rooot/.openclaw"
AGENTS_DIR = os.path.join(OPENCLAW_DIR, "agents")
PROGRESS_FILE = os.path.join(OPENCLAW_DIR, "mem0", "import_progress_fast.json")

# GLM-5 配置
LLM_CLIENT = OpenAI(
    api_key="XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69",
    base_url="https://dd-ai-api.eastmoney.com/v1",
)
LLM_MODEL = "glm-5"

EXTRACT_PROMPT = """你是一个信息提取专家。从以下对话中提取所有有价值的事实、观点、决策和知识。

提取规则：
- 投资观点和判断（看好/看空、估值判断等）
- 操作决策（建仓、减仓、发帖等）
- 研究发现和数据
- 工作指令和反馈
- 经验教训和踩坑记录
- 内容运营规则（选题、限流、风格等）
- 每条事实简洁明确，不超过50字
- 用中文记录
- 返回 JSON: {"facts": ["事实1", "事实2", ...]}
- 如果没有有价值信息，返回 {"facts": []}
- 最多提取20条最重要的事实"""


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


# ============================================================
# Session 解析（复用 import_data.py 的清洗逻辑）
# ============================================================

def clean_user_message(text):
    text = re.sub(r'^⚡ Skill-first.*?\n\n', '', text, flags=re.DOTALL)
    m = re.search(r'(?:DM from \S+:|Group message:)\s*(.*)', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    text = re.sub(r'\nConversation info.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\[message_id:.*?\]\n?', '', text)
    text = re.sub(r'^[\u4e00-\u9fff\w]+:\s*', '', text)
    return text.strip()


def clean_assistant_message(text):
    return text.replace("[[reply_to_current]]", "").strip()


def parse_session(jsonl_path):
    messages = []
    try:
        with open(jsonl_path) as f:
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
                texts = [c["text"] for c in msg.get("content", []) if c.get("type") == "text"]
                if not texts:
                    continue
                text = "\n".join(texts)
                if len(text) < 30:
                    continue
                if text.startswith("data:image/"):
                    continue
                if "Exec completed" in text and len(text) < 200:
                    continue
                if "base64," in text and len(text) > 5000:
                    continue
                if re.match(r'^(HEARTBEAT_OK|/status|/help)\s*$', text.strip()):
                    continue
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
    # 支持 bot1-N, mag1, sys1-3, main 等所有 agent 命名
    m = re.search(r'agents/([a-z]+\d*)/', path)
    return m.group(1) if m else None


def extract_session_id(path):
    return os.path.basename(path).replace(".jsonl", "")


# ============================================================
# 核心：GLM-5 一次性提取 + mem0 直接存储
# ============================================================

def extract_facts_from_messages(messages, max_chars=6000):
    """用 GLM-5 一次性从消息中提取事实"""
    # 拼接对话文本，限制长度
    conversation = ""
    for m in messages:
        role_label = "User" if m["role"] == "user" else "Assistant"
        line = f"{role_label}: {m['content']}\n"
        if len(conversation) + len(line) > max_chars:
            break
        conversation += line

    if len(conversation) < 30:
        return []

    try:
        response = LLM_CLIENT.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": f"对话内容：\n\n{conversation}"},
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        # 去掉 markdown 代码块
        content = re.sub(r'^```json\s*\n?', '', content.strip())
        content = re.sub(r'\n?```$', '', content.strip())
        facts = json.loads(content).get("facts", [])
        return [f for f in facts if isinstance(f, str) and len(f) > 5]
    except Exception as e:
        logger.error(f"GLM-5 extraction error: {e}")
        return []


def store_facts(facts, user_id, agent_id, session_id, metadata=None):
    """用 infer=False 直接存入 mem0（只做 embedding，不调 LLM）"""
    stored = 0
    for fact in facts:
        payload = {
            "messages": [{"role": "user", "content": fact}],
            "user_id": user_id,
            "agent_id": agent_id,
            "run_id": session_id,
            "infer": False,
        }
        if metadata:
            payload["metadata"] = metadata
        try:
            r = requests.post(f"{MEM0_URL}/memories", json=payload, timeout=30)
            if r.status_code == 200:
                stored += 1
            else:
                logger.warning(f"Store failed ({r.status_code}): {r.text[:100]}")
        except Exception as e:
            logger.error(f"Store error: {e}")
    return stored


def process_session(filepath, dry_run=False):
    """处理单个 session 文件：解析 → 提取 → 存储"""
    bot_id = extract_bot_id(filepath)
    session_id = extract_session_id(filepath)
    if not bot_id:
        return None

    messages = parse_session(filepath)
    if not messages:
        return {"bot": bot_id, "session": session_id, "status": "empty", "facts": 0, "msgs": 0}

    # 如果消息太多，分段提取
    all_facts = []
    chunk_size = 20  # 每次最多 20 条消息给 GLM-5
    for i in range(0, len(messages), chunk_size):
        chunk = messages[i:i + chunk_size]
        facts = extract_facts_from_messages(chunk)
        all_facts.extend(facts)

    if dry_run:
        logger.info(f"[{bot_id}] {session_id}: {len(messages)} msgs → {len(all_facts)} facts (dry run)")
        for f in all_facts:
            logger.info(f"  - {f}")
        return {"bot": bot_id, "session": session_id, "status": "dry", "facts": len(all_facts), "msgs": len(messages)}

    # 存储
    stored = store_facts(all_facts, user_id="研究部", agent_id=bot_id, session_id=session_id)
    logger.info(f"[{bot_id}] {session_id}: {len(messages)} msgs → {len(all_facts)} facts → {stored} stored")

    return {"bot": bot_id, "session": session_id, "status": "done", "facts": stored, "msgs": len(messages)}


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Fast import OpenClaw sessions into mem0")
    parser.add_argument("--bot", default="all")
    parser.add_argument("--workers", type=int, default=2, help="Concurrent session processing")
    parser.add_argument("--dry", action="store_true", help="Extract only, don't store")
    args = parser.parse_args()

    # 健康检查
    if not args.dry:
        try:
            r = requests.get(f"{MEM0_URL}/health", timeout=5)
            r.raise_for_status()
            logger.info(f"mem0 server OK")
        except Exception as e:
            logger.error(f"mem0 server not reachable: {e}")
            sys.exit(1)

    # 收集待处理文件
    progress = load_progress()
    pattern = os.path.join(AGENTS_DIR, "*/sessions/*.jsonl")
    all_files = sorted(glob.glob(pattern))

    files = []
    for f in all_files:
        bot_id = extract_bot_id(f)
        if not bot_id:
            continue
        if args.bot != "all" and bot_id != args.bot:
            continue
        if os.path.getsize(f) < 500:
            continue
        session_id = extract_session_id(f)
        key = f"{bot_id}/{session_id}"
        if key in progress:
            continue
        files.append(f)

    logger.info(f"Processing {len(files)} session files (workers={args.workers})")

    total_facts = 0
    total_done = 0
    start_time = time.time()

    if args.workers <= 1:
        # 串行
        for filepath in files:
            result = process_session(filepath, dry_run=args.dry)
            if result:
                key = f"{result['bot']}/{result['session']}"
                progress[key] = result
                save_progress(progress)
                total_facts += result.get("facts", 0)
                total_done += 1
                elapsed = time.time() - start_time
                rate = total_done / elapsed * 60 if elapsed > 0 else 0
                remaining = (len(files) - total_done) / rate if rate > 0 else 0
                logger.info(f"  Progress: {total_done}/{len(files)} ({rate:.1f}/min, ~{remaining:.0f}min left)")
    else:
        # 并发
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_session, f, args.dry): f for f in files}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    key = f"{result['bot']}/{result['session']}"
                    progress[key] = result
                    save_progress(progress)
                    total_facts += result.get("facts", 0)
                    total_done += 1
                    elapsed = time.time() - start_time
                    rate = total_done / elapsed * 60 if elapsed > 0 else 0
                    remaining = (len(files) - total_done) / rate if rate > 0 else 0
                    logger.info(f"  Progress: {total_done}/{len(files)} ({rate:.1f}/min, ~{remaining:.0f}min left)")

    elapsed = time.time() - start_time
    logger.info(f"Done! {total_done} sessions, {total_facts} facts in {elapsed:.0f}s")


if __name__ == "__main__":
    main()
