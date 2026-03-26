---
name: admin-ops
description: 管理员运维技能 — 换 API Key、重启 Gateway、给内部部门开新会话（/new）。当圣上说"换key"、"重启gateway"、"/new 印务局"等时触发。
---

# 管理员运维技能

咱家（魏忠贤）的运维操作手册。

---

## 零、给内部部门开新会话（/new）

对印务局、安全部、技能部使用 `/new`，为其开启一个**全新的隔离会话**，不带历史上下文。适合：部门状态混乱、需要从头交代任务、重置会话记忆。

### 命令格式

```bash
# 开新会话并发送首条消息
openclaw agent --agent <部门id> \
  --session-id $(uuidgen) \
  --message "你的指令" \
  --json
```

### 内部部门 ID

| 部门 | agent_id |
|------|----------|
| 印务局 | `sys1` |
| 安全部 | `security` |
| 技能部 | `skills` |

### 示例

```bash
# /new 安全部 — 让安全部在全新会话里执行完整审计
openclaw agent --agent security \
  --session-id $(uuidgen) \
  --message "请执行完整安全审计，读 AGENTS.md 了解流程。" \
  --json

# /new 技能部 — 重置技能部，刷新 skill 目录
openclaw agent --agent skills \
  --session-id $(uuidgen) \
  --message "刷新所有 skill 目录。" \
  --json

# /new 印务局 — 重置印务局
openclaw agent --agent sys1 \
  --session-id $(uuidgen) \
  --message "准备好接收新的发布任务。" \
  --json
```

> **注意**：不指定 `--session-id` 时，默认续上历史会话。`/new` 明确要求全新开始时才加这个参数。

---

## 一、给 Bot 换 API Key

### 文件位置

每个 bot 的 API Key 存在：
```
/home/rooot/.openclaw/agents/<bot_id>/agent/auth-profiles.json
```

其中 `<bot_id>` 可以是：`bot1`、`bot2`、…、`bot10`、`mag1`、`main`。

### JSON 结构

```json
{
  "version": 1,
  "profiles": {
    "kimi-coding:default": {
      "type": "api_key",
      "provider": "kimi-coding",
      "key": "sk-xxx..."
    },
    "legacylands:default": {
      "type": "api_key",
      "provider": "legacylands",
      "key": "cr_xxx..."
    }
  },
  "lastGood": { ... },
  "usageStats": { ... }
}
```

### 操作步骤

1. **读取** 目标 bot 的 `auth-profiles.json`
2. **修改** `profiles.<provider>:<profile>.key` 为新 key
3. **写回** 文件（保持 JSON 格式，2 空格缩进）
4. **验证** 再读一次确认写入正确

### 批量换 Key

如果圣上要求给所有 bot 换同一个 provider 的 key：

```bash
# 示例：给所有 bot 换 legacylands key
for bot_id in bot1 bot2 bot3 bot4 bot5 bot6 bot7 bot8 bot9 bot10 mag1 main; do
  f="/home/rooot/.openclaw/agents/${bot_id}/agent/auth-profiles.json"
  if [ -f "$f" ]; then
    # 用 jq 替换 key
    jq --arg newkey "cr_新key" '.profiles["legacylands:default"].key = $newkey' "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
    echo "✅ ${bot_id} 已更新"
  fi
done
```

### 注意

- 换完 key 后**必须重启 Gateway** 才能生效（见下方）
- 不要动 `usageStats` 和 `lastGood`，只改 `profiles.*.key`
- 换 key 前先确认新 key 格式正确（kimi-coding 以 `sk-` 开头，legacylands 以 `cr_` 开头）

---

## 二、重启 Gateway

### ⚠️ 铁律：kill 再启动，不用 restart

Gateway 由两个进程组成：
- `openclaw`（父进程）
- `openclaw-gateway`（子进程）

### ⚠️ 关键：咱家自己就跑在 Gateway 里

kill gateway = 杀了自己，所以**必须把 kill + 启动包在一条 `nohup bash -c` 里**，让独立进程完成整个操作。分步执行会导致 kill 之后没人启动。

### 操作步骤（一条命令搞定）

```bash
nohup bash -c 'pkill -f openclaw-gateway; pkill -f "openclaw$"; sleep 2; cd /home/rooot/.openclaw && openclaw gateway' > /tmp/openclaw.log 2>&1 &
```

执行后咱家会被杀掉，下次会话醒来时验证：

```bash
ps aux | grep openclaw-gateway | grep -v grep
```

### 验证成功标志

应该看到两个进程：
```
openclaw
openclaw-gateway
```

如果只看到 `openclaw` 没有 `openclaw-gateway`，查看日志排查：
```bash
tail -50 /tmp/openclaw.log
```

### 重启后咱家会怎样

- 执行重启命令后，当前会话会中断（因为 gateway 被杀了）
- 新 gateway 启动后，咱家会在下一次被唤醒时以新配置复活
- 这是正常的，不用担心

### 什么时候需要重启

- 换了 API Key 之后
- 修改了 workspace 文件（SOUL.md、IDENTITY.md 等）之后
- Gateway 进程异常（超时、无响应）时
