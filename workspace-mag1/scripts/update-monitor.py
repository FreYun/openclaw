#!/usr/bin/env python3
"""
生成 workspace-mag1/monitor/ 下的 Agent 对话监控文件。
每个 Agent 一个 MD 文件，显示最新一轮会话内容。
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

AGENTS_DIR = "/home/rooot/.openclaw/agents"
MONITOR_DIR = "/home/rooot/.openclaw/workspace-mag1/monitor"
CST = timezone(timedelta(hours=8))

# 要监控的 agent 列表（跳过 coder/main 等内部 agent）
WATCH_AGENTS = ["bot1", "bot2", "bot3", "bot4", "bot5", "bot6", "bot7", "bot8", "bot9", "bot10", "bot_main"]

BOT_NAMES = {
    "bot1": "来财妹妹",
    "bot2": "bot2",
    "bot3": "bot3",
    "bot4": "研报搬运工阿泽",
    "bot5": "宣妈慢慢变富",
    "bot6": "bot6",
    "bot7": "老K投资笔记",
    "bot8": "bot8",
    "bot9": "bot9",
    "bot10": "bot10",
    "bot_main": "魏忠贤",
}


def ts_to_cst(ts_ms):
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=CST)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def extract_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", "").strip())
                elif c.get("type") == "tool_use":
                    parts.append(f"[工具调用: {c.get('name', '?')}]")
                elif c.get("type") == "tool_result":
                    result_content = c.get("content", "")
                    if isinstance(result_content, list):
                        for rc in result_content:
                            if isinstance(rc, dict) and rc.get("type") == "text":
                                parts.append(f"[工具结果: {rc.get('text','')[:100]}...]")
                                break
                    elif isinstance(result_content, str):
                        parts.append(f"[工具结果: {result_content[:100]}...]")
        return "\n".join(parts).strip()
    return ""


def get_latest_session(agent_id):
    sessions_file = os.path.join(AGENTS_DIR, agent_id, "sessions", "sessions.json")
    if not os.path.exists(sessions_file):
        return None, None

    with open(sessions_file) as f:
        sessions = json.load(f)

    # 优先找 feishu 会话（跳过 agent:<id>:main 心跳/cron session）
    # 先在非 main 会话中找最新的，再回退到 main
    def is_real_conversation(key):
        return not key.endswith(":main")

    best = None
    best_ts = 0
    fallback = None
    fallback_ts = 0

    for key, sess in sessions.items():
        updated = sess.get("updatedAt", 0)
        if is_real_conversation(key):
            if updated > best_ts:
                best_ts = updated
                best = sess
        else:
            if updated > fallback_ts:
                fallback_ts = updated
                fallback = sess

    latest = best if best else fallback
    if not latest:
        return None, None

    session_file = latest.get("sessionFile", "")
    if not session_file or not os.path.exists(session_file):
        return None, None

    return latest, session_file


def parse_session_messages(session_file, max_messages=30):
    messages = []
    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "message":
                    msg = obj.get("message", {})
                    role = msg.get("role", "")
                    content = extract_text(msg.get("content", ""))
                    ts = obj.get("timestamp", "")
                    if role and content:
                        messages.append({
                            "role": role,
                            "content": content,
                            "timestamp": ts,
                        })
    except Exception as e:
        return [], str(e)

    return messages[-max_messages:], None


def generate_agent_md(agent_id):
    name = BOT_NAMES.get(agent_id, agent_id)
    latest_sess, session_file = get_latest_session(agent_id)

    if not latest_sess:
        return f"# {agent_id}（{name}）\n\n_无会话记录_\n"

    updated_ts = latest_sess.get("updatedAt", 0)
    updated_str = ts_to_cst(updated_ts) if updated_ts else "未知"
    session_id = latest_sess.get("sessionId", "?")
    chat_type = latest_sess.get("chatType", "?")
    channel = latest_sess.get("lastChannel", "?")

    messages, err = parse_session_messages(session_file)

    lines = [
        f"# {agent_id}（{name}）",
        f"",
        f"- **最后活动**：{updated_str}",
        f"- **会话 ID**：`{session_id}`",
        f"- **来源**：{channel} / {chat_type}",
        f"",
        f"---",
        f"",
        f"## 对话内容",
        f"",
    ]

    if err:
        lines.append(f"_读取失败：{err}_")
    elif not messages:
        lines.append("_会话为空_")
    else:
        for msg in messages:
            role_label = "👤 用户" if msg["role"] == "user" else "🤖 助手"
            content = msg["content"]
            # 截断超长内容
            if len(content) > 1000:
                content = content[:1000] + "\n\n_（内容过长已截断）_"
            lines.append(f"**{role_label}**")
            lines.append(f"")
            lines.append(content)
            lines.append(f"")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def generate_index(summaries):
    """生成 INDEX.md，按最后活动时间排序"""
    now = datetime.now(tz=CST).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Agent 对话监控",
        "",
        f"_更新时间：{now}_",
        "",
        "| Agent | 名称 | 最后活动 | 来源 |",
        "|-------|------|---------|------|",
    ]

    rows = []
    for agent_id in WATCH_AGENTS:
        latest_sess, _ = get_latest_session(agent_id)
        if not latest_sess:
            rows.append((0, agent_id, BOT_NAMES.get(agent_id, agent_id), "—", "—"))
            continue
        ts = latest_sess.get("updatedAt", 0)
        ts_str = ts_to_cst(ts) if ts else "—"
        channel = latest_sess.get("lastChannel", "?")
        chat_type = latest_sess.get("chatType", "?")
        rows.append((ts, agent_id, BOT_NAMES.get(agent_id, agent_id), ts_str, f"{channel}/{chat_type}"))

    rows.sort(key=lambda x: x[0], reverse=True)
    for _, agent_id, name, ts_str, source in rows:
        lines.append(f"| [{agent_id}](./{agent_id}.md) | {name} | {ts_str} | {source} |")

    return "\n".join(lines) + "\n"


def main():
    os.makedirs(MONITOR_DIR, exist_ok=True)

    for agent_id in WATCH_AGENTS:
        agent_dir = os.path.join(AGENTS_DIR, agent_id)
        if not os.path.exists(agent_dir):
            continue
        md = generate_agent_md(agent_id)
        out_path = os.path.join(MONITOR_DIR, f"{agent_id}.md")
        with open(out_path, "w") as f:
            f.write(md)
        print(f"✓ {agent_id}.md")

    index_md = generate_index({})
    with open(os.path.join(MONITOR_DIR, "INDEX.md"), "w") as f:
        f.write(index_md)
    print("✓ INDEX.md")
    print(f"\n完成，输出目录：{MONITOR_DIR}")


if __name__ == "__main__":
    main()
