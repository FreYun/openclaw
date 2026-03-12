# TOOLS_COMMON.md - 全体 Bot 统一工具规范

> **所有 bot 的 TOOLS.md 开头必须先 `Read` 本文件，再看自己的 bot 专属配置。**

---

## 小红书操作（最重要）

**所有小红书操作必须通过 mcporter 调用 xiaohongshu-mcp 工具。**

### ⚠️ 首次使用前必读

**在执行任何小红书操作之前，必须先 `Read skills/xiaohongshu-mcp/SKILL.md`，把完整流程加载到上下文。不读 SKILL.md 就操作 = 必翻车。**

### 铁律（违反必出事）

1. **必须用 `npx mcporter call "xiaohongshu-mcp.工具名(account_id: 'botN', ...)"` 调用**
2. **每次调用必须传 `account_id`**（你的 bot 编号，见你自己的 TOOLS.md）
3. **禁止用 `curl` / HTTP 直接请求 localhost 端口**
4. **禁止使用 Docker**（`docker ps`、`docker start`、`docker run` 等一律不准）
5. **禁止修改 xiaohongshu-mcp 源码**
6. MCP 服务是直接二进制进程，不是容器

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

### MCP 服务离线时怎么办

如果 mcporter 报 `offline` 或连接失败，**先读 `skills/xiaohongshu-mcp/SKILL.md` 的 Step -1**，里面有你专属端口的启动命令。

**启动模板**（端口号见你自己的 TOOLS.md）：
```bash
XHS_BIN=/home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp
nohup $XHS_BIN -headless=true -port=:你的端口 > /tmp/xiaohongshu-mcp-botN.log 2>&1 &
sleep 2 && curl -s http://localhost:你的端口/health
```

**禁止**：
- 不要去 ls MCP 源码目录找启动方式
- 不要尝试编译或修改源码
- 不要用 Docker 启动

### 完整工具文档

使用前先读取你 workspace 下的技能文档：`skills/xiaohongshu-mcp/SKILL.md`，里面有完整的 20 个工具列表和参数说明。

---

## 联网搜索

**必须使用 MCP 提供的搜索工具，内置 `web_search` 已禁用。**

各 bot 的搜索工具可能不同（zhipu / dashscope / ddgs），以你自己的 TOOLS.md 或 mcporter.json 配置为准。

---

## 网页浏览

**必须使用 OpenClaw 自带 browser 工具。**

- 严禁使用 Chrome 插件或任何浏览器扩展
- 需要登录或 JS 渲染的页面用 browser 工具处理
- 浏览器用完了必须关 tab（`browser close`）
- ref 只在当前 snapshot 有效，页面变化后必须重新 snapshot

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

## 工具优先级

1. **memory** → 先检索历史研究，有则增量更新
2. **Tushare 工具** → A 股行情、财务、北向资金（结构化数据）
3. **browser 工具** → 雪球、东方财富研报（定性分析）
4. **MCP 搜索** → 补充搜索、验证、海外数据
5. **xiaohongshu-mcp** → 发帖、管理笔记、互动（通过 mcporter 调用）
