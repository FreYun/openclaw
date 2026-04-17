#!/usr/bin/env python3
"""Sync sys1/publish-queue/{published,done} 的 post.md 到各 bot 的 memory/posts/

命名规则：
  原: sys1/publish-queue/published/2026-04-12T10-19-15_bot2_7054ub/post.md
  新: workspace-bot2/memory/posts/2026-04-12T10-19-15_7054ub.md

过滤：
- 只 sync 目录名匹配 {timestamp}_{bot_id}_{post_id} 的条目
- 只 sync visibility = 公开可见 的帖子（跳过 仅自己可见 测试帖）
- 目标文件已存在 → 跳过（幂等）

用法：
  python3 sync_posts.py                # 执行 sync
  python3 sync_posts.py --dry          # 预览不写入
"""

import argparse
import os
import re
import shutil
import sys

# 尝试 yaml，没有就用简单解析
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

OPENCLAW_DIR = "/home/rooot/.openclaw"
SOURCE_QUEUES = ["published", "done"]
SOURCE_BASE = os.path.join(OPENCLAW_DIR, "workspace-sys1/publish-queue")

NAME_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})_(bot\d+)_([\w-]+?)(?:\.md)?$'
)


def parse_frontmatter(path):
    """解析 post.md 的 YAML frontmatter，返回 dict 或 None"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return {}
        # 找第二个 ---
        lines = content.split("\n")
        if lines[0].strip() != "---":
            return {}
        fm_lines = []
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            fm_lines.append(ln)
        fm_text = "\n".join(fm_lines)
        if HAS_YAML:
            try:
                return yaml.safe_load(fm_text) or {}
            except yaml.YAMLError:
                pass
        # 简单 key: value 解析
        result = {}
        for ln in fm_lines:
            m = re.match(r'^(\w+):\s*"?([^"]*)"?$', ln)
            if m:
                result[m.group(1)] = m.group(2).strip()
        return result
    except Exception as e:
        return None


def iter_posts():
    """遍历 publish-queue，yield (bot_id, timestamp, post_id, source_path)"""
    for queue in SOURCE_QUEUES:
        qdir = os.path.join(SOURCE_BASE, queue)
        if not os.path.isdir(qdir):
            continue
        for entry in sorted(os.listdir(qdir)):
            entry_path = os.path.join(qdir, entry)
            m = NAME_PATTERN.match(entry)
            if not m:
                continue
            ts, bot_id, post_id = m.groups()

            if os.path.isdir(entry_path):
                src = os.path.join(entry_path, "post.md")
                if not os.path.isfile(src):
                    continue
            elif entry.endswith(".md"):
                src = entry_path
            else:
                continue

            yield bot_id, ts, post_id, src


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="预览不写入")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    stats = {"synced": 0, "skipped": 0, "filtered": 0, "errors": 0, "no_workspace": 0}
    per_bot = {}

    for bot_id, ts, post_id, src in iter_posts():
        bot_ws = os.path.join(OPENCLAW_DIR, f"workspace-{bot_id}")
        if not os.path.isdir(bot_ws):
            stats["no_workspace"] += 1
            if args.verbose:
                print(f"[no-ws] {bot_id} 无 workspace 目录，跳过")
            continue

        target_dir = os.path.join(bot_ws, "memory/posts")
        target = os.path.join(target_dir, f"{ts}_{post_id}.md")

        if os.path.exists(target):
            stats["skipped"] += 1
            continue

        fm = parse_frontmatter(src)
        if fm is None:
            stats["errors"] += 1
            if args.verbose:
                print(f"[err] 无法解析 {src}")
            continue

        visibility = (fm.get("visibility") or "").strip().strip('"').strip("'")
        if visibility and visibility != "公开可见":
            stats["filtered"] += 1
            if args.verbose:
                print(f"[filter] {bot_id}/{ts}_{post_id}: {visibility}")
            continue

        if args.dry:
            print(f"[dry] {src} -> {target}")
        else:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(src, target)

        stats["synced"] += 1
        per_bot[bot_id] = per_bot.get(bot_id, 0) + 1

    print(f"\nSync done{' (dry-run)' if args.dry else ''}:")
    print(f"  synced: {stats['synced']}")
    print(f"  skipped (exists): {stats['skipped']}")
    print(f"  filtered (非公开): {stats['filtered']}")
    print(f"  errors: {stats['errors']}")
    print(f"  no_workspace: {stats['no_workspace']}")
    if per_bot:
        print("\nBy bot:")
        for b in sorted(per_bot, key=lambda x: int(x.replace("bot", ""))):
            print(f"  {b}: +{per_bot[b]}")


if __name__ == "__main__":
    main()
