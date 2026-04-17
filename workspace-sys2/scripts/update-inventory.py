#!/usr/bin/env python3
"""
技能部目录刷新脚本
更新 workspace-sys2/memory/ 下的所有目录文件
"""

import os, json, re
from datetime import datetime, timezone, timedelta

BASE = "/home/rooot/.openclaw"
SKILLS_SRC = f"{BASE}/workspace/skills"
MEMORY = f"{BASE}/workspace-sys2/memory"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(tz=CST).strftime("%Y-%m-%d %H:%M")

os.makedirs(MEMORY, exist_ok=True)

BOTS = [f"bot{i}" for i in range(1, 11)]
BOT_NAMES = {
    "bot1": "来财妹妹", "bot2": "狗哥说财", "bot3": "meme爱基金",
    "bot4": "研报搬运工阿泽", "bot5": "宣妈慢慢变富", "bot6": "爱理财的James",
    "bot7": "老K投资笔记", "bot8": "bot8", "bot9": "bot9", "bot10": "bot10",
}

def get_skill_desc(skill_dir):
    md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(md):
        return "（无 SKILL.md）"
    with open(md, encoding="utf-8", errors="ignore") as f:
        content = f.read(800)
    m = re.search(r'description:\s*(.+)', content)
    if m:
        return m.group(1).strip()[:80]
    # Try first heading after frontmatter
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('#') and len(line) > 2:
            return line.lstrip('#').strip()[:80]
    return "（无描述）"


# ── 1. 共有 skill 目录 ─────────────────────────────────────────
shared = sorted([
    s for s in os.listdir(SKILLS_SRC)
    if os.path.isdir(os.path.join(SKILLS_SRC, s))
    and not s.endswith('.zip') and not s.startswith('.')
])

lines = [
    "# 共有 Skill 目录",
    "",
    f"_更新时间：{NOW}_",
    "",
    f"共 {len(shared)} 个共有 skill，源目录：`workspace/skills/`",
    "",
    "| Skill 名称 | 描述 |",
    "|-----------|------|",
]
for s in shared:
    desc = get_skill_desc(os.path.join(SKILLS_SRC, s))
    lines.append(f"| `{s}` | {desc} |")

with open(f"{MEMORY}/shared-skills.md", "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"✓ shared-skills.md ({len(shared)} skills)")


# ── 2. 各 bot 私有 skill ──────────────────────────────────────
lines = [
    "# 私有 Skill 目录（各 Agent 独有）",
    "",
    f"_更新时间：{NOW}_",
    "",
]

for bot in BOTS:
    ws = f"{BASE}/workspace-{bot}/skills"
    if not os.path.exists(ws):
        continue
    privates = []
    for s in sorted(os.listdir(ws)):
        p = os.path.join(ws, s)
        if os.path.isdir(p) and not os.path.islink(p):
            desc = get_skill_desc(p)
            privates.append((s, desc))
    if privates:
        name = BOT_NAMES.get(bot, bot)
        lines.append(f"## {bot}（{name}）")
        lines.append("")
        lines.append("| Skill | 描述 |")
        lines.append("|-------|------|")
        for s, d in privates:
            lines.append(f"| `{s}` | {d} |")
        lines.append("")

# workspace-mag1 独有 skill
main_skills = f"{BASE}/workspace-mag1/skills"
if os.path.exists(main_skills):
    privates = []
    for s in sorted(os.listdir(main_skills)):
        p = os.path.join(main_skills, s)
        if os.path.isdir(p):
            desc = get_skill_desc(p)
            privates.append((s, desc))
    if privates:
        lines.append("## mag1（魏忠贤）")
        lines.append("")
        lines.append("| Skill | 描述 |")
        lines.append("|-------|------|")
        for s, d in privates:
            lines.append(f"| `{s}` | {d} |")
        lines.append("")

with open(f"{MEMORY}/private-skills.md", "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"✓ private-skills.md")


# ── 3. MCP 插件清单 ────────────────────────────────────────────
lines = [
    "# MCP 插件清单（mcporter.json）",
    "",
    f"_更新时间：{NOW}_",
    "",
    "| Agent | 插件列表 |",
    "|-------|---------|",
]

configs = {
    **{f"bot{i}": f"{BASE}/workspace-bot{i}/config/mcporter.json" for i in range(1, 11)},
    "mag1": f"{BASE}/workspace-mag1/config/mcporter.json",
    "mcp_publisher": f"{BASE}/workspace-sys1/config/mcporter.json",
}
for agent, path in sorted(configs.items()):
    if not os.path.exists(path):
        continue
    with open(path) as f:
        d = json.load(f)
    servers = list(d.get("mcpServers", {}).keys()) if isinstance(d, dict) else []
    name = BOT_NAMES.get(agent, agent)
    lines.append(f"| {agent}（{name}） | {', '.join(f'`{s}`' for s in servers)} |")

with open(f"{MEMORY}/plugins.md", "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"✓ plugins.md")


# ── 4. Symlink 同步状态 ────────────────────────────────────────
lines = [
    "# Symlink 同步状态",
    "",
    f"_更新时间：{NOW}_",
    "",
]

missing_any = False
for skill in shared:
    missing = []
    for i in range(1, 11):
        p = f"{BASE}/workspace-bot{i}/skills/{skill}"
        if not os.path.exists(p):
            missing.append(f"bot{i}")
    if missing:
        lines.append(f"- ⚠️ `{skill}` 缺失：{', '.join(missing)}")
        missing_any = True

if not missing_any:
    lines.append("✅ 所有共有 skill 的 symlink 均已同步到所有 bot")
else:
    lines.append("")
    lines.append("_注：私有 skill 不应同步，以上仅检查共有 skill_")

with open(f"{MEMORY}/sync-status.md", "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"✓ sync-status.md")

print(f"\n完成，输出目录：{MEMORY}")
