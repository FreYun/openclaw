---
name: skill-standardize
description: >
  将进化后膨胀的 skill 拆分为主文件（3-5KB 路由器）+ 子文件的标准结构。
  减少每次加载的 token 消耗，agent 按需读取子文件。
---

# 技能标准化（skill-standardize）

> 进化让 skill 变好，标准化让 skill 变轻。

## 触发时机

研究部在 dashboard 批准进化后，sys2 评估该 skill 是否需要标准化：
- SKILL.md > 5KB → 需要标准化
- SKILL.md ≤ 5KB → 跳过

## 目标结构（参考 xhs-op）

```
{skill_name}/
  SKILL.md          ← 主文件（3-5KB），路由器
  skill.json        ← 不动
  analysis.md       ← 子文件（按功能模块拆分）
  templates.md      ← 子文件
  ...
```

### 主文件（SKILL.md）必须包含

1. **Frontmatter**（name + description）
2. **一句话定位**
3. **子文档索引表**：
   ```
   | 文档 | 何时读取 |
   |------|----------|
   | [analysis.md](analysis.md) | 执行分析时 |
   | [templates.md](templates.md) | 生成报告时 |
   ```
4. **铁律**（核心约束，3-5 条）
5. **高层流程概览**（步骤名 + 一句话描述，不展开细节）

### 子文件拆分原则

- 每个子文件对应一个**独立功能模块**（工具参考、分析框架、输出模板等）
- 子文件应自包含 — 读了就能执行，不需要回头看主文件
- 不要拆太碎 — 如果子文件 < 1KB，合并到相邻模块

## 执行流程

1. 读目标 skill 的 SKILL.md，理解完整内容
2. 识别可独立拆分的功能模块（通常 3-5 个）
3. 规划拆分方案：主文件保留什么，每个子文件包含什么
4. 执行拆分：
   - 写入各子文件
   - 重写主文件为路由器（保留 frontmatter、铁律、索引表、高层流程）
5. 验证：主文件 ≤ 5KB，所有子文件都在索引表中
6. 记录到 `memory/changelog.md`

## 铁律

1. **不改内容语义** — 只重构文件结构，不修改、删除或新增任何指导内容
2. **不动 skill.json** — 元数据不属于标准化范围
3. **保持 frontmatter** — name 和 description 不变
4. **线上直接操作** — 标准化在 `workspace/skills/{name}/` 上执行（此时已通过审批合并）
