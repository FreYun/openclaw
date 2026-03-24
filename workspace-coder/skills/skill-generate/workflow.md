# 📋 Skill 生成流程

---

## Step 1: 需求分析

收到"创建 skill"需求后，先确认以下信息：

| 必确认 | 说明 | 示例 |
|--------|------|------|
| **skill 名称** | 英文小写 + 连字符 | `earnings-digest`, `xuanma-cover` |
| **中文名** | 4-8 字 | 财报横评, 宣妈封面生成 |
| **slot** | 6 种枚举之一 | `research` |
| **subType** | accessory/utility/research 必填 | `research` |
| **scope** | 通用（workspace/skills/）还是 bot 专属（workspace-botN/skills/） | 通用 |
| **是否依赖 MCP** | requires 字段 | `["xiaohongshu-mcp"]` 或 `[]` |
| **是否需要 subSkills** | 内容多时拆分 | 有/无 |

**如果 Admin 没给完整信息** → 用 Scope Lock 格式确认后再执行。

---

## Step 2: 扫描现有 skill

避免重复造轮子：

```bash
# 查看现有 skill 列表
ls /home/rooot/.openclaw/workspace/skills/
ls /home/rooot/.openclaw/workspace-bot*/skills/

# 看是否已有类似 skill
grep -r "desc.*关键词" /home/rooot/.openclaw/workspace/skills/*/skill.json
```

---

## Step 3: 生成文件

通过 Claude Code (tmux) 生成以下文件：

### 3a. skill.json

Prompt 模板：

```
Goal: Create skill.json for a new skill called "{skill-id}" in {target-dir}.

Files: {target-dir}/{skill-id}/skill.json

Context:
- This is an OpenClaw skill definition file
- Follow the schema from META-SKILL-README.md exactly

Constraint:
- name: "{中文名}"
- icon: "{emoji}"
- slot: "{slot}"
- subType: "{subType}"  (omit for helm/armor/boots)
- desc: "{一句话描述}"
- requires: [{依赖}]  (omit if none)
{如果有 subSkills:}
- subSkills: [每个子文档的 name/icon/file/desc]

Don't:
- Do NOT add any fields not in the META-SKILL-README schema
- Do NOT create any other files yet

Acceptance: `python3 -c "import json; json.load(open('{target-dir}/{skill-id}/skill.json'))"` succeeds.
```

### 3b. SKILL.md

Prompt 模板：

```
Goal: Create SKILL.md for the "{skill-id}" skill in {target-dir}/{skill-id}/.

Files: {target-dir}/{skill-id}/SKILL.md

Context:
- skill.json already exists: {粘贴 skill.json 内容}
- This is the main documentation file that bots read when executing the skill
- Follow the structure: 简介 → 子文档索引(如有) → 铁律 → 流程/用法 → 安全/注意事项

Constraint:
- Start with a one-line description matching skill.json desc
- If subSkills exist, include a 子文档索引 table
- Include practical step-by-step instructions, not just concepts
- Include code examples where relevant (MCP calls, scripts, etc.)
- Keep it under 200 lines

Don't:
- Do NOT create subSkill files yet (will do separately)
- Do NOT include content that belongs in subSkill files
- Do NOT add placeholder/TODO sections
```

### 3c. SubSkill 文件（如有）

逐个生成，每个文件一个 prompt：

```
Goal: Create "{subskill-file}" for the "{skill-id}" skill.

Files: {target-dir}/{skill-id}/{subskill-file}

Context:
- Parent skill: {粘贴 skill.json}
- Main SKILL.md: {粘贴 SKILL.md 关键段落}
- This subSkill covers: {子文档描述}

Constraint:
- Start with 标题（匹配 skill.json 中的 subSkill name）
- Include actionable steps, not just guidelines
- Reference parent SKILL.md for cross-cutting rules
- Keep it under 150 lines

Don't:
- Do NOT duplicate content from SKILL.md
- Do NOT create additional files
```

---

## Step 4: 创建 symlink（通用 skill 时）

如果是通用 skill，给需要的 bot 创建 symlink：

```bash
# 示例：给所有 bot 添加
for i in 1 2 3 4 5 6 7 8 9 10; do
  ln -s ../../workspace/skills/{skill-id} \
    /home/rooot/.openclaw/workspace-bot${i}/skills/{skill-id}
done

# 或只给特定 bot
ln -s ../../workspace/skills/{skill-id} \
  /home/rooot/.openclaw/workspace-bot7/skills/{skill-id}
```

---

## Step 5: 验证

Read [validation.md](validation.md) — 跑验收清单。

---

## Step 6: 通知

告诉 Admin：
- 生成了哪些文件
- 放在哪个目录
- 需要在 dashboard 点 SYNC 才能装备
