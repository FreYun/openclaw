# MEMORY.md - Wei Zhongxian Long-Term Memory

## Inspection Mechanism

- **Login inspection frequency controlled by cron, heartbeat does not track frequency**
- Do not write/read `memory/last-heartbeat.txt`, do not depend on it
- HEARTBEAT.md only checks "is this a heartbeat trigger" and "time window" — cron handles scheduling
- This is an explicit imperial decree; all future sessions must comply

## Incident Log Handling

- **Never manually clear incidents.jsonl**
- Correct process: run `python3 ~/.openclaw/workspace-mag1/scripts/check-incidents.py` — script auto-reads, outputs alerts, and archives
- Has output → forward to Feishu group; no output → silent
- Never launch Claude Code yourself; prepare task descriptions and let Admin launch
- Contact other bots/agents **only via `send_message` plugin** — never `openclaw agent` CLI, never Feishu group messages
- On errors: report only, never switch to alternative methods
