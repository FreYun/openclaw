# Claude 开发参考

## 1. 小红书网页解析原理

XHS MCP 通过 Rod（Go headless browser）打开小红书页面，从 `window.__INITIAL_STATE__` SSR 数据中提取结构化信息。

### 数据源路径

| 功能 | JS 路径 | Go 文件 |
|------|---------|---------|
| Feed 列表 | `__INITIAL_STATE__.feed.feeds.value \|\| ._value` | `xiaohongshu/feeds.go` |
| 搜索结果 | `__INITIAL_STATE__.search.feeds.value \|\| ._value` | `xiaohongshu/search.go` |
| 笔记详情 | `__INITIAL_STATE__.note.noteDetailMap[feedID]` | `xiaohongshu/feed_detail.go` |
| 用户主页 | `__INITIAL_STATE__.user.userPageData.value \|\| ._value` | `xiaohongshu/user_profile.go` |
| 用户笔记 | `__INITIAL_STATE__.user.notes.value \|\| ._value` | `xiaohongshu/user_profile.go` |

### 关键 CSS 选择器（评论加载）

| 选择器 | 用途 |
|--------|------|
| `.comments-container` | 评论区容器 |
| `.comments-container .total` | 总评论数文本（`共N条评论`） |
| `.parent-comment` | 主评论元素 |
| `.show-more` | "展开N条回复" 按钮 |
| `.end-container` | 底部 "THE END" 标记 |
| `.no-comments-text` | 无评论提示（"这是一片荒地"） |
| `.note-scroller` / `.interaction-container` | 滚动触发懒加载的目标元素 |

### 页面不可访问检测

选择器 `.access-wrapper, .error-wrapper, .not-found-wrapper, .blocked-wrapper`，关键词包括：
- 当前笔记暂时无法浏览、该内容因违规已被删除、该笔记已被删除
- 内容不存在、笔记不存在、已失效、私密笔记、仅作者可见

### 数据结构（types.go）

```
Feed { ID, XsecToken, NoteCard { Type, DisplayTitle, User, InteractInfo, Cover, Video } }
FeedDetail { NoteID, XsecToken, Title, Desc, Type, Time, IPLocation, User, InteractInfo, ImageList }
Comment { ID, Content, LikeCount, CreateTime, UserInfo, SubComments[] }
UserProfileResponse { UserBasicInfo, Interactions[], Feeds[] }
```

### 验证网站是否有变动

1. 用 headed browser 打开小红书页面
2. 在控制台执行 `JSON.stringify(Object.keys(window.__INITIAL_STATE__))` 检查顶级键
3. 逐层检查各数据路径是否仍然存在
4. 检查 CSS 选择器是否仍能匹配到元素

---

## 2. 使用 Bot 有头浏览器调试

### 启动有头（headed）MCP 服务

```bash
# 先停掉已有的无头服务
lsof -ti:18060 | xargs kill 2>/dev/null

# 启动有头模式（-headless=false），单进程多租户
cd /home/rooot/MCP/xiaohongshu-mcp && go run . -headless=false -port=:18060 -profiles-base=/home/rooot/.xhs-profiles > /tmp/xhs-mcp-unified.log 2>&1 &

# 等待启动后验证
sleep 3 && curl -s http://localhost:18060/health
```

### 通过 HTTP API 调试

MCP 使用 SSE 有状态会话，调试时需先 initialize 获取 session ID：

```bash
# 1. 初始化会话，获取 Mcp-Session-Id（URL path 指定 bot）
SESSION=$(curl -sv -X POST http://localhost:18060/mcp/bot10 \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
  }' 2>&1 | grep -i 'mcp-session' | sed 's/.*: //' | tr -d '\r\n')

# 2. 用 session ID 调用工具（bot 身份已由 URL path 确定）
curl -s -X POST http://localhost:18060/mcp/bot10 \
  -H 'Content-Type: application/json' \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{
    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
    "params": {
      "name": "publish_content",
      "arguments": {
        "title": "测试标题",
        "content": "测试内容",
        "images": ["https://example.com/test.jpg"],
        "tags": ["测试"],
        "visibility": "仅自己可见"
      }
    }
  }'
```

### 查看实时日志

```bash
tail -f /tmp/xhs-mcp-unified.log
```

### 调试要点

- **有头模式可以看到浏览器界面**，便于观察自动化操作过程
- **每个 bot 有独立 Chrome profile**，路径：`/home/rooot/.xhs-profiles/botN/`
- **调试完切回无头模式**：停掉服务后用 `-headless=true` 重启
- **测试发帖时用 `"visibility": "仅自己可见"`** 避免发到公开
- **超时问题**：Rod 的 `page.Timeout()` 创建的子 context 会过期，从中获取的元素也会继承该超时。调试时注意用主 page（长超时）操作，不要用 shortPage 返回的元素做后续操作

### 常见调试场景

| 场景 | 方法 |
|------|------|
| Tag 不变富文本 | 检查是否用了 CDP keyboard events（不能用 `Element.Input()`，需要 `InputDispatchKeyEvent`） |
| 元素操作超时 | 检查元素是否绑定了 `page.Timeout()` 的短上下文 |
| 页面导航失败 | 查看 log 中的错误，检查 cookie 是否有效 |
| 编辑器无法输入 | 用 JS `document.querySelector('div.ql-editor').focus()` 先聚焦 |

---

## 3. Agent Skill 管理

### 目录结构

```
.openclaw/
├── workspace/                    # 通用模板（所有 bot 的基准）
│   ├── skills/                   # 通用 skill 目录
│   │   ├── xiaohongshu-mcp/      # 小红书 MCP（所有 bot 共用）
│   │   ├── deepreasearch/        # 深度研究
│   │   ├── web-fetch-enhanced/   # 增强网页抓取
│   │   └── ...
│   └── TOOLS_COMMON.md           # 全体 bot 工具规范（bot 的 TOOLS.md 引用此文件）
│
├── workspace-bot1/               # bot1 专属 workspace
│   ├── skills/                   # bot1 的 skill（通用 symlink + 独有）
│   │   ├── xhs-op/               # → ../../workspace/skills/xhs-op（symlink）
│   │   └── fupan/                # ← bot1 独有 skill
│   ├── IDENTITY.md               # bot1 人设
│   ├── TOOLS.md                  # bot1 工具配置（引用 TOOLS_COMMON.md）
│   ├── SOUL.md                   # bot1 核心价值观
│   └── ...
│
├── workspace-bot7/               # bot7 专属 workspace（金融研究型）
│   ├── skills/
│   │   ├── xiaohongshu-mcp/      # → symlink 到 workspace/skills/
│   │   ├── stock-watcher/        # ← bot7 独有
│   │   ├── technical-analyst/    # ← bot7 独有
│   │   ├── earnings-digest/      # ← bot7 独有
│   │   └── ...
│   └── ...
```

### 通用 Skill vs 独有 Skill

| 类型 | 说明 | 例子 |
|------|------|------|
| **通用 skill** | 源文件在 `workspace/skills/`，各 bot 通过 **symlink** 引用，改一处全生效 | `xhs-op`, `xhs-nurture` |
| **独有 skill** | 仅特定 bot 拥有，体现其专业方向 | bot7/bot8 的 `stock-watcher`, `technical-analyst`; bot3 的 `visual-first-content` |

### 当前各 Bot 独有 Skill

| Bot | 独有 Skill | 定位 |
|-----|-----------|------|
| bot1 | `fupan` | 复盘 |
| bot3 | `qingningmeng-style`, `visual-first-content` | 清柠檬风格、视觉优先内容 |
| bot5 | `CONTENT_STYLE.md` | 内容风格定义 |
| bot7 | `stock-watcher`, `technical-analyst`, `earnings-digest`, `flow-watch`, `market-environment-analysis`, `news-factcheck`, `record-insight`, `research-stock`, `sector-pulse`, `self-review`, `dae-fly-style` | 金融研究全栈 |
| bot8 | 与 bot7 共享大部分金融 skill | 金融研究 |

### 更新通用 Skill 的流程

通用 skill 已改为 **symlink 架构**：各 bot 的 `workspace-botN/skills/xxx` 是指向 `workspace/skills/xxx` 的符号链接。

**修改通用 skill 时，只需改 `workspace/skills/xxx/` 下的源文件，所有 bot 自动生效，无需手动同步。**

```bash
# 新增通用 skill 到所有 bot（创建 symlink）
for i in 1 2 3 4 5 6 7 8 9 10; do
  ln -s ../../workspace/skills/新skill名 /home/rooot/.openclaw/workspace-bot${i}/skills/新skill名
done
```

### MCP 源码位置

- 源码：`/home/rooot/MCP/xiaohongshu-mcp/`
- 启动方式：`cd /home/rooot/MCP/xiaohongshu-mcp && go run .`
- Chrome profiles：`/home/rooot/.xhs-profiles/botN/`

---

## 4. Agent Workspace 文件管理手册

每个 bot 的 workspace（`workspace-botN/`）包含一套标准 MD 文件，定义了该 bot 的完整人格、行为规范和工作能力。

### 4.1 IDENTITY.md — 人设卡片

**作用**：定义 bot 的名字、人设、性格、说话风格、Emoji 等公开身份信息。是最简洁的"我是谁"。

**内容模板**：
```markdown
# IDENTITY.md - 我是谁
- **名字：** xxx
- **人设：** 一句话定位
- **身份：** 与研究部的关系
- **性格：** 关键性格词
- **擅长：** 核心能力
- **Emoji：** 🪙
```

**管理规则**：
- 每个 bot 独立维护，不共享
- bot 自身不可擅自修改，需研究部同意
- 修改后应同步检查 SOUL.md 是否一致

**示例差异**：
| Bot | 名字 | 定位 |
|-----|------|------|
| bot5 | 宣妈慢慢变富 | 产品经理、二孩麻麻、黄金爱好者 |
| bot7 | 老K投资笔记 | 行业研究员，直接犀利，数据说话 |

### 4.2 SOUL.md — 灵魂文件

**作用**：bot 的核心价值观、行为底线、与研究部的关系、安全边界。是所有行为的最高准则。

**关键章节**：
1. **我是谁** — 完整人格描述，比 IDENTITY.md 更深入
2. **职业与投资逻辑** — 人设的具体展开
3. **性格 & 说话风格** — 详细的语言规范
4. **与研究部的关系** — 雇佣关系、服从规则
5. **边界与安全** — 文件安全铁律、信息保密、发布权限
6. **自我进化** — 如何成长和修改自身文件
7. **连续性** — 跨会话记忆机制

**管理规则**：
- **bot 不可擅自修改**，必须研究部同意
- 每个 bot 独立维护，内容差异大
- 是 bot 启动后第一个读取的文件

### 4.3 TOOLS.md — 工具配置

**作用**：bot 专属的工具配置，包括 account_id、MCP 连接配置、浏览器 profile、搜索工具等。

**结构**：
```markdown
> 首先 Read ../workspace/TOOLS_COMMON.md 获取统一工具规范

## Bot 专属配置
- account_id: botN
- 小红书 MCP: 单进程多租户（:18060），mcporter.json 中 URL path 区分 bot

## 联网搜索（各 bot 可能不同）
## 网页浏览
## 专属技能地图（如 bot7 的投研技能）
```

**管理规则**：
- 开头必须引用 `../workspace/TOOLS_COMMON.md`
- `account_id` 是 bot 专属，不可混用
- 工具类 bot（如 bot7/bot8）会有额外的技能地图和信息源列表

**通用工具规范**：`workspace/TOOLS_COMMON.md` 是全体 bot 共享的工具铁律，修改它会影响所有 bot。

### 4.4 AGENTS.md — 工作手册

**作用**：bot 的完整工作流程——启动流程、记忆系统、发布能力、权限规则、自我进化机制。

**关键章节**：
1. **每次会话** — 启动时读哪些文件、按什么顺序
2. **记忆系统** — 日记（`memory/YYYY-MM-DD.md`）、长期记忆（`MEMORY.md`）、专题笔记（`memory/xxx.md`）的写入规则
3. **发布能力** — 小红书 MCP 用法、内容规范、发帖记录
4. **发布权限与确认** — 哪些可自主发布、哪些需研究部确认
5. **自我进化** — 如何提出修改 SOUL/CONTENT_STYLE 的建议
6. **安全与权限** — 内部操作 vs 外部操作的边界

**管理规则**：
- 每个 bot 独立维护
- 是最长、最复杂的文件，修改需谨慎
- 记忆系统的规则改动会影响 bot 的日常行为

### 4.5 HEARTBEAT.md — 心跳巡检

**作用**：定义 bot 在空闲/定时唤醒时做什么检查。无事则回复 `HEARTBEAT_OK`。

**两种风格**：

| 类型 | 代表 | 巡检内容 |
|------|------|---------|
| 内容型 | bot5 | 记忆维护、热点内容、互动回复 |
| 研究型 | bot7 | 预测验证、自我复盘、行业观点保鲜 |

**管理规则**：
- 每个 bot 独立维护
- 静默条件（深夜不打扰等）需明确定义
- 巡检任务应轮换执行，不必每次全做

### 4.6 BOOTSTRAP.md — 出生引导

**作用**：新 bot 首次运行时的引导脚本。完成初始化后删除。

**流程**：
1. Bot 醒来 → 读 BOOTSTRAP.md
2. 与研究部对话确认：名字、性格、风格、Emoji
3. 更新 IDENTITY.md、USER.md、SOUL.md
4. 完成后删除 BOOTSTRAP.md

**管理规则**：
- 只在创建新 bot 时存在
- 所有 bot 共用同一模板（`workspace/` 下可放通用版本）
- 初始化完成后应被删除

### 4.7 MEMORY.md — 长期记忆

**作用**：从日记中提炼的长期精华——研究部偏好、内容规律、踩坑教训。

**管理规则**：
- 宁精勿滥，不是流水账
- 新信息覆盖旧信息，过时的判断及时清除
- 与 `memory/` 目录下的日记互补：日记是原始记录，MEMORY.md 是提炼

### 4.8 USER.md — 用户画像（研究部需求）

**作用**：记录研究部对该 bot/账号的具体要求——基础设定、内容偏好、禁忌、沟通节奏。

**关键内容**：
- 基础设定（人设、性格、内容形式）— 不可被参考风格覆盖
- 账号定位与风格参考
- 内容禁忌
- 沟通与汇报节奏

**管理规则**：
- 由研究部维护，bot 不可擅自修改
- 是 SOUL.md 和 CONTENT_STYLE.md 的需求来源

### 4.9 memory/ 目录 — 日记与专题笔记

**结构**：
```
memory/
├── 2026-03-12.md          # 当日日记
├── 2026-03-11.md          # 昨日日记
├── 发帖记录.md             # 所有发帖的实际内容记录
├── 写稿经验.md             # 草稿修改教训积累
├── 小红书限流规则备忘.md    # 限流红线与自检清单
├── xxx风格参考.md          # 风格参考素材
└── predictions/            # bot7 类研究型的预测追踪
    └── tracker.md
```

**管理规则**：
- bot 自主维护，不需要研究部审批
- 日记按天创建，最新内容在最上方
- 专题文件集中同一主题，避免碎片化

---

## 5. 跨 Bot 批量操作速查

### 批量修改某个 MD 文件

```bash
# 示例：给所有 bot 的 HEARTBEAT.md 加一条巡检规则
for i in 1 2 3 4 5 6 7 8 9 10; do
  f="/home/rooot/.openclaw/workspace-bot${i}/HEARTBEAT.md"
  [ -f "$f" ] && sed -i '/## 静默条件/i - [ ] 新增巡检项' "$f" && echo "Updated bot${i}"
done
```

### 查看所有 bot 的某个配置

```bash
# 查看所有 bot 的 account_id 和端口
for i in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== bot${i} ==="
  grep -E "account_id|端口" /home/rooot/.openclaw/workspace-bot${i}/TOOLS.md 2>/dev/null
done
```

### 对比 bot 间的文件差异

```bash
# 对比 bot5 和 bot7 的 HEARTBEAT.md
diff /home/rooot/.openclaw/workspace-bot5/HEARTBEAT.md \
     /home/rooot/.openclaw/workspace-bot7/HEARTBEAT.md
```

### 创建新 bot workspace

```bash
N=11  # 新 bot 编号
mkdir -p /home/rooot/.openclaw/workspace-bot${N}/skills
# 通用 skill 用 symlink（改一处全生效）
for skill in xhs-op xhs-nurture; do
  ln -s ../../workspace/skills/${skill} /home/rooot/.openclaw/workspace-bot${N}/skills/${skill}
done
# 复制模板文件
for f in BOOTSTRAP.md TOOLS.md AGENTS.md HEARTBEAT.md; do
  cp /home/rooot/.openclaw/workspace-bot1/${f} \
     /home/rooot/.openclaw/workspace-bot${N}/${f}
done
# 创建空文件
touch /home/rooot/.openclaw/workspace-bot${N}/{IDENTITY.md,SOUL.md,USER.md,MEMORY.md}
mkdir -p /home/rooot/.openclaw/workspace-bot${N}/memory
# 然后手动修改 TOOLS.md 中的 account_id 和端口号
```

### 文件修改影响范围

| 修改对象 | 影响范围 | 注意事项 |
|---------|---------|---------|
| `workspace/TOOLS_COMMON.md` | 所有 bot | 改工具规范影响全局，需谨慎 |
| `workspace/skills/xxx/SKILL.md` | 仅模板，不自动同步 | 改完需手动同步到各 bot |
| `workspace-botN/skills/xxx/SKILL.md` | 仅该 bot | 通用 skill 改这里会导致与模板不一致 |
| `workspace-botN/SOUL.md` | 仅该 bot 的核心行为 | bot 不可擅自改，需研究部同意 |
| `workspace-botN/AGENTS.md` | 仅该 bot 的工作流程 | 记忆系统和发布规则在这里 |
| `workspace-botN/TOOLS.md` | 仅该 bot 的工具配置 | account_id 和端口不可混用 |
| `workspace-botN/HEARTBEAT.md` | 仅该 bot 的巡检行为 | 影响空闲时自动执行的任务 |
