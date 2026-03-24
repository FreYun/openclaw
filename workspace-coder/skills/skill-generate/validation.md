# ✅ Skill 质量检查

> 生成 skill 文件后必须过这张清单。

---

## 自动验证（直接跑命令）

```bash
SKILL_DIR="/path/to/skill-dir"

# 1. skill.json 是合法 JSON
python3 -c "import json; d=json.load(open('$SKILL_DIR/skill.json')); print('✓ JSON valid')"

# 2. 必填字段存在
python3 -c "
import json, sys
d = json.load(open('$SKILL_DIR/skill.json'))
required = ['name', 'icon', 'slot', 'desc']
missing = [k for k in required if k not in d]
if missing:
    print(f'✗ Missing fields: {missing}')
    sys.exit(1)
print('✓ Required fields present')
"

# 3. slot 值合法
python3 -c "
import json, sys
d = json.load(open('$SKILL_DIR/skill.json'))
valid_slots = {'helm', 'armor', 'accessory', 'utility', 'research', 'boots'}
if d['slot'] not in valid_slots:
    print(f'✗ Invalid slot: {d[\"slot\"]}')
    sys.exit(1)
print(f'✓ Slot: {d[\"slot\"]}')
"

# 4. subType 检查
python3 -c "
import json, sys
d = json.load(open('$SKILL_DIR/skill.json'))
needs_subtype = {'accessory', 'utility', 'research'}
no_subtype = {'helm', 'armor', 'boots'}
slot = d['slot']
has_sub = 'subType' in d
if slot in needs_subtype and not has_sub:
    print(f'✗ {slot} slot requires subType')
    sys.exit(1)
if slot in no_subtype and has_sub:
    print(f'✗ {slot} slot should NOT have subType')
    sys.exit(1)
print('✓ subType check passed')
"

# 5. SKILL.md 存在
[ -f "$SKILL_DIR/SKILL.md" ] && echo "✓ SKILL.md exists" || echo "✗ SKILL.md missing"

# 6. subSkill 文件都存在
python3 -c "
import json, os, sys
d = json.load(open('$SKILL_DIR/skill.json'))
if 'subSkills' not in d:
    print('✓ No subSkills defined')
    sys.exit(0)
missing = []
for ss in d['subSkills']:
    path = os.path.join('$SKILL_DIR', ss['file'])
    if not os.path.exists(path):
        missing.append(ss['file'])
if missing:
    print(f'✗ Missing subSkill files: {missing}')
    sys.exit(1)
print(f'✓ All {len(d[\"subSkills\"])} subSkill files exist')
"
```

---

## 人工检查清单

| # | 检查项 | Pass 条件 |
|---|--------|----------|
| 1 | **icon 不重复** | 与同 slot 的现有 skill icon 不同 |
| 2 | **name 简洁** | 4-8 字中文 |
| 3 | **desc 精确** | 一句话，≤30 字，准确描述功能 |
| 4 | **SKILL.md 结构** | 有简介、铁律（或注意事项）、实际用法/步骤 |
| 5 | **SKILL.md 可操作** | bot 读完能直接执行，不需要猜 |
| 6 | **subSkill 不重叠** | 各子文档职责分明，无重复内容 |
| 7 | **requires 正确** | 依赖的 MCP 在 gem-registry.json 中存在 |
| 8 | **目录位置正确** | 通用 → `workspace/skills/`，专属 → `workspace-botN/skills/` |

---

## 常见错误

| 错误 | 症状 | 修复 |
|------|------|------|
| JSON 逗号多余 | `skill.json` parse 失败 | 删除最后一个属性后面的逗号 |
| helm/armor/boots 加了 subType | 装备系统报错 | 删除 subType 字段 |
| accessory/utility/research 没加 subType | 装备系统报错 | 按枚举表补上 |
| subSkill file 路径错误 | dashboard 找不到子文档 | 用相对路径，相对于 skill 目录 |
| SKILL.md 太长（>300行） | bot 读不完、上下文浪费 | 拆成 subSkills |
| 重复的 icon | dashboard 不好区分 | 换一个 |
| desc 太长 | dashboard 显示截断 | 控制在 30 字内 |
