---
name: skill-evolution
description: >
  技能部专属 — 利用 OpenSpace 在沙盒中自动进化 skill，
  调度对应 bot 测试验证，汇总日报给魏忠贤播报。
---

# 技能进化（skill-evolution）

> 每日凌晨 cron 触发，或手动执行。全程在沙盒中操作，不影响线上 skill。

## 子文档索引

| 文档 | 何时读取 |
|------|----------|
| [test-cases.md](test-cases.md) | Phase 2 调度测试时，查找对应 skill 的测试用例 |
| [merge-guide.md](merge-guide.md) | 人工审批合并时参考 |

---

## 执行流程

### Phase 1 — 同步与进化

1. **同步沙盒**
   ```bash
   bash /home/rooot/.openclaw/scripts/sync-skills-to-sandbox.sh
   ```
   确认输出中 synced 数量和 skipped 原因。

2. **遍历沙盒 skill，逐个进化**

   对 `/home/rooot/.openclaw/skills-sandbox/` 下的每个 skill 目录：

   a. 先读该 skill 的 SKILL.md，理解它是做什么的

   b. 调用 OpenSpace MCP 工具 `fix_skill`：
      - `skill_dir`: `/home/rooot/.openclaw/skills-sandbox/{skill_name}`
      - `direction`: 根据 skill 内容给出针对性的改进方向，例如：
        - 知识型 skill → "审查内容准确性、补充遗漏的边界条件、优化表述清晰度"
        - 流程型 skill → "检查流程完整性、改进步骤顺序、强化错误处理指引"
        - 分析型 skill → "优化分析框架、补充数据源建议、改进输出结构"

   c. 检查返回结果：
      - `status: "success"` → 记录 skill 名和变更摘要（`change_summary`）
      - `status: "error"` 或无变化 → 跳过，记录原因

3. **汇总进化结果**

   记录：哪些 skill 被修改了、每个的变更摘要、哪些跳过了（及原因）。

### Phase 2 — 调度测试

4. **对每个被修改的 skill，安排测试**

   a. 读 [test-cases.md](test-cases.md) 找到该 skill 对应的测试用例

   b. 确定测试 bot：查看哪些 bot 装备了对应的线上版 skill

   c. 用 `send_message` 给测试 bot 发消息：

   ```
   【技能测试】

   请阅读以下沙盒版 skill 文件，按其指引完成测试任务：

   Skill 文件路径：/home/rooot/.openclaw/skills-sandbox/{skill_name}/SKILL.md

   测试任务：{从 test-cases.md 获取}

   完成后请回复：
   1. 执行结果（成功/失败，附输出摘要）
   2. 对比你平时装备的线上版，新版指令是否更清晰/更完善
   3. 发现的任何问题
   ```

5. **收集反馈**

   等待 bot 回复（同一个 isolated session 内）。如果 bot 未在合理时间内回复，记录"未收到反馈"。

### Phase 3 — 汇总日报

6. **生成日报**

   格式：
   ```
   【技能进化日报 {日期}】

   ## 进化概况
   - 沙盒同步：{N} 个 skill
   - 触发进化：{N} 个
   - 实际修改：{N} 个
   - 无变化：{N} 个

   ## 进化详情
   ### {skill_name}
   - 变更摘要：{change_summary}
   - 测试 bot：{bot_name}
   - 测试结果：{成功/失败}
   - Bot 反馈：{摘要}
   - 推荐操作：{建议合并 / 需人工审查 / 放弃}

   ## 待审批合并
   - {skill_name_1}: 建议合并（测试通过，bot 反馈正面）
   - {skill_name_2}: 需人工审查（bot 反馈有疑虑）

   合并指引见 merge-guide.md
   ```

7. **发送日报**

   用 `send_message` 发给 mag1（魏忠贤）。mag1 会播报到飞书群。

---

## 重要规则

1. **绝不操作线上 skill** — 所有进化仅在 `/home/rooot/.openclaw/skills-sandbox/` 中进行
2. **不自动合并** — 只生成建议，合并需人工审批
3. **测试任务不能有副作用** — 不发帖、不互动、不上报、不调真实 MCP 服务
4. **每次只进化一批** — 不要一次改太多 skill，优先改质量最差的或最近出过问题的
5. **记录所有操作** — 在 memory/ 下记录每次进化的详细日志
