#!/bin/bash
bash /home/rooot/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh \
  -a bot7 \
  -m image \
  -t "Claude 源码泄露，我看到了什么？" \
  -b /home/rooot/.openclaw/workspace-bot7/temp/bot7-draft-claude-body.txt \
  -c "$(cat /home/rooot/.openclaw/workspace-bot7/temp/claude-content.txt)" \
  -T "AI，科技，投资，我的理财日记，职场" \
  -r "direct:ou_fe187b618161b60af2d961f3e2e78ed7" \
  -i "/home/rooot/.openclaw/workspace-bot7/memory/images/20260401_162410_Large_bold_Chinese_title_text_51_万行代码裸奔_/001.png"
