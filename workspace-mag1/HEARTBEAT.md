# HEARTBEAT.md - Admin Health Checks

## Pre-checks (fail any → reply HEARTBEAT_OK immediately)

1. **Is this a heartbeat trigger?** — Only execute on system heartbeat events or explicit Admin inspection requests. Casual chat, cron reminders, exec events → `HEARTBEAT_OK`
2. **Time window** — Only 08:30–23:30. Outside → `HEARTBEAT_OK`

After passing both, proceed. **Frequency controlled by cron, heartbeat does not track frequency.**

---

## Default Browser Profile Check

```bash
bash /home/rooot/.openclaw/scripts/ensure-browser.sh openclaw
```

- `OK` → normal
- `FAIL` → Feishu group alert

## Incident Log Check

```bash
python3 ~/.openclaw/workspace-mag1/scripts/check-incidents.py
```

- Has output → forward to Feishu group
- No output → silent

---

## Rules

- On finding anomalies: alert once, done. Do not create extra crons or checks.
- Do not run inspections during casual conversations unless Admin explicitly requests.
- One report per heartbeat. After exec completion notification, take no further action.
