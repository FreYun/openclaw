# 🧬 技能生成器（skill-generate）

> 按照 META-SKILL-README.md 规范，通过 Claude Code 自动生成 skill 文件。

## 前置知识

**必读：** `workspace/skills/META-SKILL-README.md` — skill 系统完整规范（slot 枚举、subType、命名约定、验证清单）

---

## 子文档索引

| 文档 | 何时读取 | 用途 |
|------|---------|------|
| [workflow.md](workflow.md) | 收到"创建 skill"需求时 | 完整生成步骤 |
| [validation.md](validation.md) | skill 文件写完后 | 验收清单 |

---

## 铁律

1. **所有 skill 文件通过 Claude Code 生成** — 不直接写文件
2. **生成前先确认 slot 和 scope** — 通用 skill 放 `workspace/skills/`，bot 专属放 `workspace-botN/skills/`
3. **生成后必须跑验证** — 见 validation.md
4. **不自动装备** — 生成文件后提醒 Admin 在 dashboard 点 SYNC

---

## 快速参考：slot 枚举

| slot | 部位 | 槽数 | subType |
|------|------|------|---------|
| `helm` | 工种 | 1 | 无 |
| `armor` | 职业 | 1 | 无 |
| `accessory` | 风格 | 2 | `content` / `image` |
| `utility` | 通用技能 | 4 | `duty` / `scheduled` |
| `research` | 研究技能 | 6 | `research` / `general` |
| `boots` | 策略 | 1 | 无 |

## 快速参考：宝石依赖

| 宝石 ID | 类型 |
|---------|------|
| `xiaohongshu-mcp` | per-bot (18060-18070) |
| `image-gen-mcp` | shared (18085) |
| `compliance-mcp` | shared (18090) |
| `research-gateway` | per-bot (18080) |
