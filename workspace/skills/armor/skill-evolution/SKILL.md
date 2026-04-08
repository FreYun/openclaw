---
name: skill-evolution
description: >
  技能部核心职业 — 利用 OpenSpace 引擎在沙盒中进化 skill，
  fix_skill 定向修复 + execute_task 实战验证与自动进化，提交审批，汇总日报。
---

# 技能进化师

> 装备即生效。技能部的核心职责：让系统中的 skill 持续变好。

按需读取的子文档：
- [merge-guide.md](merge-guide.md) — 人工审批合并时参考

---

## 铁律

1. **绝不修改线上 skill** — 所有进化仅在沙盒 `/home/rooot/.openclaw/skills-sandbox/` 中进行
2. **不自动合并** — 只生成建议和 diff，合并必须人工审批
3. **测试无副作用** — 不发帖、不互动、不上报、不调真实 xiaohongshu-mcp / compliance-mcp
4. **每次控制规模** — 单次最多进化 3-5 个 skill
5. **记录所有操作** — 进化结果写入 `memory/evolution-log.md`

---

## 执行流程

串行处理：对每个候选 skill 执行 fix → execute 验证 → diff 检查 → 提交审批。

### Phase 0 — 同步与筛选

```bash
bash /home/rooot/.openclaw/scripts/sync-skills-to-sandbox.sh
```

**筛选候选**（优先 .direction 文件）：
```bash
# 用户指定（有 .direction）
for d in /home/rooot/.openclaw/skills-sandbox/*/; do
  name=$(basename "$d")
  [ "$name" = "pending-approval" ] && continue
  [ -f "$d/.exclude" ] && continue
  [ -f "$d/.upload_meta.json" ] && continue
  [ -f "$d/.direction" ] && echo "$name [direction]"
done
```
- 有 `.direction` → 直接全部进化（最多 5 个）
- 没有 → 从候选池自动选 3 个：
```bash
for d in /home/rooot/.openclaw/skills-sandbox/*/; do
  name=$(basename "$d")
  [ "$name" = "pending-approval" ] && continue
  [ -f "$d/.upload_meta.json" ] && continue
  [ -f "$d/.exclude" ] && continue
  [ -f "$d/.evolution-result.json" ] && continue
  live="/home/rooot/.openclaw/workspace/skills/$name/SKILL.md"
  [ ! -f "$live" ] || [ ! -s "$live" ] && continue
  echo "$name $(wc -c < "$live")B"
done
```
自动选中的 skill，快速读 SKILL.md 诊断问题，写 `.direction` 文件。

### Phase 1 — 逐个进化

对每个候选 skill 执行以下步骤：

#### Step 1: fix_skill（定向修复）

读 `.direction` 文件获取进化方向。direction 末尾追加：
```
【Token 效率提示】不要添加无关内容；已经足够好的部分保持原样；优先修正错误和补充缺失。
```

调用：
```
npx mcporter call --timeout 600000 --config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json 'openspace.fix_skill(
  skill_dir: "/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}",
  direction: "{direction 内容}"
)'
```

| 返回 status | 处理 |
|------------|------|
| `"success"` | 继续 Step 2 |
| `"failed"` | 跳过该 skill，记日报 |

#### Step 2: execute_task（实战验证 + 自动进化）

用 execute_task 给沙盒版 skill 一个真实测试任务，验证可用性，同时触发自动进化（DERIVED/CAPTURED）。

**根据 skill 类型构造测试任务**：
| skill 类型 | 测试任务示例 |
|-----------|------------|
| 分析/研究类 | "用 {SKILL_NAME} 分析一个具体案例，输出结构化结果" |
| 写作/内容类 | "用 {SKILL_NAME} 写一段 200 字短文（不发布，只输出文本）" |
| 工具指南类 | "按 {SKILL_NAME} 的流程描述，列出操作步骤和注意事项" |
| 角色/流程类 | "描述 {SKILL_NAME} 定义的职责边界和关键规则" |

调用：
```
npx mcporter call --timeout 600000 --config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json 'openspace.execute_task(
  task: "{测试任务}",
  skill_dirs: ["/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}"],
  search_scope: "local",
  max_iterations: 10
)'
```

**处理返回**：

| 返回 | 处理 |
|------|------|
| `status: "success"` | 记录验证通过，检查 `evolved_skills` 是否有自动进化 |
| `status: "failed"` | 记录失败原因，skill 仍可提交审批（fix_skill 的改动可能有效） |

**自动进化处理**：
- 如果返回中有 `evolved_skills`，说明 execute_task 自动触发了 DERIVED 或 CAPTURED 进化
- **DERIVED/CAPTURED 产生的新文件必须归入原 skill 目录**：
  - OpenSpace 可能创建新目录（如 `xhs-pub-enhanced`），**不要**把新目录作为独立 skill 提交
  - 把新生成的 `.md` 文件移入原 skill 的沙盒目录下，作为子文件：
    ```bash
    # 示例：DERIVED 产物 xhs-pub-enhanced → 归入 xhs-pub
    NEW_DIR="/home/rooot/.openclaw/skills-sandbox/{DERIVED_NAME}"
    PARENT_DIR="/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}"
    if [ -d "$NEW_DIR" ] && [ -d "$PARENT_DIR" ]; then
      for f in "$NEW_DIR"/*.md; do
        fname=$(basename "$f")
        # 避免覆盖已有的 SKILL.md
        [ "$fname" = "SKILL.md" ] && fname="{DERIVED_NAME}.md"
        cp "$f" "$PARENT_DIR/$fname"
      done
      rm -rf "$NEW_DIR"
    fi
    ```
  - 同时更新原 skill 的 `skill.json`，在 `subSkills` 中添加新子文件的引用
- 归并后的变更统一在原 skill 的 diff 和审批中体现

#### Step 3: diff + token 检查

```bash
diff -ruN /home/rooot/.openclaw/workspace/skills/{SKILL_NAME}/ \
          /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/ \
          --exclude=skill.json --exclude=.skill_id --exclude=.upload_meta.json \
          --exclude=DIFF.patch --exclude=.direction --exclude=.evolution-result.json --exclude=.exclude \
          > /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/DIFF.patch

BEFORE=$(wc -c < /home/rooot/.openclaw/workspace/skills/{SKILL_NAME}/SKILL.md)
AFTER=$(wc -c < /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/SKILL.md)
echo "Token growth: $(( (AFTER - BEFORE) * 100 / BEFORE ))%"
```

- diff 为空 → 跳过（无实质变更）
- 否则继续 Step 4

#### Step 4: 提交审批

```bash
mkdir -p /home/rooot/.openclaw/skills-sandbox/pending-approval/{SKILL_NAME}
cp /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/*.md \
   /home/rooot/.openclaw/skills-sandbox/pending-approval/{SKILL_NAME}/
cp /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/DIFF.patch \
   /home/rooot/.openclaw/skills-sandbox/pending-approval/{SKILL_NAME}/
```

必须生成 `pending-approval/{SKILL_NAME}/proposal.json`：
```json
{
  "skillName": "{SKILL_NAME}",
  "status": "pending",
  "createdAt": "{ISO 时间}",
  "evolution": {
    "changeSummary": "{fix_skill 返回的 change_summary}",
    "createdBy": "openspace/claude-sonnet-4-6",
    "changes": ["变更点1", "变更点2"]
  },
  "verification": {
    "executeTask": {
      "status": "{success|failed|skipped}",
      "iterations": "{N}",
      "toolCallCount": "{N}",
      "autoEvolved": "{DERIVED/CAPTURED skill 名，无则 null}"
    }
  },
  "size": {
    "before": { "skillMdKB": "{进化前 KB}" },
    "after": { "skillMdKB": "{进化后 KB}" },
    "tokenDelta": "+{N}%"
  },
  "diffStats": {
    "added": "{diff 新增行数}",
    "removed": "{diff 删除行数}"
  }
}
```

### Phase 2 — 汇总日报 + 写入汇报清单

1. 汇总所有 skill 的进化结果
2. 写入 `memory/evolution-log.md`
3. 生成日报内容，**写入汇报清单**（mag1 会定期传达到飞书群）：
   ```bash
   echo '{"ts":"'$(date -Iseconds)'","from":"sys2","title":"技能进化日报","content":"进化{N}个skill，待审批{N}个，跳过{N}个。Dashboard: http://localhost:18888 → sys2 → 技能进化","priority":"normal"}' >> /home/rooot/.openclaw/cron/bulletin.jsonl
   ```
4. 清理所有 `.evolution-result.json`

**日报内容模板**（写入 bulletin 的 content 字段）：
```
进化{N}个skill：
- {skill_1}: fix={changeSummary}，execute={success/failed}，Token {tokenDelta}
- {skill_2}: ...
待审批{N}个，Dashboard: http://localhost:18888 → sys2 → 技能进化
```

---

## 工具参考

所有工具调用需指定 mcporter 配置：
```
--config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json
```

### fix_skill

对沙盒中的 skill 进行 LLM 审查和定向改进。适用于已知问题的修复。

```
npx mcporter call --timeout 600000 --config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json 'openspace.fix_skill(
  skill_dir: "沙盒路径",
  direction: "改进方向"
)'
```

| 参数 | 说明 |
|------|------|
| `skill_dir` | 沙盒中的 skill 目录绝对路径 |
| `direction` | 改进方向（越具体越好，避免模糊指令如"优化清晰度"） |

**direction 维度参考**：
- 精确性：指令/参数/格式是否正确
- 可执行性：agent 能否无歧义逐步执行
- 容错性：失败场景是否有兜底
- scope 匹配：描述与实际用途是否一致

返回 `{ status: "success"|"failed", new_skill: { change_summary, ... } }`

### execute_task

用 OpenSpace 引擎执行真实任务。会自动匹配 skill、执行、分析，并在需要时自动触发进化（FIX/DERIVED/CAPTURED）。

```
npx mcporter call --timeout 600000 --config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json 'openspace.execute_task(
  task: "测试任务描述",
  skill_dirs: ["/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}"],
  search_scope: "local",
  max_iterations: 10
)'
```

| 参数 | 说明 |
|------|------|
| `task` | 自然语言任务描述 |
| `skill_dirs` | skill 目录列表，OpenSpace 自动注册并在执行中使用 |
| `search_scope` | `"local"` 只搜本地 skill，`"all"` 搜本地+云端 |
| `max_iterations` | 最大迭代次数（默认 20，建议设 10 控制成本） |

返回：
```json
{
  "status": "success|failed",
  "response": "任务执行结果",
  "iterations": 5,
  "tool_call_count": 12,
  "evolved_skills": [
    {
      "name": "xxx",
      "origin": "derived|captured|fixed",
      "change_summary": "...",
      "upload_ready": true
    }
  ]
}
```

**三种自动进化模式**（由 execute_task 内部触发）：
| 模式 | 触发条件 | 结果 |
|------|---------|------|
| **FIX** | 执行中发现 skill 指令有误 | 原地修复当前 skill |
| **DERIVED** | 发现可以从已有 skill 增强/组合 | 创建新 skill，保留原版 |
| **CAPTURED** | 发现全新的可复用 pattern | 创建全新 skill（无 parent） |

### search_skills

搜索本地和云端 skill 库，用于发现可复用的 skill。

```
npx mcporter call --timeout 60000 --config /home/rooot/.openclaw/workspace-sys2/config/mcporter.json 'openspace.search_skills(
  query: "搜索关键词",
  source: "all",
  limit: 10
)'
```

返回匹配的 skill 列表，包含来源（local/cloud）、相关度评分、skill 描述。
云端 skill 会自动导入到本地（`auto_import: true`）。

---

_技能部核心职业。fix_skill 定向修复 + execute_task 实战验证，让每个 skill 持续进化。_
