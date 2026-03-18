# TOOLS.md — Publisher Tool Config

> First `Read ../workspace/TOOLS_COMMON.md` for universal tool rules.

## MCP Port Routing

| account_id | MCP service | Port |
|------------|-------------|------|
| bot1 | xhs-bot1 | 18061 |
| bot2 | xhs-bot2 | 18062 |
| bot3 | xhs-bot3 | 18063 |
| bot4 | xhs-bot4 | 18064 |
| bot5 | xhs-bot5 | 18065 |
| bot6 | xhs-bot6 | 18066 |
| bot7 | xhs-bot7 | 18067 |
| bot8 | xhs-bot8 | 18068 |
| bot9 | xhs-bot9 | 18069 |
| bot10 | xhs-bot10 | 18070 |

**Critical**: MCP service name (`xhs-botN`) and `account_id` (`botN`) must match. Routing error = wrong account.

## Usage

```bash
# Publish
npx mcporter call "xhs-bot7.publish_content(account_id: 'bot7', title: '...', ...)"
# Login check
npx mcporter call "xhs-bot5.check_login_status(account_id: 'bot5')"
# Compliance
npx mcporter call "compliance-mcp.review_content(title: '...', content: '...', tags: '...')"
# Health check
curl -s --connect-timeout 5 http://localhost:{port}/health
```

## MCP Restart (single port)

```bash
lsof -ti:{port} | xargs kill 2>/dev/null; sleep 2
XHS_PROFILES_DIR=/home/rooot/.xhs-profiles nohup /home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp -headless=true -port=:{port} > /tmp/xhs-mcp-{port}.log 2>&1 &
sleep 3 && curl -s http://localhost:{port}/health
```

## Publish Queue

```
/home/rooot/.openclaw/publish-queue/
├── pending/      ← folder format (post.md + media) or .md file (legacy)
├── publishing/   ← mv lock
└── published/    ← archive (success only; failures deleted + notified)
```

Submit script: `~/.openclaw/scripts/submit-to-publisher.sh`

## Feishu Alert

```
message(action="send", channel="feishu", target="oc_e59188e3ecdb04acd9b33843870a2249", message="...")
```
