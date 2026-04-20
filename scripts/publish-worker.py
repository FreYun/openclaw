#!/usr/bin/env python3
"""publish-worker.py — 流程化发布脚本，替代印务局 (sys1) Agent。

用法：
  python3 publish-worker.py                          # 处理所有 pending
  python3 publish-worker.py FOLDER_NAME              # 处理单个投稿
  python3 publish-worker.py --dry-run                 # 只打印不执行
  python3 publish-worker.py --dry-run FOLDER_NAME     # 单个投稿 dry-run

完全复刻 workspace-sys1/AGENTS.md 的发布流水线：
  scan → parse → validate → normalize tags → health check → login check
  → lock → build args → publish → archive → log → notify
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

# ─── 常量 ───────────────────────────────────────────────────────────────────

BASE_DIR = Path("/home/rooot/.openclaw")
QUEUE_DIR = BASE_DIR / "workspace-sys1" / "publish-queue"
PENDING_DIR = QUEUE_DIR / "pending"
PUBLISHING_DIR = QUEUE_DIR / "publishing"
PUBLISHED_DIR = QUEUE_DIR / "published"
FAILED_DIR = QUEUE_DIR / "failed"
SYS1_WORKSPACE = BASE_DIR / "workspace-sys1"
LOG_SCRIPT = BASE_DIR / "scripts" / "log-publish.py"
MCP_HEALTH_URL = "http://localhost:18060/health"

RATE_LIMIT_MINUTES = 15
RATE_LIMIT_EXEMPT = {"bot10"}
VALID_ACCOUNTS = {f"bot{i}" for i in range(1, 20)}
MAX_TAGS = 5
MCPORTER_TIMEOUT = "180000"


# ─── YAML frontmatter 解析 ──────────────────────────────────────────────────

def parse_post_md(post_path: Path) -> tuple[dict, str]:
    """解析 post.md，返回 (frontmatter_dict, body_text)。"""
    raw = post_path.read_text(encoding="utf-8")

    # 分割 frontmatter
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"post.md 格式错误：找不到 YAML frontmatter 分隔符 (---)")

    fm_text = parts[1]
    body = parts[2]

    # 剥离归档时追加的 published_at 注释，防止重发场景下把归档标记当正文发出去。
    body = re.sub(r"\n*<!--\s*published_at:.*?-->\s*", "", body)
    body = body.strip()

    meta = yaml.safe_load(fm_text)
    if not isinstance(meta, dict):
        raise ValueError(f"post.md frontmatter 解析结果不是 dict: {type(meta)}")

    return meta, body


# ─── 校验 ───────────────────────────────────────────────────────────────────

def validate(meta: dict, body: str, entry_name: str) -> list[str]:
    """校验 post 元数据，返回错误列表（空 = 通过）。"""
    errors = []

    account_id = meta.get("account_id", "")
    if account_id not in VALID_ACCOUNTS:
        errors.append(f"account_id 无效: '{account_id}'（需 bot1-bot19）")

    title = meta.get("title", "")
    if not title:
        errors.append("title 为空")
    elif len(title) > 20:
        errors.append(f"title 超长: {len(title)} 字（最大 20）")

    # body 非空检查
    if not body:
        errors.append("body 为空（--- 之后无内容）")

    # text_to_image 专项核查（MEMORY.md 永久规则）
    publish_type = meta.get("publish_type", "content")
    content_mode = meta.get("content_mode", "")
    if publish_type == "content" and content_mode == "text_to_image":
        # text_image 来自 body（YAML double-quote 会 fold 换行，所以用 body 原文判断）
        text_image_raw = body
        content = meta.get("content", "")
        if not text_image_raw:
            errors.append(
                "text_to_image 模式: text_image（卡片文字）为空。"
                "必须同时提供 text_image 和 content，请补全后重新投稿"
            )
        if not content:
            errors.append(
                "text_to_image 模式: content（图下正文）为空。"
                "必须同时提供 text_image 和 content，请补全后重新投稿"
            )
        # 卡片数检查：body 里 \n\n 分隔，最多 3 张（超出打 WARNING，不硬拒）
        cards = [c.strip() for c in text_image_raw.split("\n\n") if c.strip()]
        if len(cards) > 3:
            print(f"  [WARN] text_to_image 卡片数 {len(cards)} 张，超过建议的 3 张上限")

    # 频率限制（published/ 里只有成功的，失败的已被 rm，所以天然只对成功的生效）
    if account_id and account_id not in RATE_LIMIT_EXEMPT:
        last_ts = _find_last_published_time(account_id)
        if last_ts:
            elapsed = datetime.now() - last_ts
            if elapsed < timedelta(minutes=RATE_LIMIT_MINUTES):
                remaining = RATE_LIMIT_MINUTES - int(elapsed.total_seconds() / 60)
                errors.append(
                    f"频率限制: {account_id} 上次发布于 {int(elapsed.total_seconds())}s 前，"
                    f"需等待 {remaining} 分钟"
                )

    return errors


def _find_last_published_time(account_id: str) -> datetime | None:
    """在 published/ 目录中找同 account_id 的最近成功发布时间。"""
    if not PUBLISHED_DIR.exists():
        return None

    latest = None
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})_" + re.escape(account_id) + r"_")

    for entry in PUBLISHED_DIR.iterdir():
        m = pattern.match(entry.name)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%dT%H-%M-%S")
                # 文件夹时间戳是本地时间，不附加时区
                if latest is None or ts > latest:
                    latest = ts
            except ValueError:
                continue

    return latest


# ─── Tag 规范化 ─────────────────────────────────────────────────────────────

def normalize_tags(tags) -> list[str]:
    """逗号分割、去 # 前缀、去重、cap at 5。"""
    if not tags:
        return []

    if isinstance(tags, str):
        tags = [tags]

    expanded = []
    for tag in tags:
        # 分割中英文逗号
        parts = re.split(r"[，,]", str(tag))
        expanded.extend(p.strip() for p in parts if p.strip())

    # 去 # 前缀
    cleaned = [t.lstrip("#").strip() for t in expanded]

    # 去重（保序）
    seen = set()
    deduped = []
    for t in cleaned:
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)

    return deduped[:MAX_TAGS]


# ─── MCP 健康检查 ───────────────────────────────────────────────────────────

def health_check() -> bool:
    """检查 XHS MCP 服务是否存活。"""
    try:
        r = subprocess.run(
            ["curl", "-s", "--connect-timeout", "3", "--max-time", "5", MCP_HEALTH_URL],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip() != ""
    except (subprocess.TimeoutExpired, Exception):
        return False


# ─── 登录检查 ───────────────────────────────────────────────────────────────

def login_check(account_id: str) -> tuple[bool, str]:
    """检查 bot 的创作者平台登录状态。返回 (is_logged_in, raw_output)。"""
    svc = f"xhs-{account_id}"
    try:
        r = subprocess.run(
            ["npx", "mcporter", "call", "--timeout", MCPORTER_TIMEOUT,
             f"{svc}.check_login_status()"],
            capture_output=True, text=True, timeout=200,
            cwd=str(SYS1_WORKSPACE),
        )
        output = r.stdout + r.stderr

        # mcporter 输出格式可能是:
        # 1) 中文文本: "创作者平台: ✅ 已登录"
        # 2) JSON: { "isCreatorLoggedIn": true }
        # 3) JSON wrapped in content[].text

        # 先检查中文文本格式
        if "创作者平台" in output:
            if "✅" in output and "已登录" in output:
                return True, output
            if "未登录" in output or "❌" in output:
                return False, output

        # 再检查 JSON 格式
        if "isCreatorLoggedIn" in output:
            if '"isCreatorLoggedIn": true' in output or '"isCreatorLoggedIn":true' in output:
                return True, output
            return False, output

        # mcporter 返回 0 且没有明显错误 → 视为已登录
        if r.returncode == 0 and "error" not in output.lower()[:200]:
            return True, output

        return False, output
    except subprocess.TimeoutExpired:
        return False, "mcporter call timeout"
    except Exception as e:
        return False, str(e)


# ─── 构建 mcporter args.json ────────────────────────────────────────────────

def _resolve_schedule_at(raw: str) -> str:
    """schedule_at 处理：空/过期 → 空串（立即发布），未来时间 → 原样返回。"""
    if not raw:
        return ""
    try:
        scheduled = datetime.fromisoformat(raw)
        if scheduled.tzinfo is None:
            # 假设本地时间
            scheduled = scheduled.astimezone()
        if scheduled <= datetime.now().astimezone():
            return ""  # 已过期，立即发布
        return raw
    except (ValueError, TypeError):
        return ""


def build_args(meta: dict, body: str, folder_path: Path) -> dict:
    """根据 publish_type/content_mode 构建 MCP 调用参数。"""
    publish_type = meta.get("publish_type", "content")
    content_mode = meta.get("content_mode", "text_to_image")
    tags = normalize_tags(meta.get("tags", []))
    schedule_at = _resolve_schedule_at(meta.get("schedule_at", ""))

    if publish_type == "content" and content_mode == "text_to_image":
        # text_image 必须用 body 原文（YAML double-quote 会 fold 换行，丢失卡片内换行）
        # MEMORY.md 永久规则: text_image MCP param = body（--- 之后）
        args = {
            "title": meta.get("title", ""),
            "content": meta.get("content", ""),
            "text_image": body,
            "text_to_image": True,
            "image_style": meta.get("image_style", "基础"),
            "tags": tags,
            "visibility": meta.get("visibility", "公开可见"),
            "is_original": meta.get("is_original", False),
        }
        if schedule_at:
            args["schedule_at"] = schedule_at
        return args

    if publish_type == "content" and content_mode == "image":
        # 图片路径需要转成绝对路径
        images = meta.get("images", [])
        abs_images = [str(folder_path / img) for img in images]
        args = {
            "title": meta.get("title", ""),
            "content": meta.get("content", "") or body,
            "text_to_image": False,
            "images": abs_images,
            "tags": tags,
            "visibility": meta.get("visibility", "公开可见"),
            "is_original": meta.get("is_original", False),
        }
        if schedule_at:
            args["schedule_at"] = schedule_at
        return args

    if publish_type == "longform":
        args = {
            "title": meta.get("title", ""),
            "content": body,
            "tags": tags,
            "visibility": meta.get("visibility", "公开可见"),
        }
        if meta.get("desc"):
            args["desc"] = meta["desc"]
        return args

    if publish_type == "video":
        video_file = meta.get("video", "")
        args = {
            "title": meta.get("title", ""),
            "content": body,
            "video": str(folder_path / video_file) if video_file else "",
            "tags": tags,
            "visibility": meta.get("visibility", "公开可见"),
            "is_original": meta.get("is_original", False),
        }
        if schedule_at:
            args["schedule_at"] = schedule_at
        return args

    raise ValueError(f"未知的 publish_type/content_mode: {publish_type}/{content_mode}")


def get_mcp_method(meta: dict) -> str:
    """根据 publish_type 返回 MCP method 名。"""
    publish_type = meta.get("publish_type", "content")
    if publish_type == "longform":
        return "publish_longform"
    return "publish_content"


# ─── 发布 ───────────────────────────────────────────────────────────────────

def publish(account_id: str, method: str, args: dict, folder_path: Path) -> tuple[bool, str]:
    """调用 mcporter 发布。返回 (success, output)。"""
    svc = f"xhs-{account_id}"
    args_file = folder_path / "args.json"
    args_file.write_text(json.dumps(args, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        print(f"  ⏳ 等待 MCP 响应（最长 3 分钟）...")
        sys.stdout.flush()
        r = subprocess.run(
            ["npx", "mcporter", "call", "--timeout", MCPORTER_TIMEOUT,
             f"{svc}.{method}", "--args", args_file.read_text(encoding="utf-8")],
            capture_output=True, text=True, timeout=200,
            cwd=str(SYS1_WORKSPACE),
        )
        output = r.stdout + r.stderr

        # 失败关键词（包括中文和英文）
        fail_keywords = ["失败", "失敗", "error", "failed", "exception", "timeout", "没有找到", "未找到", "无法"]
        # 成功关键词
        success_keywords = ["发布成功", "已发布", "publish success", "published"]

        output_lower = output.lower()
        has_fail = any(k.lower() in output_lower for k in fail_keywords)
        has_success = any(k.lower() in output_lower for k in success_keywords)

        # 判断优先级：明确失败 > 明确成功 > returncode
        # 失败优先：同一 output 同时含两类关键词时，宁可误报失败也不能把失败当成功
        # （失败误报最多触发一次重试；成功误报会污染 post.md 并跳过实际错误处理）
        if has_fail:
            error_hint = ""
            for line in output.splitlines():
                if any(k in line for k in fail_keywords):
                    error_hint = line.strip()[:150]
                    break
            print(f"  MCP 返回错误: {error_hint or output.splitlines()[0][:150]}")
            return False, output

        if has_success:
            for line in output.splitlines():
                if any(k in line for k in success_keywords):
                    print(f"  MCP 返回: {line.strip()[:100]}")
                    break
            return True, output

        # 既没明确成功也没明确失败 → 看 returncode
        if r.returncode == 0:
            return True, output

        error_hint = output.splitlines()[0][:150] if output.strip() else "空输出"
        print(f"  MCP 返回错误 (exit {r.returncode}): {error_hint}")
        return False, output
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ MCP 调用超时 (200s)")
        return False, "mcporter call timeout (200s)"
    except Exception as e:
        return False, str(e)


# ─── 日志记录 ───────────────────────────────────────────────────────────────

def log_publish(account_id: str, title: str, opinion: str, status: str):
    """调用 log-publish.py 记录。"""
    try:
        subprocess.run(
            ["python3", str(LOG_SCRIPT),
             "--bot", account_id,
             "--title", title,
             "--opinion", opinion,
             "--status", status],
            capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        print(f"  [WARN] log-publish.py 失败: {e}", file=sys.stderr)


# ─── 通知 ───────────────────────────────────────────────────────────────────

def notify(reply_to: str, account_id: str, message: str):
    """通过 openclaw message send 发送飞书通知。"""
    if not reply_to:
        print("  [WARN] reply_to 为空，跳过通知", file=sys.stderr)
        return

    # 解析 reply_to: "direct:ou_xxx" → target = "ou_xxx"
    target = reply_to
    if target.startswith("direct:"):
        target = target[len("direct:"):]

    try:
        subprocess.run(
            ["openclaw", "message", "send",
             "--channel", "feishu",
             "--target", target,
             "--account", account_id,
             "-m", message],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        print(f"  [WARN] 通知发送失败: {e}", file=sys.stderr)


# ─── mag1 上报（基础设施异常） ────────────────────────────────────────────────

def _notify_mag1(message: str):
    """基础设施异常上报 mag1。"""
    try:
        subprocess.run(
            ["openclaw", "agent", "--agent", "mag1",
             "--session-id", "agent:mag1:agent:sys1",
             "-m", message],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        print(f"  [WARN] mag1 上报失败: {e}", file=sys.stderr)


# ─── daily journal 更新 ─────────────────────────────────────────────────────

def _update_daily_journal(account_id: str, title: str, status: str):
    """更新 workspace-sys1/memory/YYYY-MM-DD.md 日志。"""
    today = datetime.now().strftime("%Y-%m-%d")
    journal_path = SYS1_WORKSPACE / "memory" / f"{today}.md"
    now_str = datetime.now().strftime("%H:%M")
    line = f"- {now_str} | {account_id} | 《{title}》| {status}\n"

    try:
        if journal_path.exists():
            content = journal_path.read_text(encoding="utf-8")
            # 插入到文件开头（标题之后）
            if content.startswith("#"):
                # 找到第一个空行后插入
                idx = content.find("\n\n")
                if idx >= 0:
                    content = content[:idx+2] + line + content[idx+2:]
                else:
                    content = content + "\n" + line
            else:
                content = line + content
            journal_path.write_text(content, encoding="utf-8")
        else:
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            journal_path.write_text(f"# {today} 印务局日志\n\n{line}", encoding="utf-8")
    except Exception as e:
        print(f"  [WARN] daily journal 更新失败: {e}", file=sys.stderr)


# ─── 主流水线 ───────────────────────────────────────────────────────────────

def process_entry(entry_name: str, dry_run: bool = False) -> bool:
    """处理单个投稿，返回是否成功。"""
    pending_path = PENDING_DIR / entry_name
    post_md_path = pending_path / "post.md"

    print(f"\n{'='*60}")
    print(f"处理: {entry_name}")
    print(f"{'='*60}")

    # ── 1. Parse ──
    if not post_md_path.exists():
        # 兼容老格式：.md 文件直接在 pending/ 下
        post_md_path = pending_path
        if not post_md_path.exists() or not post_md_path.is_file():
            print(f"  [ERROR] post.md 不存在: {post_md_path}")
            return False

    try:
        meta, body = parse_post_md(post_md_path)
    except Exception as e:
        print(f"  [ERROR] 解析失败: {e}")
        if not dry_run:
            _fail_entry(entry_name, pending_path, "unknown", entry_name, "",
                        f"YAML 解析失败: {e}")
        return False

    account_id = meta.get("account_id", "unknown")
    title = meta.get("title", entry_name)
    reply_to = meta.get("reply_to", "")

    print(f"  账号: {account_id}")
    print(f"  标题: {title}")
    print(f"  类型: {meta.get('publish_type')}/{meta.get('content_mode', '-')}")
    print(f"  可见性: {meta.get('visibility')}")
    print(f"  reply_to: {reply_to}")

    # ── 2. Validate ──
    errors = validate(meta, body, entry_name)
    if errors:
        for e in errors:
            print(f"  [VALIDATE FAIL] {e}")
        if not dry_run:
            _fail_entry(entry_name, pending_path, account_id, title, reply_to,
                        "校验失败: " + "; ".join(errors))
        return False

    # ── 3. Normalize tags ──
    original_tags = meta.get("tags", [])
    meta["tags"] = normalize_tags(original_tags)
    if meta["tags"] != original_tags:
        print(f"  [TAG FIX] {original_tags} → {meta['tags']}")

    # ── 4. Lock (mv pending → publishing) — 尽早锁定，dashboard 立刻显示 PUBLISHING ──
    publishing_path = PUBLISHING_DIR / entry_name
    if dry_run:
        print(f"  [DRY-RUN] 跳过锁定: {pending_path} → {publishing_path}")
        folder_path = pending_path
    else:
        PUBLISHING_DIR.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(pending_path), str(publishing_path))
        except Exception as e:
            print(f"  [ERROR] 锁定失败（可能已被其他进程处理）: {e}")
            return False
        print(f"  已锁定 → publishing/")
        folder_path = publishing_path

    # ── 5. Health check ──
    print("  健康检查...")
    if not health_check():
        print("  [ERROR] MCP 服务不可用 (localhost:18060)")
        if not dry_run:
            _notify_mag1(f"⚠️ MCP 服务不可用 (localhost:18060)，发布队列阻塞。投稿: 《{title}》({account_id})")
            _fail_entry(entry_name, folder_path, account_id, title, reply_to,
                        "MCP 服务不可用，请联系管理员")
        return False
    print("  MCP 服务正常 ✓")

    # ── 6. Login check ──
    print(f"  登录检查 ({account_id})...")
    if dry_run:
        print("  [DRY-RUN] 跳过登录检查")
    else:
        logged_in, login_output = login_check(account_id)
        if not logged_in:
            print(f"  [ERROR] {account_id} 创作者平台未登录")
            _fail_entry(entry_name, folder_path, account_id, title, reply_to,
                        f"{account_id} 创作者平台未登录")
            notify(reply_to, account_id,
                   f"📮 发布暂停 | 《{title}》| {account_id} 需要重新登录创作者平台")
            return False
        print(f"  创作者平台已登录 ✓")

    # ── 7. Build args ──
    try:
        args = build_args(meta, body, folder_path)
        method = get_mcp_method(meta)
    except Exception as e:
        print(f"  [ERROR] 构建参数失败: {e}")
        if not dry_run:
            _fail_entry(entry_name, folder_path, account_id, title, reply_to,
                        f"参数构建失败: {e}")
        return False

    print(f"  MCP method: xhs-{account_id}.{method}")

    if dry_run:
        print(f"  [DRY-RUN] 跳过发布")
        print(f"  [DRY-RUN] 完成 ✓")
        return True

    # ── 8. Publish ──
    print(f"  发布中...")
    success, output = publish(account_id, method, args, folder_path)

    if success:
        # ── 9a. Archive (success) ──
        PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
        published_path = PUBLISHED_DIR / entry_name
        try:
            shutil.move(str(folder_path), str(published_path))
            # 追加 published_at 时间戳到 post.md
            pub_post = published_path / "post.md"
            if pub_post.exists():
                with open(pub_post, "a", encoding="utf-8") as f:
                    f.write(f"\n<!-- published_at: {datetime.now().isoformat()} -->\n")
        except Exception as e:
            print(f"  [WARN] 归档失败: {e}")

        print(f"  发布成功 ✅")

        # ── 10. Log & Notify (success) ──
        log_publish(account_id, title, "通过", "✅ 已发布")
        _update_daily_journal(account_id, title, "✅ 已发布")
        notify(reply_to, account_id,
               f"📮 已发布 ✅ | 《{title}》| 账号: {account_id} | 可见性: {meta.get('visibility', '公开可见')}")
        return True
    else:
        # 首次失败 → 重试一次
        print(f"  发布失败，60s 后重试...")
        print(f"  错误: {output[:300]}")

        # 检查不可重试的情况
        if "Another operation in progress" in output:
            print(f"  [ERROR] 另一个操作进行中，不重试")
        elif "timeout" in output.lower() or "SIGTERM" in output:
            print(f"  [ERROR] 超时/SIGTERM，不重试（服务端可能仍在执行）")
        else:
            # 等待 60s 重试
            time.sleep(60)
            # 重试前重新检查登录
            logged_in, _ = login_check(account_id)
            if logged_in:
                print(f"  重试发布...")
                success, output = publish(account_id, method, args, folder_path)
                if success:
                    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
                    published_path = PUBLISHED_DIR / entry_name
                    try:
                        shutil.move(str(folder_path), str(published_path))
                    except Exception:
                        pass
                    print(f"  重试成功 ✅")
                    log_publish(account_id, title, "重试通过", "✅ 已发布")
                    _update_daily_journal(account_id, title, "✅ 已发布（重试）")
                    notify(reply_to, account_id,
                           f"📮 已发布 ✅ | 《{title}》| 账号: {account_id} | 可见性: {meta.get('visibility', '公开可见')}")
                    return True

        # ── 9b. Archive (failure) ──
        _fail_entry(entry_name, folder_path, account_id, title, reply_to,
                    output[:200])
        return False


def _fail_entry(entry_name: str, folder_path: Path, account_id: str,
                title: str, reply_to: str, reason: str):
    """处理失败的投稿：移到 failed/（保留原稿可修复重投）、记录、通知。"""
    # 移到 failed/（不删除）
    if folder_path.exists():
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        failed_path = FAILED_DIR / entry_name
        try:
            shutil.move(str(folder_path), str(failed_path))
            # 写入失败原因，方便排查
            error_file = failed_path / "error.txt" if failed_path.is_dir() else None
            if error_file:
                error_file.write_text(
                    f"time: {datetime.now().isoformat()}\n"
                    f"account_id: {account_id}\n"
                    f"title: {title}\n"
                    f"reason: {reason}\n",
                    encoding="utf-8",
                )
            print(f"  已移至 failed/{entry_name}")
        except Exception as e:
            print(f"  [WARN] 移到 failed/ 失败: {e}", file=sys.stderr)

    # 记录
    log_publish(account_id, title, reason[:100], "❌ 失败")
    _update_daily_journal(account_id, title, "❌ 失败")

    # 通知（告知可重投）
    notify(reply_to, account_id,
           f"📮 发布失败 ❌ | 《{title}》| 原因: {reason[:100]}\n"
           f"原稿已保留在 failed/，修复后可移回 pending/ 重投")

    print(f"  发布失败 ❌: {reason[:100]}")


# ─── 扫描 pending ───────────────────────────────────────────────────────────

def scan_pending() -> list[str]:
    """扫描 pending/ 目录，返回按时间排序的文件夹名列表（最早的在前）。"""
    if not PENDING_DIR.exists():
        return []

    entries = []
    for item in PENDING_DIR.iterdir():
        if item.name.startswith("."):
            continue
        if item.is_dir() and (item / "post.md").exists():
            entries.append(item.name)

    # 按文件夹名排序（名字以 timestamp 开头，自然排序 = 时间序）
    entries.sort()
    return entries


# ─── main ───────────────────────────────────────────────────────────────────

def retry_failed(entry_name: str = None):
    """将 failed/ 中的投稿移回 pending/ 重新处理。"""
    if not FAILED_DIR.exists():
        print("failed/ 目录不存在，无失败投稿。")
        return

    if entry_name:
        entries = [entry_name]
    else:
        entries = sorted(e.name for e in FAILED_DIR.iterdir()
                         if e.is_dir() and (e / "post.md").exists())

    if not entries:
        print("failed/ 目录为空。")
        return

    for name in entries:
        src = FAILED_DIR / name
        dst = PENDING_DIR / name
        if not src.exists():
            print(f"  [SKIP] {name} 不在 failed/ 中")
            continue
        # 删除 error.txt（重投不需要）
        err_file = src / "error.txt"
        if err_file.exists():
            err_file.unlink()
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"  ✅ {name} → pending/（等待下一轮处理）")


def list_failed():
    """列出 failed/ 中的投稿。"""
    if not FAILED_DIR.exists():
        print("failed/ 目录不存在。")
        return
    entries = sorted(e.name for e in FAILED_DIR.iterdir()
                     if e.is_dir() and (e / "post.md").exists())
    if not entries:
        print("failed/ 为空。")
        return
    print(f"失败投稿: {len(entries)} 个\n")
    for name in entries:
        err_file = FAILED_DIR / name / "error.txt"
        reason = ""
        if err_file.exists():
            for line in err_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("reason:"):
                    reason = line[7:].strip()
                    break
        print(f"  {name}  {reason[:60]}")


def main():
    parser = argparse.ArgumentParser(
        description="发布流水线 worker — 替代印务局 Agent")
    parser.add_argument("entry", nargs="?", default=None,
                        help="指定处理的文件夹名（不指定则处理所有 pending）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印不执行（跳过登录检查、锁定、发布、通知）")
    parser.add_argument("--retry", nargs="?", const="__all__", default=None,
                        metavar="FOLDER",
                        help="将 failed/ 中的投稿移回 pending/ 重投（不指定则全部重投）")
    parser.add_argument("--failed", action="store_true",
                        help="列出 failed/ 中的失败投稿")
    args = parser.parse_args()

    if args.failed:
        list_failed()
        return

    if args.retry is not None:
        entry = None if args.retry == "__all__" else args.retry
        retry_failed(entry)
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if args.entry:
        entries = [args.entry]
    else:
        entries = scan_pending()

    if not entries:
        print("pending/ 队列为空，无需处理。")
        return

    # 预览每个投稿的账号和标题
    for entry in entries:
        post_path = PENDING_DIR / entry / "post.md"
        hint = entry
        if post_path.exists():
            try:
                m, _ = parse_post_md(post_path)
                hint = f"{m.get('account_id', '?')} | 《{m.get('title', entry)}》"
            except Exception:
                pass
        print(f"  → {hint}")

    print(f"\npublish-worker | {now_str} | 待处理 {len(entries)} 个")
    sys.stdout.flush()

    success_count = 0
    fail_count = 0

    for entry in entries:
        try:
            ok = process_entry(entry, dry_run=args.dry_run)
            if ok:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  [FATAL] 未预期错误: {e}", file=sys.stderr)
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"完成 | 成功: {success_count} | 失败: {fail_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
