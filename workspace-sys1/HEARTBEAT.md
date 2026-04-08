# HEARTBEAT.md — Publisher Health Check

Cron-triggered every 3h (09:00–21:00).

## Check Pending Queue

```bash
ls -1 /home/rooot/.openclaw/workspace-sys1/publish-queue/pending/ 2>/dev/null
```

- Has items → process the pending queue per AGENTS.md workflow
- Empty → reply `HEARTBEAT_OK`

## Rules

- Quiet hours: 23:00–08:00
- One report per heartbeat, no self-spawning extra crons
- **禁止 kill/restart 任何服务进程** — 遇到异常只上报 mag1
- Feishu alerts only for: publish failures. Normal results never go to Feishu group
- No issues → reply `HEARTBEAT_OK`
