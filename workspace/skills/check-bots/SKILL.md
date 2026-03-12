---
name: check-bots
description: 管理员巡检技能 — 检查所有 bot 的小红书登录状态和 MCP 服务状态。用于日常巡检、故障排查。当用户说"检查bot状态"、"巡检"、"看看谁掉线了"时触发。
---

# Bot 巡检技能

你是管理员（main），负责监控所有 bot 的运行状态。

## Bot 列表

| Bot ID | 名称 | 小红书账号 |
|--------|------|-----------|
| bot1 | 来财妹妹 | bot1 |
| bot2 | 狗哥说财 | bot2 |
| bot3 | meme爱基金 | bot3 |
| bot4 | 研报搬运工阿泽 | bot4 |
| bot5 | 宣妈慢慢变富 | bot5 |
| bot6 | 爱理财的James | bot6 |
| bot7 | 老K投资笔记 | bot7 |

bot8-10 暂未启用，不用检查。

---

## 任务一：检查小红书登录状态

直接运行现有脚本：

```bash
python3 /home/rooot/.openclaw/scripts/check_xhs_login.py --url http://localhost:18060
```

或者只检查指定 bot：

```bash
python3 /home/rooot/.openclaw/scripts/check_xhs_login.py --url http://localhost:18060 --bots bot1 bot2 bot5 bot7
```

### 结果解读

- **已登录** → 正常，不用管
- **未登录** → 需要扫码，汇报给用户，列出哪些 bot 需要重新扫码
- **服务不可用** → MCP 服务挂了，先处理任务二

### 如果有 bot 未登录

汇报格式：
```
小红书登录巡检结果：
✅ 已登录：bot1(来财妹妹), bot5(宣妈慢慢变富), bot7(老K投资笔记)
❌ 未登录：bot2(狗哥说财), bot3(meme爱基金)

需要扫码的 bot：bot2, bot3
```

---

## 任务二：检查 MCP 服务状态

### 2.1 检查 xiaohongshu-mcp 服务

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:18060/health
```

- 返回 `200` → 正常
- 其他或连接失败 → 服务挂了

如果挂了，检查进程：

```bash
ps aux | grep xhs-mcp | grep -v grep
```

### 2.2 检查 finance-data MCP 服务

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse
```

### 2.3 检查 mcporter 连接（每个 bot 的 MCP 配置）

检查每个 bot workspace 的 mcporter.json 是否配置了 xiaohongshu-mcp：

```bash
for i in 1 2 3 4 5 6 7; do
  echo -n "bot$i: "
  if grep -q "xiaohongshu-mcp" /home/rooot/.openclaw/workspace-bot$i/config/mcporter.json 2>/dev/null; then
    echo "✅ 已配置"
  else
    echo "❌ 未配置"
  fi
done
```

### 汇报格式

```
MCP 服务状态巡检：
🔌 xiaohongshu-mcp (localhost:18060): ✅ 运行中 / ❌ 已停止
🔌 finance-data (localhost:8000): ✅ 运行中 / ❌ 已停止

Bot MCP 配置：
bot1-bot7: 全部已配置 / botX 未配置 xiaohongshu-mcp
```

---

## 完整巡检流程

当用户说"巡检"或"检查所有bot状态"时，按以下顺序执行：

1. **先检查 MCP 服务** — 如果服务都没跑，login check 也没意义
2. **再检查小红书登录** — 逐个 bot 检查
3. **输出汇总报告**

汇总报告格式：

```
========== Bot 巡检报告 ==========
时间：YYYY-MM-DD HH:MM

【MCP 服务】
  xiaohongshu-mcp: ✅ / ❌
  finance-data: ✅ / ❌

【小红书登录】
  ✅ 已登录 (N个): bot1, bot5, bot7
  ❌ 未登录 (N个): bot2, bot3

【需要处理】
  - bot2, bot3 需要重新扫码登录小红书
================================
```

---

## 故障处理建议

### MCP 服务挂了

提示用户重启：
```bash
nohup /tmp/xhs-mcp -headless=true -port=:18060 > /tmp/xiaohongshu-mcp.log 2>&1 &
```

### Bot 未登录

告知用户哪些 bot 需要扫码，不要自己尝试登录流程。
