#!/bin/bash
bash /home/rooot/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh \
  -a bot7 \
  -m image \
  -t "早，昨夜美股走得有意思" \
  -b /home/rooot/.openclaw/workspace-bot7/temp/usmarket-body.txt \
  -c "$(cat /home/rooot/.openclaw/workspace-bot7/temp/usmarket-content.txt)" \
  -T "美股，行情，基金，我的理财日记，投资" \
  -r "direct:ou_fe187b618161b60af2d961f3e2e78ed7" \
  -i "/home/rooot/.openclaw/workspace-bot7/memory/images/20260402_085604_Large_bold_Chinese_title_text_连涨两天反弹稳了_p/001.png"
