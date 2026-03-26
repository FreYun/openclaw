# MCP 服务管理

> 印务局负责监控和维护 xiaohongshu-mcp 服务。

## 架构

xiaohongshu-mcp 是**单进程多租户**架构，监听 `:18060`，通过 URL path 区分 bot：

```
http://localhost:18060/mcp/bot7   ← bot7 的 MCP 端点
http://localhost:18060/mcp/bot1   ← bot1 的 MCP 端点
http://localhost:18060/mcp        ← fallback（兼容旧接口）
```

每个 bot 的 cookie 和 Chrome profile 仍然独立：
- Cookie 文件：`cookies-botN.json`（在 MCP 源码目录下）
- Chrome profile：`/home/rooot/.xhs-profiles/botN/`

## 路由表

| account_id | MCP 端点 | Profile 目录 |
|------------|---------|-------------|
| bot1 | http://localhost:18060/mcp/bot1 | /home/rooot/.xhs-profiles/bot1/ |
| bot2 | http://localhost:18060/mcp/bot2 | /home/rooot/.xhs-profiles/bot2/ |
| bot3 | http://localhost:18060/mcp/bot3 | /home/rooot/.xhs-profiles/bot3/ |
| bot4 | http://localhost:18060/mcp/bot4 | /home/rooot/.xhs-profiles/bot4/ |
| bot5 | http://localhost:18060/mcp/bot5 | /home/rooot/.xhs-profiles/bot5/ |
| bot6 | http://localhost:18060/mcp/bot6 | /home/rooot/.xhs-profiles/bot6/ |
| bot7 | http://localhost:18060/mcp/bot7 | /home/rooot/.xhs-profiles/bot7/ |
| bot8 | http://localhost:18060/mcp/bot8 | /home/rooot/.xhs-profiles/bot8/ |
| bot9 | http://localhost:18060/mcp/bot9 | /home/rooot/.xhs-profiles/bot9/ |
| bot10 | http://localhost:18060/mcp/bot10 | /home/rooot/.xhs-profiles/bot10/ |

---

## 健康检查

```bash
# 整个服务
curl -s --connect-timeout 5 http://localhost:18060/health
```

返回 `{"success":true,...}` = 正常。连接失败/无响应 = 异常。

---

## 服务重启

```bash
# 1. 停掉进程
lsof -ti:18060 | xargs kill 2>/dev/null
sleep 2

# 2. 重新启动（单进程，服务所有 bot）
nohup /home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp \
  --headless=true -port=:18060 -profiles-base=/home/rooot/.xhs-profiles \
  > /tmp/xhs-mcp-unified.log 2>&1 &

# 3. 验证
sleep 3 && curl -s http://localhost:18060/health
```

### 安全铁律

- **禁止 `pkill -9 -f "chrome.*xhs-profiles"`** — 通配符强杀会杀掉所有 bot 的 Chrome，导致 cookie 丢失
- 重启 MCP 服务不影响 Chrome cookie（它们在 profile 目录中持久化）

---

## 登录状态检查

```bash
# 通过 mcporter 检查（推荐）
npx mcporter call "xiaohongshu-mcp.check_login_status()"
```

返回两个状态：
- `web_session` — 主站登录（浏览、搜索、互动）
- `galaxy_creator_session_id` — 创作者平台登录（**发布必须**）

创作者平台未登录 → 无法发布 → 通知提交者 + 报告研究部。

---

## 日志查看

```bash
# 实时日志（单文件，包含所有 bot 的操作，带 [botN] 标记）
tail -f /tmp/xhs-mcp-unified.log

# 最近错误
grep -i "error\|panic\|fatal" /tmp/xhs-mcp-unified.log | tail -20

# 过滤特定 bot
grep "bot7" /tmp/xhs-mcp-unified.log | tail -20
```

---

## 故障排查

| 症状 | 可能原因 | 处理 |
|------|---------|------|
| health 无响应 | 服务挂了 | 重启服务 |
| 发布超时 | 页面加载慢 | 检查日志，可能需要重启 |
| 登录状态 expired | cookie 过期 | 通知研究部重新登录 |
| Chrome 进程僵死 | profile 锁定 | 重启服务 |

---

## MCP 源码位置

- 源码：`/home/rooot/MCP/xiaohongshu-mcp/`
- 编译产物：`/home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp`
- Chrome profiles：`/home/rooot/.xhs-profiles/botN/`
