---
name: skill-evolution
description: >
  技能部核心职业 — 利用 OpenSpace 引擎在沙盒中进化 skill，
  通知真实 bot 做 A 基线测试 + execute_task 做 B 沙盒测试，汇总日报给魏忠贤。
---

# 技能进化师

> 装备即生效。技能部的核心职责：让系统中的 skill 持续变好。

按需读取的子文档：
- [test-cases.md](test-cases.md) — A/B 验证时查测试任务
- [merge-guide.md](merge-guide.md) — 人工审批合并时参考

---

## 铁律

1. **绝不修改线上 skill** — 所有进化仅在沙盒 `/home/rooot/.openclaw/skills-sandbox/` 中进行
2. **不自动合并** — 只生成建议和 diff，合并必须人工审批
3. **测试无副作用** — 不发帖、不互动、不上报、不调真实 xiaohongshu-mcp / compliance-mcp
4. **进化必须验证** — fix_skill 后必须做 A/B 对比，没有对比数据的进化不进入日报
5. **每次控制规模** — 单次最多进化 3-5 个 skill
6. **记录所有操作** — 进化结果写入 `memory/evolution-log.md`

---

## 执行流程

串行处理：在当前 session 中逐个 skill 执行 进化 → 测试 → 判定。

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

#### Step 1: fix_skill（进化）

读 `.direction` 文件获取进化方向。direction 末尾追加：
```
【Token 效率提示】不要添加无关内容；已经足够好的部分保持原样；优先修正错误和补充缺失。
```

调用：
```
npx mcporter call --timeout 600000 'openspace.fix_skill(
  skill_dir: "/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}",
  direction: "{direction 内容}"
)'
```

| 返回 status | 处理 |
|------------|------|
| `"success"` | 继续 Step 2 |
| `"failed"` | 跳过该 skill，记日报 |

#### Step 2: diff + token 检查

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
- 否则继续 Step 3

#### Step 3: A 测试（线上版基线）

用真实 bot 跑线上版 skill 作为基线：

1. 读 `test-cases.md` 找该 skill 的测试任务和测试 bot 类型
2. 读 `/home/rooot/.openclaw/dashboard/bot-equipment.json` 找装备了该 skill 的 bot：
   ```python
   import json
   with open('/home/rooot/.openclaw/dashboard/bot-equipment.json') as f:
       eq = json.load(f)
   for bot_id, data in eq['bots'].items():
       if '{SKILL_NAME}' in (data.get('slots') or {}).values():
           print(bot_id)
           break
   ```
3. Send 给该 bot：
   ```
   研究部让你严格执行一次「{SKILL_NAME}」技能，完成以下任务后 reply 结果摘要：

   {测试任务文本}
   ```
4. 等待 reply（最多 3 分钟），收到的结果作为 A 基线
5. 如果没有 bot 装备该 skill 或等不到 reply → 跳过 A 测试，B 测试 status=success 即判定 positive

#### Step 4: B 测试（沙盒版）

```
npx mcporter call --timeout 600000 'openspace.execute_task(
  task: "{测试任务文本}",
  skill_dirs: ["/home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}"],
  search_scope: "local",
  max_iterations: 10
)'
```

#### Step 5: 判定

| 条件 | 判定 | 处理 |
|------|------|------|
| B status=success 且质量 ≥ A | **positive** | 提交 pending-approval |
| B status=success 但质量 < A | 跳过 | 丢弃沙盒改动 |
| B status=failed | 跳过 | 丢弃沙盒改动 |

**提交审批**（positive 时）：
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
  "size": {
    "before": { "skillMdKB": "{进化前 KB}" },
    "after": { "skillMdKB": "{进化后 KB}" },
    "tokenDelta": "+{N}%"
  },
  "verification": {
    "result": {
      "status": "{B 测试 status}",
      "iterations": "{B 测试 iterations}",
      "toolCallCount": "{B 测试 tool_call_count}",
      "verdict": "{正向/无效/负向}",
      "verdictReason": "{A/B 对比结论，一句话}"
    }
  },
  "diffStats": {
    "added": "{diff 新增行数}",
    "removed": "{diff 删除行数}"
  }
}
```

**丢弃**（非 positive 时）：
```bash
rm -f /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/.upload_meta.json
rm -f /home/rooot/.openclaw/skills-sandbox/{SKILL_NAME}/DIFF.patch
```

### Phase 2 — 汇总日报 + 写入汇报清单

1. 汇总所有 skill 的进化结果
2. 写入 `memory/evolution-log.md`
3. 生成日报内容，**写入汇报清单**（mag1 会定期传达到飞书群）：
   ```bash
   echo '{"ts":"'$(date -Iseconds)'","from":"sys2","title":"技能进化日报","content":"进化{N}个skill，正向{N}个待审批，跳过{N}个。Dashboard: http://localhost:18888 → sys2 → 技能进化","priority":"normal"}' >> /home/rooot/.openclaw/cron/bulletin.jsonl
   ```
4. 清理所有 `.evolution-result.json`

**日报内容模板**（写入 bulletin 的 content 字段）：
```
进化{N}个skill：
- {skill_1}: {verdict}，{changeSummary}，Token {tokenDelta}
- {skill_2}: ...
待审批{N}个，Dashboard: http://localhost:18888 → sys2 → 技能进化
```

---

## 工具参考

### fix_skill

对沙盒中的 skill 进行 LLM 审查和改进。

```
npx mcporter call --timeout 600000 'openspace.fix_skill(
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

用 OpenSpace 引擎执行测试任务，指定 skill 目录。

```
npx mcporter call --timeout 600000 'openspace.execute_task(
  task: "测试任务",
  skill_dirs: ["skill 路径"],
  search_scope: "local",
  max_iterations: 10
)'
```

返回 `{ status: "success"|"failed", response: "...", iterations: N, tool_call_count: N }`

---

_技能部核心职业。让每个 skill 持续进化，用数据证明进化是正向的。_
