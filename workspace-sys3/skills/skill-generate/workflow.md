# 📋 Skill 生成流程

---

## Step 1: 确认需求

| 必确认 | 说明 | 示例 |
|--------|------|------|
| **skill ID** | 英文小写+连字符，即目录名 | `earnings-digest` |
| **中文名** | 4-8 字 | 财报横评 |
| **slot** | 7 种之一 | `research` |
| **subType** | accessory/utility/research/scheduled 必填 | `research` |
| **scope** | 通用 or bot 专属 | 通用 |
| **MCP 依赖** | requires 字段 | `["xiaohongshu-mcp"]` 或无 |
| **是否需要 subSkills** | 内容多时拆分子文档 | 有/无 |

如果信息不全，先问 Admin 确认。

---

## Step 2: 创建 skill.json（必须第一步）

**这是最关键的步骤，没有 skill.json 的技能不会被系统识别。**

确定目标目录：
- 通用 skill → `/home/rooot/.openclaw/workspace/skills/{skill-id}/`
- bot 专属 → `/home/rooot/.openclaw/workspace-botN/skills/{skill-id}/`

直接创建 skill.json：

```json
{
  "name": "中文名",
  "icon": "📊",
  "slot": "research",
  "subType": "research",
  "desc": "一句话描述"
}
```

字段规则：
- `name` — 必填，中文简称
- `icon` — 必填，单个 Emoji，不要和现有技能重复
- `slot` — 必填，7 种之一：helm/armor/accessory/utility/research/boots/scheduled
- `subType` — accessory、utility、research、scheduled 的技能必填，helm/armor/boots 不填
- `desc` — 必填，一句话，不超过 30 字
- `requires` — 可选，依赖的宝石 ID 数组
- `infrastructure` — 可选，true 表示基础层不可装备
- `subSkills` — 可选，子文档列表

**创建后立即验证：**
```bash
python3 -c "import json; print(json.load(open('skill.json')))"
```

---

## Step 3: 创建 SKILL.md

这是 bot 执行技能时实际读取的文档。

结构要求：
1. 标题 + 一句话简介（与 skill.json desc 一致）
2. 子文档索引表（如有 subSkills）
3. 铁律/规则
4. 具体步骤/流程（可执行的，不是概念描述）
5. 安全/注意事项

控制在 200 行以内。

---

## Step 4: 创建 SubSkill 文件（如有）

每个 subSkill 文件：
- 标题匹配 skill.json 中的 subSkill name
- 包含可执行的具体步骤
- 不重复 SKILL.md 的内容
- 控制在 150 行以内

---

## Step 5: 创建 symlink（通用 skill 时）

```bash
# 给所有 bot 添加
for i in 1 2 3 4 5 6 7 8 9 10; do
  ln -s ../../workspace/skills/{skill-id} \
    /home/rooot/.openclaw/workspace-bot${i}/skills/{skill-id}
done
```

---

## Step 6: 验证

Read [validation.md](validation.md)，逐条检查。

重点：
- [ ] skill.json 存在且可被 JSON.parse
- [ ] slot 值在 7 种枚举内
- [ ] 需要 subType 的 slot 已填 subType
- [ ] SKILL.md 存在
- [ ] 告诉 Admin 去 dashboard 点 SYNC
