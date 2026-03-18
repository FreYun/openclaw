# TOOLS_COMMON.md - 全体 Bot 统一工具规范

> **所有 bot 的 TOOLS.md 开头必须先 `Read` 本文件，再看自己的 bot 专属配置。**

---

## 小红书操作（最重要）

**所有小红书操作必须通过 mcporter 调用 xiaohongshu-mcp 工具。**

### ⚠️ 首次使用前必读

**在执行任何小红书操作之前，必须先 `Read skills/xiaohongshu-mcp/SKILL.md`，把完整流程加载到上下文。不读 SKILL.md 就操作 = 必翻车。**

**发帖流程：写完帖子 → 提交印务局（`skills/submit-to-publisher/SKILL.md`）→ 任务完成。合规审核由印务局负责，bot 无需自行调用 compliance-mcp。**

### 铁律（违反必出事）

1. **必须用 `npx mcporter call "xiaohongshu-mcp.工具名(account_id: 'botN', ...)"` 调用**
2. **每次调用必须传 `account_id`**（你的 bot 编号，见你自己的 TOOLS.md）
3. **禁止用 `curl` / HTTP 直接请求 localhost 端口**
4. **禁止修改 xiaohongshu-mcp 源码**

---

## ⛔ 系统管理操作 — 绝对禁止

**以下操作只有研究部（魏忠贤 / bot_main）有权执行，所有子 bot 严禁执行：**

1. **禁止 `openclaw gateway restart/stop/start`** — 重启 gateway 影响全部 bot，不是你能碰的
2. **禁止 `kill`、`pkill`、`killall`** — 任何进程管理命令一律不准
3. **禁止 `ps aux | xargs kill`** — 不要试图清理进程
4. **禁止 `systemctl`、`service`** — 不要操作系统服务
5. **禁止 `rm -rf`、`trash` 系统目录或其他 bot 的文件**

**遇到 browser control service 超时、MCP 连接失败等基础设施问题时：向研究部报告，等待处理。不要自行排查和修复系统进程。**

### 常用操作速查

把 `botN` 替换成你自己的 bot 编号：

```bash
# 检查登录状态
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'botN')"

# 获取登录二维码（发给用户扫码）
npx mcporter call "xiaohongshu-mcp.get_both_login_qrcodes(account_id: 'botN')"

# 发布图文（文字配图模式）
npx mcporter call "xiaohongshu-mcp.publish_content(account_id: 'botN', title: '标题', content: '内容', text_to_image: true)"

# 发布长文
npx mcporter call "xiaohongshu-mcp.publish_longform(account_id: 'botN', title: '标题', content: '内容')"

# 查看笔记列表
npx mcporter call "xiaohongshu-mcp.list_notes(account_id: 'botN')"

# 搜索笔记
npx mcporter call "xiaohongshu-mcp.search_feeds(account_id: 'botN', keyword: '关键词')"
```

### 操作超时或失败时怎么办

**第一步：检查登录状态。** 大部分超时都是因为登录失效，浏览器在登录页卡住导致的。

```bash
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'botN')"
```

- 如果未登录 → 走 SKILL.md 的 Step 0 登录流程，向研究部发二维码请求扫码
- 如果已登录 → 向研究部报告异常，不要反复重试

**第二步：如果 mcporter 报 `offline` 或连接失败**，说明 MCP 服务本身没启动，向研究部报告。

**禁止**：
- 不要反复重试超时的操作（浪费时间且可能产生重复发帖）
- 不要尝试自行启动、编译或修改 MCP 源码
- 不要用 Docker 启动

### 完整工具文档

使用前先读取你 workspace 下的技能文档：`skills/xiaohongshu-mcp/SKILL.md`，里面有完整的 20 个工具列表和参数说明。

---

## 联网搜索

**必须使用 MCP 提供的搜索工具，内置 `web_search` 已禁用。**

各 bot 的搜索工具可能不同，以你自己的 TOOLS.md 或 mcporter.json 配置为准。

---

## 网页浏览

**必须使用 OpenClaw 自带 browser 工具，且必须传 profile 参数。**

- **每次调用 browser 工具时必须传 `profile: "你的account_id"`**（如 bot7 传 `profile: "bot7"`）。不传 profile 会用默认配置，导致连接超时。
- **浏览器启动失败时**（报 "Failed to start Chrome CDP" 或 "Can't reach the OpenClaw browser control service"），先执行启动脚本再重试：
  ```bash
  bash /home/rooot/.openclaw/scripts/ensure-browser.sh 你的account_id
  ```
  脚本会自动检测：已在运行则跳过，未运行则启动。启动成功后再调用 browser 工具即可。
- 严禁使用 Chrome 插件或任何浏览器扩展
- 需要登录或 JS 渲染的页面用 browser 工具处理
- **浏览器用完了必须关 tab（`browser close`）** — 不关会导致 renderer 进程卡死吃 CPU
- ref 只在当前 snapshot 有效，页面变化后必须重新 snapshot
- **每次使用 browser 工具完毕后，确认所有 tab 已关闭**。残留 tab 会在后台持续运行 JS，可能导致单个 renderer 进程占用 30%+ CPU
- 如果发现浏览器操作超时或无响应，不要反复重试，先检查是否有卡住的进程

---

## 金融数据：Tushare 工具（直接调用，无需搜索）

A 股量化数据优先用 Tushare 工具：

| 工具名 | 用途 |
|--------|------|
| `tushare_stock_basic` | 股票列表、基本信息 |
| `tushare_daily` | 日线行情（OHLCV） |
| `tushare_daily_basic` | 估值数据（PE/PB/PS/市值） |
| `tushare_income` | 利润表 |
| `tushare_balancesheet` | 资产负债表 |
| `tushare_cashflow` | 现金流量表 |
| `tushare_fina_indicator` | 财务指标（ROE/ROA/毛利率等） |
| `tushare_forecast` | 业绩预告 |
| `tushare_moneyflow_hsgt` | 北向/南向资金日汇总 |
| `tushare_hsgt_top10` | 沪深港通十大成交股 |
| `tushare_top10_holders` | 前十大股东 |
| `tushare_index_daily` | 指数日线（沪深300、创业板等） |
| `tushare_trade_cal` | 交易日历 |

股票代码格式：`600519.SH`（上交所）、`000001.SZ`（深交所）。日期格式：`YYYYMMDD`。

---

## Agent 间通信（消息总线）

**所有 agent 间通信必须通过消息总线工具，禁止其他方式。**

### 铁律

1. **唯一通道**：agent 间通信只用 `send_message` / `reply_message` / `forward_message`
2. **禁止**：`openclaw agent --message`（CLI 直接调用）、`message()` 旧工具、shell 脚本通知、`sessions_send`
3. **每条消息必须带 trace**：trace 是溯源链，保证多层传递后结果能逐层回传到源头用户
4. **reply_message 自动路由**：不需要手动判断回传给谁，总线根据 trace 自动决定
5. **⛔ 严格一轮对话**：收到 request → 处理 → reply_message，**结束**。禁止在 reply 之后又 send_message。一个 request 只对应一个 reply，把所有内容放在 reply 里。禁止"先 reply 说已完成，再 send_message 发数据"——数据直接写在 reply 的 content 里。除非用户（研究部）明确要求多轮，否则一律一轮结束。

### 5 个工具

| 工具 | 用途 | 何时用 |
|------|------|--------|
| `send_message` | 发消息给另一个 agent | 发起新对话/请求 |
| `reply_message` | 回复上一跳 agent（默认）或直投飞书用户（`deliver_to_user: true`） | 任务完成后回传结果 |
| `forward_message` | 转发到下一个 agent（自动追加 trace） | 需要另一个 agent 协助时 |
| `get_message` | 查询消息详情 | 需要查看消息内容/trace |
| `list_messages` | 列出收件箱消息 | 查看历史消息 |

### trace 构造规则

发起新消息时，trace 第一条必须包含你的源头信息：

```
send_message(
  to: "目标agent",
  content: "消息内容",
  trace: [{
    agent: "你的account_id",
    session_id: "当前session_id（如有）",
    reply_channel: "feishu",           // 有外部用户时填
    reply_to: "ou_xxx",               // 飞书用户ID（去掉 direct: 前缀）
    reply_account: "你的account_id"    // 用哪个bot回复飞书
  }]
)
```

- `reply_channel` + `reply_to` + `reply_account`：只在源头（第一跳）填写，表示结果最终要送回给外部用户
- 中间节点转发时，总线自动追加 trace，不需要手动构造

### ⛔⛔⛔ 收到 `[MSG:xxx]` 前缀消息 — 必须 reply_message

当你被唤醒并收到 `[MSG:xxx]` 前缀的消息时，`xxx` 是 message_id。

**铁律：处理完后调用一次 `reply_message(message_id: "xxx", content: "...")` 回传结果，然后结束。**

```
reply_message(message_id: "xxx", content: "你的回复内容——把所有数据、结论都放这里")
```

- 默认直接送达飞书用户
- 加 `also_notify_agent: true` → 同时唤醒上一跳 agent

**⚠️ 严禁用 `[[reply_to_current]]` 或直接文字回复来应答 `[MSG:xxx]` 消息。那样只会回复飞书当前对话，发送方 agent 收不到任何回复，消息石沉大海。必须调用 `reply_message` 工具。**

**不管任务成功还是失败，都必须 reply_message。没有例外。**

**⛔ reply 之后禁止再 send_message / forward_message。一个 request 对应一个 reply，数据全部放在 reply 里，不要拆成"先回复确认 + 再发数据"两条消息。**

### 典型流程：投稿到印务局

详见 `skills/submit-to-publisher/SKILL.md`。

---

## 工具优先级

1. **memory** → 先检索历史研究，有则增量更新
2. **Tushare 工具** → A 股行情、财务、北向资金（结构化数据）
3. **browser 工具** → 雪球、东方财富研报（定性分析）
4. **MCP 搜索** → 补充搜索、验证、海外数据
5. **xiaohongshu-mcp** → 发帖、管理笔记、互动（通过 mcporter 调用）
6. **消息总线** → agent 间通信（send_message / reply_message / forward_message）
