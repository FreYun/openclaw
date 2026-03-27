# Meta Skill README — 技能创建指南

> 本文档是EQS的完整参考手册。新建技能时，照着 `skill.json` 模板填写即可。

---

## 1. skill.json 模板

```jsonc
{
  "name": "技能显示名",            // 必填，中文简称
  "icon": "📊",                   // 必填，一个 Emoji
  "slot": "research",             // 必填（除非 infrastructure），见下方枚举
  "desc": "一句话描述这个技能做什么",  // 必填
  "subType": "research",          // 部分 slot 必填，见下方枚举
  "requiresMcp": ["xiaohongshu-mcp"],// 可选，依赖的宝石（MCP 服务）
  "requiresSkills": ["contact-book"], // 可选，依赖的其他 skill（装备时校验）
  "infrastructure": true,         // 可选，true = 基础层，不可装备
  "subSkills": [                  // 可选，技能子文档
    {
      "name": "子文档标题",
      "icon": "🔧",
      "file": "relative-path.md", // 相对于技能目录
      "desc": "子文档说明",
      "readBefore": "write"       // 可选，"write" 表示写作前必读
    }
  ]
}
```

---

## 2. 装备槽位枚举

### 全部槽位一览

| slot 值 | 部位 | 图标 | 槽数 | subType | 说明 |
|---------|------|------|------|---------|------|
| `helm` | 头盔 | ⛑️ | 1 | 无 | 工种：决定 bot 的角色定位 |
| `armor` | 衣服 | 👔 | 1 | 无 | 职业：主要工作能力 |
| `accessory` | 风格 | 💍 | 2 | **必填** | 内容风格 / 画图风格 |
| `utility` | 通用技能 | 🔧 | 4 | **必填** | 职能工具 |
| `research` | 研究技能 | ⚔️ | 6 | **必填** | 研究分析 / 通识参考 |
| `boots` | 靴子 | 👢 | 1 | 无 | 策略：行为策略或运营方针 |
| `scheduled` | 定时任务 | ⏰ | 6/20 | `scheduled` | 定时执行的技能，不在装备UI显示，通过⏰面板管理 |

> 特殊槽 `accessory-soul`（灵魂）自动填充 SOUL.md，不可拆卸，不需要 skill.json。
>
> `scheduled` 槽数动态：管理工种（helm=management）20个，其他工种 6 个。

### subType 枚举

| slot | subType 值 | 含义 | 图标 |
|------|-----------|------|------|
| **accessory** | `content` | 内容风格 | ✍️ |
| **accessory** | `image` | 画图风格 | 🎨 |
| **utility** | `duty` | 职能 | ⚙️ |
| **utility** | `material` | 素材 | 📦 |
| **utility** | `craft` | 手艺 | ✏️ |
| **research** | `research` | 研究分析 | 📊 |
| **research** | `general` | 通识参考 | 📚 |
| **scheduled** | `scheduled` | 定时任务 | ⏰ |

> `helm`、`armor`、`boots` 无 subType，不要填。

### 权限约束

- **research 槽位** 需要 bot 装备了 `helm-1: "frontline"` 才能解锁
- **requires 里的宝石** 必须在 gem-registry.json 中定义且已镶嵌

---

## 3. 宝石依赖（requires）可用值

| 宝石 ID | 名称 | 类型 |
|---------|------|------|
| `xiaohongshu-mcp` | 小红书 MCP | per-bot（端口 18060-18070） |
| `image-gen-mcp` | 图片生成 MCP | shared（端口 18085） |
| `compliance-mcp` | 合规审核 MCP | shared（端口 18090） |
| `research-mcp` | 研究数据网关 | per-bot（端口 18080） |

不依赖任何 MCP 的技能可以省略 `requiresMcp` 或写 `"requiresMcp": []`。

### 技能间依赖（requiresSkills）

当 skill A 需要引用 skill B 的内容时，用 `requiresSkills` 声明：

```json
"requiresSkills": ["contact-book"]
```

- 装备时校验：依赖的 skill 必须在该 bot 的 `workspace-botN/skills/` 下存在（symlink 或真实目录）
- 卸装保护：被依赖的 skill 不能在依赖方还装备时被卸下
- Tooltip 展示：依赖的 skill 以 icon + name 徽章显示

---

## 4. 各部位现有技能速查

### ⛑️ helm（工种）— 1 槽

| skill ID | name | desc |
|----------|------|------|
| `frontline` | 前台 | 面向公众的内容创作者（装备后解锁 research 槽） |
| `management` | 管理 | 全局管理者：监控、调度、审批 |
| `ops` | 内务 | 内部运维：基础设施、发布执行、研发支持 |

### 👔 armor（职业）— 1 槽

| skill ID | name | desc | requires |
|----------|------|------|----------|
| `xhs-op` | 小红书运营 | 全流程：登录、互动、选题、发布 | xiaohongshu-mcp |
| `xhs-pub` | 小红书发布中心 | 印务局：MCP 管理、发布流水线 | xiaohongshu-mcp |
| `gzh-publish` | 公众号发文 | 微信公众号发文流程 | — |
| `xhs-browser-publish` | 浏览器发布 | 浏览器发布小红书笔记 | xiaohongshu-mcp |

### 💍 accessory（风格）— 2 槽

**subType: `content`（内容风格 ✍️）**

| skill ID | name | desc |
|----------|------|------|
| `laicaimeimei-writing-style` | 来财妹妹写作风格 | 小红书投研内容写作风格标准 |
| `xuanma-style` | 宣妈内容风格 | 日常简评、月度复盘、排版、封面规范 |
| `james-style` | 老詹内容风格 | 硬卡点、写作心法、正文模板、语气措辞 |
| `dae-fly-style` | 大E飞风格 | 犀利直接、数据驱动的投研写作 |
| `qingningmeng-style` | 清柠檬风格 | 清新可爱、meme 风格 |
| `mp-content-writer` | 公众号写作 | 公众号投资文章框架 |
| `daily-market-recap` | 每日盘面复盘 | 公众号四段式推送 |
| `record-insight` | 记录灵感 | 捕捉日常观察与灵感洞察 |
| `self-review` | 自我复盘 | 内容表现回顾与改进反思 |

**subType: `image`（画图风格 🎨）**

| skill ID | name | desc | requires |
|----------|------|------|----------|
| `xuanma-cover` | 宣妈封面生成 | 角色形象、卡片/写实模板 | image-gen-mcp |
| `james-cover` | 老詹封面生成 | 角色形象、卡片模板 | image-gen-mcp |
| `laicaimeimei-cover-style` | 来财妹妹封面风格 | 品牌视觉体系 | image-gen-mcp |
| `visual-first-content` | meme绘图风格 | 贪财猫像素风 IP 画图框架 | image-gen-mcp |
| `laok-style` | 老K画图风格 | IP 形象与配图 prompt 模板 | image-gen-mcp |

### 🔧 utility（通用技能）— 4 槽

**subType: `duty`（职能 ⚙️）**

| skill ID | name | desc | requires |
|----------|------|------|----------|
| `browser-base` | 浏览器基础 | profile 管理、标签页生命周期 | — |
| `compliance-review` | 合规审核 | 独立合规审核服务 | compliance-mcp |
| `report-incident` | 异常上报 | 运行时异常记录与通知 | — |

**subType: `material`（素材 📦）**

| skill ID | name | desc |
|----------|------|------|
| `james-topic-research` | 詹姆斯话题库 | 小红书詹姆斯话题热点与蹭热度角度（bot6 专属） |

**subType: `craft`（手艺 ✏️）**

> 暂无，写稿经验、踩坑教训等技能可归入此类。

### ⚔️ research（研究技能）— 6 槽

**subType: `research`（研究分析 📊）**

| skill ID | name | desc |
|----------|------|------|
| `earnings-digest` | 财报横评 | 行业财报横向对比 |
| `flow-watch` | 资金流向 | 北向、融资融券、主力流向 |
| `research-stock` | 个股分析 | 估值、财务、市场情绪 |
| `sector-pulse` | 行业研究 | 行业竞争格局、供需 |
| `stock-watcher` | 自选股 | 自选股列表管理与行情 |
| `technical-analyst` | 技术分析 | K线形态、均线、量价 |
| `market-environment-analysis` | 宏观环境 | 全球市场、汇率、商品 |
| `energy-chem-tracker` | 能化跟踪 | 能源化工供需与价格 |
| `lithium-battery-tracker` | 锂电跟踪 | 锂电供应链产能与价格 |
| `memory-chip-tracker` | 存储芯片跟踪 | 存储芯片产业周期 |
| `space-tracker` | 航天跟踪 | 商业航天发射日历 |
| `industry-chain-breakdown` | 产业链拆解 | 产业链上下游竞争分析 |
| `tmt-landscape` | TMT全景 | 半导体、AI、消费电子、通信 |

**subType: `general`（通识参考 📚）**

| skill ID | name | desc |
|----------|------|------|
| `deepreasearch` | 深度研究 | 多轮迭代深度研究框架 |
| `news-factcheck` | 事实核查 | 新闻数据交叉验证 |
| `research-mcp` | 研究数据库 | 金融 MCP 数据接口 |
| `laicaimeimei-fupan` | 来财妹妹每日复盘 | 热点与市场深度解读 |
| `report-digest` | 研报速读 | 研报核心观点与数据提取 |
| `report-critique` | 研报批判 | 研报逻辑与数据批判性审视 |
| `report-compare` | 研报对比 | 多份研报横向对比分析 |
| `report-to-post` | 研报转帖 | 研报转化为小红书帖子 |
| `report-to-image` | 研报配图 | 研报内容生成信息图卡片 |

### 👢 boots（策略）— 1 槽

目前无现有技能。

### ⏰ scheduled（定时任务）— 6/20 槽

> 不在装备 UI 显示，通过 agent chip 上的 ⏰ 按钮管理。管理工种（management）20 槽，其他 6 槽。

| skill ID | name | desc |
|----------|------|------|
| `cron-bot-main-patrol` | 全面巡查 | 印务局登录状态、技能部汇报、编辑部研究状态 |
| `cron-daily-model-report` | 模型日报 | 每天通报各 bot 的模型序列号 |
| `cron-incidents-check` | 异常巡检(工作日) | 工作日每3小时检查 incidents.jsonl |
| `cron-incidents-check-weekend` | 异常巡检(周末) | 周末早晚各一次检查异常 |
| `cron-xhs-nurture-dispatch` | 养号调度 | 每天5轮随机挑3个bot养号 |
| `zsxq-reader` | 知识星球 | 知识星球情报采集与摘要 |

### 🏗️ infrastructure（基础层，不可装备）

| skill ID | name | desc |
|----------|------|------|
| `submit-to-publisher` | 印务局投稿 | 通过印务局发布队列提交内容（无 slot） |
| `xhs-nurture` | 养号互动 | 小红书养号（无 slot） |
| `xhs-writing` | 小红书写作规范 | 通用排版、标题、限流防范（无 slot） |

---

## 5. 新建技能步骤

### 通用技能（所有 bot 共享）

```bash
# 1. 创建目录
mkdir -p /home/rooot/.openclaw/workspace/skills/你的技能名

# 2. 写 skill.json（参考模板）
cat > /home/rooot/.openclaw/workspace/skills/你的技能名/skill.json << 'EOF'
{
  "name": "技能中文名",
  "icon": "📊",
  "slot": "research",
  "subType": "research",
  "desc": "一句话说明"
}
EOF

# 3. 写 SKILL.md（技能详细文档，bot 实际执行时会读这个）
# 4. 在 dashboard 点 🔄 SYNC，或调用 POST /api/skills/sync
```

### Bot 专属技能

```bash
# 创建在 bot 的 workspace 下
mkdir -p /home/rooot/.openclaw/workspace-bot7/skills/你的技能名
# 写 skill.json 和 SKILL.md
# 点 SYNC
```

### subSkills（子文档）

适合内容较多、需要拆分的技能。每个 subSkill 在 dashboard 里显示为可展开的子项：

```json
{
  "name": "小红书运营",
  "icon": "📕",
  "slot": "armor",
  "desc": "全流程运营",
  "requiresMcp": ["xiaohongshu-mcp"],
  "subSkills": [
    { "name": "MCP 工具", "icon": "🔧", "file": "mcp-tools.md", "desc": "工具列表" },
    { "name": "发帖前必读", "icon": "⚠️", "file": "发帖前必读.md", "desc": "红线自检", "readBefore": "write" }
  ]
}
```

---

## 6. 命名约定

| 规则 | 说明 |
|------|------|
| **skill ID** | 即目录名，用英文小写 + 连字符，如 `flow-watch`、`xuanma-cover` |
| **bot 专属前缀** | 建议加 bot 名，如 `laicaimeimei-writing-style`、`james-cover` |
| **icon** | 单个 Emoji，不要重复已有技能的图标 |
| **name** | 简短中文，4-8 字最佳 |
| **desc** | 一句话，不要超过 30 字 |

---

## 7. 验证清单

新建技能后检查：

- [ ] `skill.json` 可被 `JSON.parse()` 成功（注意逗号、引号）
- [ ] `slot` 值在 7 种枚举内（helm/armor/accessory/utility/research/boots/scheduled）
- [ ] 有 subType 的槽位（accessory/utility/research）已填 subType
- [ ] helm/armor/boots 没有填 subType
- [ ] `requiresMcp` 里的宝石 ID 在 gem-registry.json 中存在
- [ ] 目录下有 SKILL.md（bot 执行时的实际文档）
- [ ] Dashboard 点 SYNC 后能看到新技能出现在仓库中
