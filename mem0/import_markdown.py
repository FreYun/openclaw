#!/usr/bin/env python3
"""导入 workspace-bot*/memory/ 下的 markdown 到 mem0

扫描三类数据，全部用 infer=False 存向量（已经是结构化内容，不需要 LLM 再提取）：

  1. research/*.md    — 研究报告
  2. posts/*.md       — sync 过来的历史发帖（含 YAML frontmatter）
  3. YYYY-MM-DD.md    — 日记（按日期切分，不会被修改）

切分策略：
- 文件 < 4000 字 → 整文件 1 条记忆
- 文件 >= 4000 字 → 按 `##` 标题切，每段 1 条

进度：按 path 记录到 markdown_progress.json，幂等追加新文件。

用法：
  python3 import_markdown.py                 # 全量跑
  python3 import_markdown.py --bot bot7      # 只跑 bot7
  python3 import_markdown.py --source posts  # 只跑 posts
  python3 import_markdown.py --dry           # 预览不写入
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MEM0_URL = "http://localhost:18095"
OPENCLAW_DIR = "/home/rooot/.openclaw"
PROGRESS_FILE = os.path.join(OPENCLAW_DIR, "mem0", "markdown_progress.json")

MAX_CHARS = 4000
USER_ID = "研究部"

# 只处理 bot 类型 agent（不处理 mag1/sys1-3/main）
BOT_WORKSPACE_PATTERN = re.compile(r"^workspace-bot\d+$")

# 合法 post 文件名：YYYY-MM-DDTHH-MM-SS_{post_id}.md（sync_posts.py 的命名规则）
# 过滤掉遗留的 ad-hoc 文件（如「发帖记录.md」「xxx-草稿.md」等）
POST_FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}_[\w-]+\.md$")

# 合法 diary 文件名：YYYY-MM-DD.md
DIARY_FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


# ============================================================
# 文件切分
# ============================================================

def split_markdown(text, max_chars=MAX_CHARS):
    """长文件按 ## 标题切分，短文件整段返回"""
    text = text.strip()
    if len(text) < max_chars:
        return [text]

    # 按 `^## ` 切分
    sections = re.split(r'\n(?=##\s)', text)
    chunks = []
    buf = ""
    for sec in sections:
        if len(buf) + len(sec) <= max_chars:
            buf = (buf + "\n" + sec).strip() if buf else sec.strip()
        else:
            if buf:
                chunks.append(buf)
            # 段本身超长 → 硬切
            if len(sec) > max_chars:
                for i in range(0, len(sec), max_chars):
                    chunks.append(sec[i:i + max_chars])
                buf = ""
            else:
                buf = sec.strip()
    if buf:
        chunks.append(buf)
    return [c for c in chunks if len(c) >= 30]


# ============================================================
# 三种数据源的 parser
# ============================================================

def parse_post(path):
    """解析 posts/*.md，返回 [(text, metadata)] 一条"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析 frontmatter
    fm = {}
    body = content
    if content.startswith("---"):
        lines = content.split("\n")
        fm_end = -1
        for i, ln in enumerate(lines[1:], 1):
            if ln.strip() == "---":
                fm_end = i
                break
        if fm_end > 0:
            for ln in lines[1:fm_end]:
                m = re.match(r'^(\w+):\s*(.*)$', ln)
                if m:
                    fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
            body = "\n".join(lines[fm_end + 1:]).strip()

    title = fm.get("title", "").strip().strip('"').strip("'")
    tags_raw = fm.get("tags", "")
    fm_content = fm.get("content", "").strip().strip('"').strip("'")
    date = os.path.basename(path).split("T")[0]  # 2026-04-12T10-19-15_xxx.md -> 2026-04-12

    # 构造记忆文本
    parts = [f"[{date} 已发布] {title}"] if title else [f"[{date} 已发布]"]
    if fm_content:
        parts.append(fm_content)
    # body（text_image 的完整内容）如果跟 content 不同且不重复，追加
    if body and body not in fm_content and len(body) > 20:
        parts.append(body[:1500])  # 限长防止太长
    if tags_raw:
        parts.append(f"标签: {tags_raw}")

    text = "\n".join(parts)

    metadata = {
        "source": "post",
        "date": date,
        "title": title,
        "filename": os.path.basename(path),
    }
    return [(text, metadata)]


def parse_research(path):
    """解析 research/*.md，切分后返回多条"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = split_markdown(content)
    filename = os.path.basename(path)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    date = date_match.group(1) if date_match else ""

    results = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "source": "research",
            "filename": filename,
            "date": date,
            "chunk": i,
        }
        results.append((chunk, metadata))
    return results


def parse_diary(path):
    """解析 YYYY-MM-DD.md，切分后返回多条"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = split_markdown(content)
    filename = os.path.basename(path)
    date = filename.replace(".md", "")

    results = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "source": "diary",
            "date": date,
            "chunk": i,
        }
        results.append((chunk, metadata))
    return results


# ============================================================
# mem0 存储
# ============================================================

def store_memory(text, user_id, agent_id, run_id, metadata):
    """用 infer=False 直接存向量"""
    payload = {
        "messages": [{"role": "user", "content": text}],
        "user_id": user_id,
        "agent_id": agent_id,
        "run_id": run_id,
        "infer": False,
        "metadata": metadata,
    }
    try:
        r = requests.post(f"{MEM0_URL}/memories", json=payload, timeout=60)
        if r.status_code == 200:
            return True
        logger.warning(f"Store failed ({r.status_code}): {r.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"Store error: {e}")
        return False


# ============================================================
# 主流程
# ============================================================

def iter_files(bot_id, source):
    """返回 (bot_id, source, file_path) 迭代器"""
    mem_dir = os.path.join(OPENCLAW_DIR, f"workspace-{bot_id}/memory")
    if not os.path.isdir(mem_dir):
        return

    if source in ("research", "all"):
        for f in sorted(glob.glob(os.path.join(mem_dir, "research/*.md"))):
            yield bot_id, "research", f

    if source in ("posts", "all"):
        # 只认 sync_posts.py 命名规范的文件，避免老 bot 在 posts/ 里塞的草稿/笔记被误索引
        for f in sorted(glob.glob(os.path.join(mem_dir, "posts/*.md"))):
            if POST_FILENAME_PATTERN.match(os.path.basename(f)):
                yield bot_id, "post", f

    if source in ("diary", "all"):
        # 支持两种目录结构：memory/YYYY-MM-DD.md 和 memory/diary/YYYY-MM-DD.md
        for pattern in ("*.md", "diary/*.md"):
            for f in sorted(glob.glob(os.path.join(mem_dir, pattern))):
                if DIARY_FILENAME_PATTERN.match(os.path.basename(f)):
                    yield bot_id, "diary", f


def list_bots():
    """列出所有 workspace-botN 目录"""
    bots = []
    for d in os.listdir(OPENCLAW_DIR):
        if BOT_WORKSPACE_PATTERN.match(d):
            bots.append(d.replace("workspace-", ""))
    return sorted(bots, key=lambda x: int(x.replace("bot", "")))


def process_file(bot_id, source, filepath, dry_run=False):
    """处理单个文件：parse → chunks → store"""
    try:
        if source == "post":
            items = parse_post(filepath)
        elif source == "research":
            items = parse_research(filepath)
        elif source == "diary":
            items = parse_diary(filepath)
        else:
            return 0

        if not items:
            return 0

        stored = 0
        run_id = f"{source}-{os.path.basename(filepath).replace('.md', '')}"
        for text, metadata in items:
            if len(text) < 30:
                continue
            if dry_run:
                stored += 1
                continue
            if store_memory(text, USER_ID, bot_id, run_id, metadata):
                stored += 1
        return stored
    except Exception as e:
        logger.error(f"Process {filepath} error: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", default="all", help="bot ID (e.g. bot7) or 'all'")
    parser.add_argument("--source", default="all",
                        choices=["all", "research", "posts", "diary"])
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    if not args.dry:
        try:
            requests.get(f"{MEM0_URL}/health", timeout=5).raise_for_status()
            logger.info("mem0 server OK")
        except Exception as e:
            logger.error(f"mem0 server not reachable: {e}")
            sys.exit(1)

    progress = load_progress()

    # 收集 bot 列表
    all_bots = list_bots()
    bots = all_bots if args.bot == "all" else [args.bot]

    # 收集所有文件
    files = []
    for bot_id in bots:
        for b, src, f in iter_files(bot_id, args.source):
            key = f"{b}/{src}/{os.path.basename(f)}"
            if key in progress:
                continue
            files.append((b, src, f, key))

    logger.info(f"Processing {len(files)} files (bots={len(bots)}, source={args.source})")

    total_stored = 0
    by_source = {}
    by_bot = {}
    start = time.time()

    for i, (bot_id, source, filepath, key) in enumerate(files, 1):
        stored = process_file(bot_id, source, filepath, dry_run=args.dry)
        total_stored += stored
        by_source[source] = by_source.get(source, 0) + stored
        by_bot[bot_id] = by_bot.get(bot_id, 0) + stored

        if not args.dry:
            progress[key] = {"bot": bot_id, "source": source, "stored": stored, "ts": time.time()}
            save_progress(progress)

        if i % 10 == 0 or i == len(files):
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(files) - i) / rate if rate > 0 else 0
            logger.info(f"  {i}/{len(files)} ({rate:.1f}/s, ~{eta:.0f}s left) - {bot_id}/{source}: +{stored}")

    logger.info(f"Done! {total_stored} memories stored in {time.time() - start:.0f}s")
    logger.info(f"  By source: {by_source}")
    logger.info(f"  By bot: {dict(sorted(by_bot.items(), key=lambda x: int(x[0].replace('bot', ''))))}")


if __name__ == "__main__":
    main()
