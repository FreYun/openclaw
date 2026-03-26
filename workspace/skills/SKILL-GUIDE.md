# 新建技能指南

## 一、技能目录结构

```
workspace/skills/技能名/          ← 通用技能（所有 bot 可用）
workspace-botN/skills/技能名/     ← 专属技能（仅该 bot 可用）
```

每个技能目录至少包含两个文件：

| 文件 | 作用 |
|------|------|
| `skill.json` | 元数据：名称、图标、槽位、依赖（dashboard 读这个） |
| `SKILL.md` | 执行文档：bot 实际工作时读的详细指南 |

---

## 二、skill.json 字段说明

```jsonc
{
  "name": "黄金盯盘",              // 必填，中文名 4-8 字
  "icon": "🪙",                   // 必填，单个 Emoji
  "slot": "research",             // 必填，装备槽位（见下表）
  "subType": "research",          // 部分槽位必填（见下表）
  "desc": "黄金行情追踪与收盘复盘",  // 必填，一句话 ≤30 字
  "requiresMcp": ["research-mcp"],   // 可选，依赖的 MCP 宝石（见第四节）
  "requiresSkills": ["xxx"],      // 可选，依赖的其他技能
  "infrastructure": true,         // 可选，true = 基础层不可装备
  "subSkills": [                  // 可选，技能子文档
    {
      "name": "数据源说明",         // 子文档标题
      "icon": "⏱️",               // 子文档图标
      "file": "data-sources.md",  // 相对于技能目录的路径
      "desc": "各数据源时效与用途", // 子文档说明
      "readBefore": "write"       // 可选，"write" = 写作前必读
    }
  ]
}
```

---

## 三、装备槽位与 subType

| slot | 部位 | 槽数 | subType | 说明 |
|------|------|------|---------|------|
| `helm` | 工种 | 1 | — | bot 角色定位（前台/管理/内务） |
| `armor` | 职业 | 1 | — | 主要工作能力（小红书运营等） |
| `accessory` | 风格 | 2 | `content` 内容风格 / `image` 画图风格 | 必填 subType |
| `utility` | 通用技能 | 4 | `duty` 职能 / `material` 素材 / `craft` 手艺 | 必填 subType |
| `research` | 研究技能 | 6 | `research` 研究分析 / `general` 通识参考 | 必填 subType，需装备前台工种解锁 |
| `boots` | 策略 | 1 | — | 行为策略或运营方针 |
| `scheduled` | 定时任务 | 6/20 | `scheduled` | 不在装备 UI 显示，通过 ⏰ 面板管理 |

---

## 四、MCP 宝石依赖（requiresMcp）

当前可用的 MCP 宝石：

| 宝石 ID | 名称 | 说明 |
|---------|------|------|
| `xiaohongshu-mcp` | 小红书 | 登录、互动、发布 |
| `image-gen-mcp` | 图片生成 | AI 生图 |
| `compliance-mcp` | 合规审核 | 内容合规检查 |
| `research-mcp` | 研究数据 | 行情、基金、宏观、新闻 |

不依赖 MCP 的技能省略 `requiresMcp` 即可。

---

## 五、命名规范

| 项目 | 规则 | 示例 |
|------|------|------|
| 目录名（= skill ID） | 英文小写 + 连字符 | `gold-tracker`、`flow-watch` |
| bot 专属技能 | 建议加 bot 名前缀 | `james-cover`、`xuanma-style` |
| icon | 单个 Emoji，不与已有技能重复 | `🪙` |
| name | 中文 4-8 字 | `黄金盯盘`、`技术分析` |
| desc | 一句话 ≤ 30 字 | `黄金行情追踪与收盘复盘` |

---

## 六、创建步骤

### 通用技能

```bash
# 1. 创建目录
mkdir -p workspace/skills/你的技能名

# 2. 写 skill.json
# 3. 写 SKILL.md
# 4. Dashboard 点 🔄 SYNC
```

### Bot 专属技能

```bash
mkdir -p workspace-bot7/skills/你的技能名
# 写 skill.json + SKILL.md → SYNC
```

### 通用技能挂载到 bot

```bash
# 用 symlink，改源文件自动全部生效
ln -s ../../workspace/skills/技能名 workspace-botN/skills/技能名
```

---

## 七、上线前自检

- [ ] `skill.json` 是合法 JSON（注意逗号、引号）
- [ ] `slot` 值在 7 种枚举内
- [ ] 需要 subType 的槽位已填写
- [ ] `requiresMcp` 里的宝石 ID 在 gem-registry.json 中存在
- [ ] 目录下有 `SKILL.md`
- [ ] Dashboard SYNC 后能看到新技能
