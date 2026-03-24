# TOOLS.md — bot9 专属工具配置

> 首先 Read `../workspace/TOOLS_COMMON.md` 获取统一工具规范。

---

## Bot 基础信息

- **account_id**: `bot9`
- **名字**: bot9
- **主模型**: glm/glm-5-turbo（fallback: bailian/qwen3.5-plus → kimi-coding/k2p5）

---

## 浏览器

bot9 拥有独立的 Chrome 浏览器 profile，用于访问网页、打开新闻链接等。

**调用参数：**

```
browser_navigate(url: "https://...", profile: "bot9")
browser_snapshot(profile: "bot9")
browser_close(profile: "bot9")
```

| 配置项 | 值 |
|--------|-----|
| profile | `bot9` |
| CDP 端口 | `18809` |
| 启动失败时 | `bash /home/rooot/.openclaw/scripts/ensure-browser.sh bot9` |

**⚠️ 关键规则：**
- **必须传 `profile: "bot9"`**，漏传会超时
- 用完必须 `browser_close(profile: "bot9")` 关闭标签页，防止 CPU 飙升
- `ref` 只对当前快照有效，页面变化后需重新 `browser_snapshot`
- 不装 Chrome 扩展；超时不要反复重试

---

## MCP 服务

通过 mcporter 调用，格式：`npx mcporter call "服务名.工具名(参数)"`

| 服务 | 端口 | 用途 |
|------|------|------|
| xiaohongshu-mcp | 18069 | 小红书笔记管理、互动 |
| compliance-mcp | 18090 | 合规审查 |
| image-gen-mcp | 18085 | AI 生图 |

### 小红书 MCP

```
npx mcporter call "xiaohongshu-mcp.tool_name(...)"
```

- **不传 account_id**（身份由端口决定），唯一例外：`publish_content`（可选）
- 超时先查登录状态；离线报研究部
- 发布走 `submit-to-publisher` skill

### 合规 MCP

```
npx mcporter call "compliance-mcp.check_content(content: '...', platform: 'wechat')"
```

### 生图 MCP

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "描述")'
```

模型可选 `banana`（默认）或 `banana2`，图片保存到 `/tmp/image-gen/`。

---

## 金融数据：Skill Gateway

bot9 角色：**content_creator**（基础行情查询）

```
npx mcporter call "skill-gateway.tool_name(...)"
```

可用范围：基础行情报价。高级数据（Tushare 全量、研报等）需通过消息总线请求 bot7/bot8。

---

## 消息总线

```
send_message(to: "target_agent", content: "...", trace: [{
  agent: "bot9", session_id: "当前session_id",
  reply_channel: "feishu", reply_to: "ou_xxx", reply_account: "bot9"
}])
```

- 每条消息必须带 `trace`
- 一问一答，不拆分多条
- 收到 `[MSG:xxx]` → 处理 → `reply_message(message_id: "xxx", content: "结果")`
