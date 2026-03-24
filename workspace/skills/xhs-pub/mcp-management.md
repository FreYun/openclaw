# MCP 服务管理

> 印务局负责监控和维护所有 bot 的 xiaohongshu-mcp 服务。

## 端口路由表

| account_id | MCP 服务名 | 端口 | Profile 目录 |
|------------|-----------|------|-------------|
| bot1 | xhs-bot1 | 18061 | /home/rooot/.xhs-profiles/bot1/ |
| bot2 | xhs-bot2 | 18062 | /home/rooot/.xhs-profiles/bot2/ |
| bot3 | xhs-bot3 | 18063 | /home/rooot/.xhs-profiles/bot3/ |
| bot4 | xhs-bot4 | 18064 | /home/rooot/.xhs-profiles/bot4/ |
| bot5 | xhs-bot5 | 18065 | /home/rooot/.xhs-profiles/bot5/ |
| bot6 | xhs-bot6 | 18066 | /home/rooot/.xhs-profiles/bot6/ |
| bot7 | xhs-bot7 | 18067 | /home/rooot/.xhs-profiles/bot7/ |
| bot8 | xhs-bot8 | 18068 | /home/rooot/.xhs-profiles/bot8/ |
| bot9 | xhs-bot9 | 18069 | /home/rooot/.xhs-profiles/bot9/ |
| bot10 | xhs-bot10 | 18070 | /home/rooot/.xhs-profiles/bot10/ |

---

## 健康检查

```bash
# 单个端口
curl -s --connect-timeout 5 http://localhost:{port}/health

# 批量检查所有端口
for port in 18061 18062 18063 18064 18065 18066 18067 18068 18069 18070; do
  status=$(curl -s --connect-timeout 5 http://localhost:$port/health 2>/dev/null)
  if echo "$status" | grep -q '"success":true'; then
    echo "Port $port: OK"
  else
    echo "Port $port: DOWN"
  fi
done
```

返回 `{"success":true,...}` = 正常。连接失败/无响应 = 异常。

---

## 单端口重启

```bash
# 1. 精确杀掉占用该端口的进程（禁止 pkill -f 通配符！）
lsof -ti:{port} | xargs kill 2>/dev/null
sleep 2

# 2. 重新启动
XHS_PROFILES_DIR=/home/rooot/.xhs-profiles nohup /home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp \
  -headless=true -port=:{port} > /tmp/xhs-mcp-{port}.log 2>&1 &

# 3. 验证
sleep 3 && curl -s http://localhost:{port}/health
```

### 安全铁律

- **禁止 `pkill -9 -f "chrome.*xhs-profiles"`** — 通配符强杀会杀掉所有 bot 的 Chrome，导致 cookie 丢失
- **禁止 `pkill -f "xhs-mcp"`** — 会杀掉所有 MCP 实例
- 只用 `lsof -ti:{port} | xargs kill` 精确杀单个端口

---

## 登录状态检查

```bash
# 检查单个 bot 的登录状态
npx mcporter call "xhs-botN.check_login_status(account_id: 'botN')"
```

返回两个状态：
- `web_session` — 主站登录（浏览、搜索、互动）
- `galaxy_creator_session_id` — 创作者平台登录（**发布必须**）

创作者平台未登录 → 无法发布 → 通知提交者 + 报告研究部。

---

## 日志查看

```bash
# 实时日志
tail -f /tmp/xhs-mcp-{port}.log

# 最近错误
grep -i "error\|panic\|fatal" /tmp/xhs-mcp-{port}.log | tail -20
```

---

## 故障排查

| 症状 | 可能原因 | 处理 |
|------|---------|------|
| health 无响应 | 服务挂了 | 单端口重启 |
| 发布超时 | 页面加载慢 | 检查日志，可能需要重启 |
| 登录状态 expired | cookie 过期 | 通知研究部重新登录 |
| `account_id` 路由错误 | 端口与 account_id 不匹配 | 核对路由表 |
| Chrome 进程僵死 | profile 锁定 | `lsof -ti:{port} | xargs kill -9`，然后重启 |

---

## MCP 源码位置

- 源码：`/home/rooot/MCP/xiaohongshu-mcp/`
- 编译产物：`/home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp`
- Chrome profiles：`/home/rooot/.xhs-profiles/botN/`
