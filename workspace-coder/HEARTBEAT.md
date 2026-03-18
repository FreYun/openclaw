# HEARTBEAT

## Checks (rotate, don't run all every time)

- [ ] MCP ports listening: `lsof -i:18060-18070 | grep LISTEN`
- [ ] MCP error logs in /tmp
- [ ] OpenClaw gateway alive
- [ ] Unhandled messages from other agents
- [ ] Diary cleanup needed

## Silent hours

- 23:00-08:00: no output unless service is down
- All normal + no messages → `HEARTBEAT_OK`
