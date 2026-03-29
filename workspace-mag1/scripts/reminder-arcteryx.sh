#!/bin/bash
# One-time reminder: pack Arcteryx shoes
# Fires at 21:00 on 2026-03-17, then removes itself from cron

MSG="⏰ 提醒：出门前记得把始祖马装进包里！"

# Send via openclaw message bus
openclaw send --channel feishu --target "chat:oc_e59188e3ecdb04acd9b33843870a2249" --message "$MSG" 2>/dev/null

# Remove this cron entry after firing
crontab -l | grep -v "reminder-arcteryx" | crontab -
