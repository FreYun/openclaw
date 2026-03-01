# HEARTBEAT.md

# 心跳频率：每 2 小时一次

（实际间隔在 `openclaw.json` 的 `agents.defaults.heartbeat.every` 配置，当前为 `"2h"`。）

## 心跳任务

1. **MEMORY.md 已在上方「Long-term memory」中注入，切勿 read(MEMORY.md)**（否则会重复注入到对话记录）。
2. 根据已注入内容，将「今天做了什么、学到什么、明天要做什么」写入 MEMORY.md 的 **Daily** 小节：以当日日期 `YYYY-MM-DD` 为子项，三项分别简要填写；若该日已有条目可只做补充。
3. **必须：更新 RECENT_MEMORY.md** — 从 `memory/` 目录里的 daily logs 合成近期记忆（越近日期权重越高）。若今天的内容有更新，则重写 RECENT_MEMORY.md。
4. 无其它待办时回复 `HEARTBEAT_OK`。

---

## MCP 浏览器和图片分析现状（2026-02-12）

### 已查官方文档（modelcontextprotocol/servers）

#### 浏览器
- **Puppeteer MCP** — 官方已归档
- 替代方案：原生 `web_fetch`/`web_search` 抓网页，或 **Playwriter MCP**（见下）

#### 图片分析
- **EverArt MCP** — 官方已归档，功能是 AI 图片生成（不是图片分析）
- 需要的话：找支持 vision API 的第三方 MCP

---

## Playwriter MCP — 控制用户 Chrome 浏览器

用 [Playwriter Chrome 扩展](https://chromewebstore.google.com/detail/playwriter-mcp/jfeammnjpkecdekppnclgkkffahnhfhe) 连接用户已打开的 Chrome，执行 Playwright 代码。不单独起浏览器，不会自动关闭。

1. **安装扩展**
   打开 Chrome 应用店安装 Playwriter，在目标标签页点击扩展图标启用（变绿）。

2. **配置**（已就绪）
   `gooddog.json` 已配置：
   ```json
   "playwriter": {"command": "npx", "args": ["-y", "playwriter@latest"], "env": {"PLAYWRITER_AUTO_ENABLE":"1"}}
   ```

3. **用法**
   好狗用 `mcp_call(server="playwriter", tool="execute", arguments={"code": "..."})` 即可。
   Skill：`gooddog/skills/playwriter/SKILL.md` 已包含详细用法，会自动加载。

4. **使用前提**
   - Chrome 已打开，目标页面已加载
   - 在目标标签页点击 Playwriter 扩展图标（绿色表示已连接）
