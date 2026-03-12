# Heartbeat — 管理员定期巡检

每次 heartbeat 触发时执行以下巡检：

## 1. 检查 MCP 服务状态

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:18060/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse
```

## 2. 检查所有 bot 小红书登录状态

```bash
python3 /home/rooot/.openclaw/scripts/check_bots.py
```

## 3. 汇报异常

如果有异常（MCP 挂了、bot 未登录），记录到今日日记 `memory/YYYY-MM-DD.md`，并在下次与用户对话时主动汇报。

如果一切正常，简单记录"巡检正常"即可。
