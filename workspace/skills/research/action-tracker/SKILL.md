---
name: action-tracker
description: >
  韭研公社异动解析数据采集与分析 — 爬取每日涨停/异动板块数据，生成板块详情，
  分析连板梯队、一字板、板块主线与资金方向。
  触发：/action-tracker、"今天有什么异动"、"涨停板块分析"、"异动解析"
---

# 异动追踪 /action-tracker

> 装备即生效。从韭研公社采集 A 股异动解析数据，生成板块详情与汇总分析报告。

**触发词**：`/action-tracker`、"今天异动"、"涨停板块"、"异动解析"、"连板梯队"

**技能目录**：`skills/action-tracker/`（脚本、数据、auth 均在此目录下）

---

## 数据路径

| 项目 | 路径（相对技能目录） |
|------|------|
| 采集脚本 | `scrape_action.js` |
| 登录脚本 | `login.js` |
| 登录凭证 | `auth.json` |
| 最新数据 | `data/action/action_latest.json` |
| 板块详情 | `data/action/details/*.md` |
| 截图 | `data/action/action_all_*.png` |

---

## 执行流程

### Step 0 — 检查登录态（每次必做）

**检查 `auth.json` 是否存在**：

```bash
ls skills/action-tracker/auth.json
```

- **存在** → 跳到 Step 1
- **不存在或过期**（脚本报 `无法获取异动数据`）→ **你无法自行登录，必须通知用户手动运行登录脚本**：

> ⚠️ 韭研公社未登录。请在终端运行以下命令完成登录：
> ```
> cd /home/rooot/.openclaw/workspace/skills/action-tracker && node login.js
> ```
> 脚本会要求输入手机号和短信验证码，登录成功后自动保存 auth.json。

**绝对不要尝试自行运行 login.js** — 该脚本需要用户交互输入验证码，bot 无法完成。

---

### Step 1 — 运行采集脚本

```bash
cd /home/rooot/.openclaw/workspace/skills/action-tracker && node scrape_action.js
```

**可选参数**：
- `2026-04-08` — 指定日期标签
- `--skip-scrape` — 跳过爬取，用已有的 `action_latest.json`
- `--data-dir /path` — 自定义数据输出目录

**脚本输出**：
- `data/action/action_latest.json` — 结构化异动数据（JSON）
- `data/action/details/*.md` — 各板块详情 Markdown
- `data/action/action_all_*.png` — 全量截图
- `data/action/action_jiantu_*.png` — 涨停简图截图（如有）

**异常处理**：
- `auth.json 不存在` → 回到 Step 0，通知用户运行 login.js
- `无法获取异动数据` → auth 可能过期，通知用户重新运行 login.js
- 网络超时 → 重试一次，仍失败则上报研究部

---

### Step 2 — 读取数据

读取 `data/action/action_latest.json`，理解数据结构：

```json
{
  "date": "2026-04-08",
  "total_stocks": 42,
  "sectors": [
    {
      "name": "板块名",
      "reason": "题材原因",
      "count": 5,
      "stocks": [
        {
          "code": "600xxx",
          "name": "股票名",
          "change_pct": 10.02,
          "num": "3板",
          "time": "09:31",
          "is_recommend": 1,
          "expound": "韭研分析文本..."
        }
      ]
    }
  ]
}
```

按需读取 `data/action/details/*.md` 获取各板块详细信息。

---

### Step 3 — 分析与报告生成

基于 Step 2 的数据，自行分析并生成报告。**以下为报告必须包含的章节**：

#### 一、板块概览

表格列出所有板块：板块名称、题材原因、个股数量、代表个股。

#### 二、连板梯队

- 按连板高度从高到低排列所有连板股
- 分析连板梯队结构（最高板、二板、首板分布）
- 判断市场情绪（赚钱效应/亏钱效应）

#### 三、一字板个股

- 列出所有一字板个股（`is_recommend = 1`）
- 分析资金抢筹方向

#### 四、板块深度分析

对每个板块逐一分析：
- **催化剂**：什么事件/消息驱动了今日异动
- **持续性判断**：该题材是短期脉冲还是有持续性
- **核心标的**：板块中最值得关注的个股及理由

#### 五、跨板块主线分析

找出今日板块之间的关联主线和资金流向逻辑，判断市场主线方向。

#### 六、明日关注

基于今日异动，给出明日需要重点关注的方向和个股。

---

### Step 4 — 输出报告

**报告格式模板**：

```markdown
# 异动解析报告

> 日期: {date} | 共 {total_stocks} 只异动股 | {sectors_count} 个板块

---

## 一、板块概览

| 板块 | 题材 | 个股数 | 代表个股 |
|------|------|--------|----------|
| ... | ... | ... | ... |

## 二、连板梯队

[最高板 → 二板 → 首板，情绪判断]

## 三、一字板个股

[一字板列表 + 资金方向分析]

## 四、板块深度分析

### 【板块名】
- 催化剂：...
- 持续性：...
- 核心标的：...

## 五、跨板块主线分析

[主线逻辑、资金流向]

## 六、明日关注

[重点方向 + 关注个股]

---
数据来源：韭研公社异动解析 | 免责：分析仅供参考，不构成投资建议
```

报告完成后：
1. 保存到 `memory/异动解析-{YYYY-MM-DD}.md`
2. 更新当日日记 `memory/{YYYY-MM-DD}.md`

---

## 配合其他技能

| 场景 | 配合技能 |
|------|----------|
| 深挖某个板块 | `/sector-pulse {板块名}` |
| 查看板块资金流向 | `/flow-watch` |
| 分析板块内个股 | `/research-stock {代码}` |
| 技术面验证龙头 | `/technical-analyst {代码}` |
| 写成小红书内容 | 走 xhs-op 发帖流程 |

---

## 首次安装

```bash
cd /home/rooot/.openclaw/workspace/skills/action-tracker
npm install
# 然后用户手动运行 node login.js 完成韭研公社登录
```

---

## 注意事项

- **数据时效**：异动数据日内有效，盘后数据更完整。建议在 **15:30 之后** 采集当日数据
- **auth 过期**：韭研公社 cookie 有效期约 7-14 天，过期后需用户重新运行 `node login.js`
- **不要频繁爬取**：每日 1-2 次即可，避免被封 IP
- **截图用途**：`action_all_*.png` 和 `action_jiantu_*.png` 可用作小红书配图素材
- **expound 字段**：韭研公社自带的个股分析文本，可作为参考但需独立判断
- **login.js 不可由 bot 运行**：需要用户交互输入短信验证码，bot 只能提示用户去终端执行
