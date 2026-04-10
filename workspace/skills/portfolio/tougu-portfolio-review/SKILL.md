name: tougu-portfolio-review
description: 定期复查 bot 的投顾持仓，对比最新目标组合与当前持仓（金额制），决定 KEEP/REBALANCE/SWITCH，写回 MCP 数据库 + markdown 归档
---

# 投顾组合巡检 /tougu-portfolio-review

**触发词**: `/tougu-portfolio-review`, "检查你的投顾组合要不要调", "更新你的投顾持仓", "复核你的投顾仓位"

**定位**: 面向当前 bot 自己的投顾持仓巡检 skill。模拟 bot 像真人投资者一样，先用最新产品池生成目标组合，再审视当前持仓，决定要不要动、动多少。

**核心原则**: 所有交易按实际金额结算，weight 为衍生字段。MCP 数据库是事实源，markdown 是归档层。

---

## 核心文件

### 数据库（事实源，通过 MCP 读写）

- `bot_accounts` — 账户信息（initial_capital, cash）
- `bot_holdings` — 当前持仓（amount_invested, quantity, entry_nav, market_value）
- `bot_reviews` — 巡检记录
- `bot_rebalance_actions` — 调仓动作
- `bot_daily_snapshots` / `bot_position_snapshots` — 收益快照

### Markdown（归档层）

- `memory/portfolio/当前投顾持仓.md`
- `memory/portfolio/投顾巡检记录.md`
- `memory/portfolio/投顾调仓日志.md`
- `memory/portfolio/个性化投顾产品选择.md`（目标组合，由 product-match 覆盖写入）
- `memory/portfolio/投资策略摘要.md`（投资画像）

---

## 定时主流程

定时任务触发时，严格按以下顺序执行：

```
Step 1: 获取最新产品池
    ↓
Step 2: 重新生成目标组合（覆盖写入 个性化投顾产品选择.md）
    ↓
Step 3: 读取当前持仓（从 MCP 数据库）
    ↓
Step 4: 对比目标组合 vs 当前持仓
    ↓
Step 5: 套用真实世界约束
    ↓
Step 6: 形成调仓动作（金额制，先卖后买）
    ↓
Step 7: 写回 MCP 数据库 + 同步 markdown
    ↓
Step 8: 记录收益快照
```

---

## 输入优先级

### 1. 产品池

1. **MCP 数据库**（推荐）：`tougu-portfolio-mcp.get_product_pool()`
2. 用户明确指定的产品池文件
3. 测试期 `memory/portfolio/` 下的候选池 markdown

无候选池时不进入正式 review，只记录"候选池缺失，跳过"。

### 2. 当前持仓

1. **MCP 数据库**（推荐）：`tougu-portfolio-mcp.get_bot_holdings(bot_id)`
   - 返回金额制数据：amount_invested, quantity, market_value, unrealized_pnl 等
   - 返回账户信息：initial_capital, cash, total_value, net_value
2. `memory/portfolio/当前投顾持仓.md`（备用）

无持仓时，先跑 product-match 生成目标组合，再通过 `init_bot_holdings` 初始化。初始化时 `allocations_json` 中每个产品必须携带 `thesis` 字段（从目标组合的"选择原因"提取），该理由会写入 `bot_rebalance_actions.reason`，后续可查。

### 3. 目标组合

**每次巡检都重新生成**，不复用旧的 `个性化投顾产品选择.md`：

1. 先获取最新产品池
2. 调用 `tougu-product-match` 重新选品
3. 覆盖写入 `个性化投顾产品选择.md`

### 4. 投资画像

必须先读 `memory/portfolio/投资策略摘要.md`，不足时才回看 SOUL.md / IDENTITY.md / USER.md。

---

## 真实世界约束

即使目标组合更优，也不代表当前就要切换。

| 约束 | 值 | 说明 |
|------|-----|------|
| 冷静期 | 7 天 | 距上次调仓不足 7 天，默认不做大动作。通过 `check_cooldown(bot_id)` 检查 |
| 最小变更阈值 | 5% | 单个产品权重变化 < 5% 默认忽略 |
| 最大换手 | 25% | 单次巡检最多调整总仓位的 25%（按金额计算：turnover_amount / total_value） |
| 核心仓替换 | 1 个 | 单次最多替换 1 个核心产品 |
| 调仓顺序 | 先卖后买 | 先释放现金，再执行买入 |
| 买入校验 | buy_status + min/max_deposit | 从 tougu_info 读取，暂停申购的不能买入 |
| 证据不足 | 偏向不动 | 新方案优势不明显时继续持有 |
| 风险不升档 | 无强证据不升 | 不因短期收益高而上调风险带 |
| 现金是主动仓位 | — | 保留现金是风险管理，不是没想好 |

---

## 执行流程

### Step 1: 获取最新产品池

调用 `get_product_pool()` 确认产品池可用。记录来源和更新时间。

### Step 2: 重新生成目标组合

调用 `tougu-product-match` 方法，基于最新产品池 + 投资策略摘要，生成新的目标组合。

**覆盖写入** `memory/portfolio/个性化投顾产品选择.md`。

### Step 3: 读取当前持仓

调用 `get_bot_holdings(bot_id)` 获取：

```json
{
  "initial_capital": 100000,
  "cash": 25000,
  "invested_value": 75000,
  "total_value": 100000,
  "net_value": 1.0,
  "holdings": [
    {"product_id": "AILVXKB", "product_name": "嘉实百灵全天候",
     "amount_invested": 30000, "market_value": 30000,
     "quantity": 25854, "entry_nav": 1.16, "weight": 30.0, "role": "核心底仓"}
  ]
}
```

同时调用 `check_cooldown(bot_id)` 检查冷静期。

### Step 4: 对比目标组合 vs 当前持仓

逐项比较：

- 产品是否一致
- 权重差异是否超过 5% 阈值
- 当前持仓是否偏离 bot 风险带
- 新目标是否真的显著更优

结论三选一：`KEEP` / `REBALANCE` / `SWITCH`

### Step 5: 套用决策闸门

SWITCH 条件（全部满足）：
- 新产品有明确优势
- 风险匹配不下降
- 不违反冷静期或换手上限
- 新产品在 bot 可接受能力圈
- 新产品 buy_status = 开放申购

轻微更优 → 保持不动或仅小幅再平衡。

### Step 6: 形成调仓动作（金额制，先卖后买）

**固定顺序**：先执行 SELL/DECREASE 释放现金，再执行 BUY/INCREASE 消耗现金。

每笔动作需计算：
- `amount`：交易金额
- `nav_used`：交易时净值（从 `get_bot_holdings` 返回的 latest_nav 或 `tougu_nav`）
- `quantity`：= amount / nav_used
- `cash_delta`：SELL 为正（+），BUY 为负（-）
- `before_market_value` / `after_market_value`
- `reason`：**必填**，该笔操作的具体理由（为什么买入/卖出这个产品、金额为什么是这个数）

买入前校验：
- 可用现金 ≥ 买入金额
- 买入金额 ≥ min_deposit
- buy_status ≠ 暂停申购

### Step 7: 写回数据库 + markdown（双写）

#### 7a. 写入 MCP 数据库（事实源）

1. `save_review(bot_id, decision, reason, review_md, cooldown_days, cash_before, cash_after, portfolio_value_before, portfolio_value_after, invested_value_before, invested_value_after, turnover_amount, turnover_ratio)` → 获取 review_id

2. 如有调仓：`save_rebalance_actions(bot_id, review_id, actions_json)`
   - **每笔动作必须填写 `reason` 字段**，说明该笔买入/卖出的具体理由（如"风险匹配度下降，减仓降低波动暴露"、"新增卫星仓位，补充科技赛道暴露"）
   - reason 不能为空或用通用占位符，必须针对该笔具体操作
   ```json
   [
     {"product_id":"X", "action_type":"SELL", "amount":5000, "nav_used":1.16,
      "quantity":4310, "cash_delta":5000, "before_weight":30, "after_weight":25,
      "before_market_value":30000, "after_market_value":25000,
      "reason":"近3月最大回撤扩大至15%，超出风险带上限，减仓控制波动"},
     {"product_id":"Y", "action_type":"BUY", "amount":5000, "nav_used":1.13,
      "quantity":4425, "cash_delta":-5000, "before_weight":0, "after_weight":5,
      "before_market_value":0, "after_market_value":5000,
      "reason":"新增卫星仓位，该产品夏普比率同类前20%，补充消费赛道暴露"}
   ]
   ```

3. 如持仓变化：`save_bot_holdings(bot_id, holdings_json, cash)`
   - holdings_json 格式：`[{"product_id":"X", "amount_invested":25000, "quantity":21552, "market_value":25000, "latest_nav":1.16, "weight":25, "role":"核心底仓", "thesis":"..."}]`
   - 增量更新：未变仓位保留 entry_date / entry_nav / holding_id

4. 确认 `check_cooldown(bot_id)` 冷静期已写入

#### 7b. 同步 markdown 归档

更新 `当前投顾持仓.md` + `投顾巡检记录.md`。有动作时更新 `投顾调仓日志.md`。

### Step 8: 记录收益快照

如果 `tougu_nav` 已有当日净值，调用：

```
record_daily_snapshot(bot_id, trade_date)
```

系统自主计算：从 bot_holdings 读 quantity，从 tougu_nav 读 nav，计算 market_value、total_value、net_value、daily_return、max_drawdown，写入 bot_daily_snapshots + bot_position_snapshots。

如果 tougu_nav 缺少当日净值，跳过此步骤。

---

## 输出格式

### A. 当前持仓 `memory/portfolio/当前投顾持仓.md`

```markdown
# 当前投顾持仓

**更新日期：** YYYY-MM-DD
**状态来源：** MCP 数据库
**上次巡检：** YYYY-MM-DD
**上次调仓：** YYYY-MM-DD / 暂无
**当前结论：** KEEP / REBALANCE / SWITCH

## 账户概况

| 项目 | 值 |
|------|-----|
| 初始资金 | ¥XXX |
| 当前现金 | ¥XXX |
| 持仓市值 | ¥XXX |
| 总资产 | ¥XXX |
| 账户净值 | X.XXXX |
| 累计收益 | +X.XX% |

## 当前持仓

| 产品名称 | 产品代码 | 投入金额 | 当前市值 | 权重 | 角色 | 浮盈亏 | 持有理由 |
|---------|---------|---------|---------|------|------|--------|---------|

## 现金

- **现金**：¥XXX（XX%）

## 当前约束

- **冷静期截至**：YYYY-MM-DD / 无
- **单次最大换手**：25%
- **最小权重变更阈值**：5%
```

### B. 巡检记录 `memory/portfolio/投顾巡检记录.md`

```markdown
## YYYY-MM-DD

- **巡检类型**：常规巡检 / 初始化
- **候选池来源**：MCP get_product_pool
- **结论**：KEEP / REBALANCE / SWITCH
- **本轮是否动作**：是 / 否
- **动作摘要**：
- **调仓金额**：¥XXX（换手率 X%）
- **调仓前资产**：¥XXX → 调仓后：¥XXX
- **触发原因**：
- **下次观察点**：
```

### C. 调仓日志 `memory/portfolio/投顾调仓日志.md`

```markdown
## YYYY-MM-DD

| 动作 | 产品名称 | 交易金额 | 使用净值 | 份额 | 现金变化 | 原因 |
|------|---------|---------|---------|------|---------|------|
```

---

## 硬约束

1. **流程顺序固定**：产品池 → 目标组合（重新生成）→ 当前持仓 → review → 写回
2. **金额制结算**：所有调仓按实际金额计算，份额 = amount / nav
3. **先卖后买**：SELL/DECREASE 排在 BUY/INCREASE 前面
4. **MCP 数据库优先**：事实源是数据库，markdown 是归档
5. **每次重新选品**：不复用旧的目标组合，每次巡检都覆盖写入
6. **不频繁折腾**：轻微更优不等于立刻切换
7. **风险纪律优先**：不为更高收益突破风险带
8. **证据不足时宁可不动**：偏向保守
9. **写回必须可追踪**：每次巡检留痕，动作留金额明细

_通用投顾组合巡检 skill，所有 bot 共享。修改此文件会影响全部 bot。_
