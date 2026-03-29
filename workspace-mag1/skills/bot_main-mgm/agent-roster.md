# Agent 职能表

> Agent ID↔名字 的映射请查 📇 **通讯小本本**（`workspace/skills/contact-book/SKILL.md`）
> 本文档聚焦职能分工和协作关系。

## 内容创作 Bot（bot1–bot18）

这些 bot 是小红书内容创作者，通过印务局投稿发布。

| Agent ID | 人设定位 |
|----------|----------|
| bot1 | 金融产品经理，可爱活泼，A 股日常 |
| bot2 | TMT 行业研究，理性犀利 |
| bot3 | 基金投资，清新可爱，meme 风格 |
| bot4 | 研报解读转化，严谨专业 |
| bot5 | 二孩妈妈，黄金/基金，温暖务实 |
| bot6 | 海归理财男，国际视野，轻松专业 |
| bot7 | 行业研究员，数据驱动，直接犀利 |
| bot8 | 金融研究（备用） |
| bot9 | 公众号运营 |
| bot10 | 多用途（测试/实验） |
| bot11 | 小奶龙 |
| bot12 | 小天爱黄金，95后职场女生，黄金投资 |
| bot13 | （待分配） |
| bot14 | （待分配） |
| bot15 | （待分配） |
| bot16 | （待分配） |
| bot17 | （待分配） |
| bot18 | （待分配） |

### 与印务局的关系

- Bot 通过 `submit-to-publisher.sh` 提交投稿 → 印务局处理
- 印务局通过 `reply_message` 回报结果 → Bot 收到结果更新日记
- **印务局不主动联系 bot 催稿**，只被动响应投稿请求

## 管理层

| Agent ID | 职能 |
|----------|------|
| mag1 | 研究部总管。基础设施运维、agent 调度、系统巡检。有权执行 `pkill`/`systemctl` 等系统命令 |
| sys1 | 发布执行中心。处理投稿队列、合规审核、MCP 健康检查、飞书告警 |
| coder | 研发支持。代码修改、工具开发、bug 修复。不参与内容创作 |
| skills | 技能管理。skill 开发、EQS维护 |

### 汇报关系

```
研究部
  ↓ 指令下达
mag1（管理员）
  ├─ sys1（印务局）— 发布执行
  ├─ coder（研发）— 技术支持
  ├─ skills（技能部）— 技能管理
  └─ bot1–bot18（内容创作）— 各自负责账号运营
```

## 职能速查

### 按职能分类

| 职能 | Agent |
|------|-------|
| 小红书内容创作 | bot1–bot18 |
| 公众号写作 | bot11 |
| 行业深度研究 | bot2, bot7, bot8 |
| 基金/理财科普 | bot3, bot5, bot6 |
| 研报解读 | bot4 |
| 发布执行 | sys1 |
| 系统运维 | mag1 |
| 技术开发 | coder |
| 技能管理 | skills |

### 印务局需要知道的关键信息

| 信息 | 用途 |
|------|------|
| account_id → 端口映射 | 发布时调用正确的 MCP 服务 |
| bot 名字 | 告警消息中展示可读名称 |
| bot 是否有独立合规要求 | 目前所有 bot 共用同一套合规规则 |
| bot10 豁免发布间隔 | bot10 不受 15 分钟发帖间隔限制 |

## MCP 端口速查

```
mag1  → 18060（管理专用）
bot1–bot18 → 单进程多租户，URL path 路由（http://localhost:18060/mcp/botN）
compliance → 18090
```

Health check: `curl -s --connect-timeout 3 http://localhost:{port}/health`
