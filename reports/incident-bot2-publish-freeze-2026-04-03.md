# Incident Report: bot2 "Publish Now" Triggered System Freeze

**Date (local):** 2026-04-03  
**Time window:** 16:41–16:59 (Asia/Shanghai)  
**Systems:** xiaohongshu-mcp (port 18060), Rod/Chrome, dvc-core (system proxy, port 8080)  
**Impact:** MCP calls slowed/blocked, system-wide network became unresponsive

## Summary

At ~16:41, a pending publish entry for bot2 was moved to immediate execution. The publish pipeline initiated login checks for bot2, which started Rod/Chrome. The Rod launch failed (CDP `json/version` reset), and the login check then hit the XHS captcha flow. This sequence produced repeated browser-level network activity that traversed the system proxy (`dvc-core:8080`). The proxy accumulated many `CLOSE-WAIT` sockets, creating a system-wide connectivity degradation that appeared as a "full freeze".

## Timeline (key events)

**16:41**  
Pending queue entry appears for bot2:  
`/home/rooot/.openclaw/workspace-sys1/publish-queue/pending/2026-04-03T16-41-41_bot2_47ahp3`

**16:49:19**  
MCP starts login check for bot2:  
```
time="2026-04-03T16:49:19+08:00" level=info msg="MCP [bot2]: 检查登录状态"
```

**16:49:23**  
Login check hits profile page:  
```
time="2026-04-03T16:49:23+08:00" level=info msg="CheckBothLoginStatus [bot2] main URL: https://www.xiaohongshu.com/user/profile/me"
```

**16:53:27 (failure point)**  
Rod/Chrome launch fails when attempting to read CDP endpoint:  
```
time="2026-04-03T16:53:27+08:00" level=error msg="Tool handler panicked" panic="Get \"http://127.0.0.1:37859/json/version\": read tcp 127.0.0.1:38934->127.0.0.1:37859: read: connection reset by peer" tool=check_login_status
```

**16:54**  
New Rod profile created under `/tmp/rod/user-data/` (mtime ~16:54).  
This indicates a fresh Rod/Chrome instance was spawned.

**16:57:25–16:59:28**  
Login check retried and hits captcha page:  
```
time="2026-04-03T16:57:25+08:00" level=info msg="MCP [bot2]: 检查登录状态"
time="2026-04-03T16:58:16+08:00" level=info msg="CheckBothLoginStatus [bot2] main URL: https://www.xiaohongshu.com/website-login/captcha?redirectPath=..."
```

## Where it froze

1. **Rod/Chrome launch step** inside `check_login_status` failed (CDP connection reset).  
   This is the first hard failure and correlates with the start of network instability.

2. **Captcha flow** forced the login check into a slow, blocking state.  
   This increased browser network churn.

3. **System proxy saturation (`dvc-core:8080`)** accumulated many `CLOSE-WAIT` sockets.  
   As a system-level interceptor, `dvc-core` sits on the path of outbound requests.  
   When saturated, it affects *all* traffic, not just MCP calls.

## Evidence (logs)

Source: `/tmp/xhs-mcp-unified.log`

```
time="2026-04-03T16:49:19+08:00" level=info msg="MCP [bot2]: 检查登录状态"
time="2026-04-03T16:49:23+08:00" level=info msg="CheckBothLoginStatus [bot2] main URL: https://www.xiaohongshu.com/user/profile/me"
time="2026-04-03T16:53:27+08:00" level=error msg="Tool handler panicked" panic="Get \"http://127.0.0.1:37859/json/version\": read tcp 127.0.0.1:38934->127.0.0.1:37859: read: connection reset by peer" tool=check_login_status
time="2026-04-03T16:57:25+08:00" level=info msg="MCP [bot2]: 检查登录状态"
time="2026-04-03T16:58:16+08:00" level=info msg="CheckBothLoginStatus [bot2] main URL: https://www.xiaohongshu.com/website-login/captcha?redirectPath=..."
```

## bot2 Session ID (publish submission)

The publish submission for the frozen job is recorded in bot2 session:

- **Session ID:** `cb90e258-d37f-41d8-beef-a2f0ff93fb43`  
- **Evidence:** entry at `2026-04-03T08:42:20.066Z` (local 16:42) contains:  
  - 投稿ID: `2026-04-03T16-41-41_bot2_47ahp3`  
  - 提交时间: `16:41`  
  - “光芯片帖子已重新提交”  

File: `/home/rooot/.openclaw/agents/bot2/sessions/cb90e258-d37f-41d8-beef-a2f0ff93fb43.jsonl`

## How to track this error

Use this chain to reproduce the exact diagnosis:

1. **Confirm publish queue entry**
   - Path: `/home/rooot/.openclaw/workspace-sys1/publish-queue/pending/2026-04-03T16-41-41_bot2_47ahp3`

2. **Locate the bot2 session that submitted it**
   - Search bot2 sessions for `2026-04-03T16-41-41_bot2_47ahp3`
   - Result: session `cb90e258-d37f-41d8-beef-a2f0ff93fb43.jsonl`

3. **Correlate MCP activity**
   - Log: `/tmp/xhs-mcp-unified.log`
   - Look for bot2 events around 16:49–16:59
   - Key failure: `check_login_status` panic on CDP `json/version` reset

4. **Verify Rod spawn timing**
   - Path: `/tmp/rod/user-data/`
   - New profile directory mtime around `16:54`

5. **Explain system-wide freeze**
   - dvc-core (system proxy) on `:8080` accumulates `CLOSE-WAIT`
   - This degrades all outbound connectivity, not only MCP

## Root cause hypothesis

**Primary:** `check_login_status` for bot2 triggers Rod/Chrome. CDP launch fails and then captcha blocks.  
**Secondary:** The retry + captcha flow increases browser outbound connection churn.  
**System amplifier:** `dvc-core:8080` intercepts outbound traffic and accumulated `CLOSE-WAIT`, causing global slowdown.

## Immediate remediation options

1. Avoid triggering `check_login_status` loops while captcha is required.  
2. Reduce concurrent Rod/Chrome launch attempts per bot.  
3. Apply a global connection budget to prevent `dvc-core` saturation.
