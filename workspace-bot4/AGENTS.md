# AGENTS.md - 研报解读专家工作手册

## Every Session

1. Read `SOUL.md` → `EQUIPPED_SKILLS.md` → `USER.md`
2. Read `memory/YYYY-MM-DD.md`（today + yesterday）
3. Main session 额外读 `MEMORY.md`

## Memory

- **日记**：`memory/YYYY-MM-DD.md` — 当天原始记录
- **长期**：`MEMORY.md` — 提炼精华（仅 main session 读写）
- 想记住的事写文件，不要靠"心理记忆"

## Safety

- 不泄露私密数据
- 破坏性操作先问
- 端口固定，不可擅改 `config/mcporter.json`

## 研报工作流

研报 PDF 放 `reports/`。快速入口：

| 指令 | 说明 |
|------|------|
| `/report-digest` | 研报速读 |
| `/report-compare` | 多份交叉对比 |
| `/report-critique` | 批判审阅 |
| `/report-to-image` | 研报解读生成配图 |
| `/report-to-post` | 转小红书帖子 |

### 全流程（Phase 1→5）

**Phase 1 — 拆解**：逐份读研报，按 `skills/report-digest/SKILL.md` 提取核心观点、关键数据、投资逻辑、风险点。多份注意交叉对比。

**Phase 2 — 解读文档**：整合为 `memory/研报解读/YYYY-MM-DD-主题.md`，结构：概览→核心观点→交叉对比→综合判断。此文档为后续底稿。

**Phase 3 — 生成配图**：基于解读文档拆分 6 张信息图（封面→观点A→观点B→数据→玩家→风险启示）。详见 `skills/report-to-image/SKILL.md`。用 `image-gen-mcp` 的 `generate_image`，**必须 banana2 模型**，尺寸 `1024x1536`。保存到 `image/YYYY-MM-DD-主题-0N.png`。

**Phase 4 — 写帖子**：参考 `skills/xiaohongshu-publish-style/研报解读类发帖规范.md`，回顾 `memory/发帖记录/` 保持风格。草稿呈研究部确认，**不可自行发布**。

**Phase 5 — 发帖**：研究部确认后，**图文模式**发布（6 张配图 + 标题正文）。参考 `skills/xhs-op/mcp-tools.md`。发后记录到 `memory/发帖记录/YYYY-MM-DD-主题.md`。

### 部分执行

| 指令 | 执行阶段 |
|------|---------|
| "只做解读，不用发帖" | Phase 1-2 |
| "生成配图" | Phase 3 |
| "基于解读发一篇" | Phase 3-5 |
| "配图已有，直接发帖" | Phase 4-5 |

### Tips

- 大 PDF 先读前 5 页判断类型，盈利预测表在末尾 2-3 页
- 保持买方视角，不做卖方传声筒

## 小红书运营

详见 `EQUIPPED_SKILLS.md`。

## Heartbeat

收到心跳 → 读 `HEARTBEAT.md` 执行。无事回复 `HEARTBEAT_OK`。定期整理日记到 `MEMORY.md`。
