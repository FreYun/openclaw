---
name: xhs-web-inspector
description: 小红书网页调试工具 — 检查 cookie、测试 CSS 选择器、截图、执行 JS、导出 DOM。用于维护 xiaohongshu-mcp 时排查选择器失效、登录状态异常等问题。
---

# xhs-web-inspector

维护 xiaohongshu-mcp 的调试工具集。**不要用生产 bot（bot1-bot9）做测试，用 bot10。**

## 工具

### 1. Cookie 检查（Python，无需浏览器）

```bash
python3 ~/.openclaw/workspace/skills/xhs-web-inspector/scripts/inspect_cookies.py <account_id>
```

输出：登录状态、关键 cookie 存在性与过期时间、全部 cookie 列表。

### 2. Inspector 二进制（Go，需要浏览器）

路径：`/home/rooot/MCP/xiaohongshu-mcp/inspector`

> 注意：同一个 profile 不能同时被两个 Chrome 实例使用（SingletonLock）。如果 MCP 服务正在用某个 bot 的 profile，inspector 无法再打开该 profile。用 bot10 做测试。

#### DOM 选择器测试

```bash
./inspector dom --profile bot10 --url "https://www.xiaohongshu.com/explore" --selectors ".login-container,.side-bar .user,div#app"
```

返回每个选择器的匹配数量、元素标签、class、文本内容、关键属性。

#### JavaScript 执行

```bash
./inspector eval --profile bot10 --url "https://www.xiaohongshu.com/explore" --js "JSON.stringify(Object.keys(window.__INITIAL_STATE__ || {}))"
```

#### 页面截图

```bash
./inspector screenshot --profile bot10 --url "https://www.xiaohongshu.com/explore" --output /home/rooot/.openclaw/media/xhs-debug-bot10.png
```

加 `--full` 截全页面。

#### 批量选择器检查

```bash
./inspector selectors --profile bot10
```

预置了 xiaohongshu-mcp 中所有关键 CSS 选择器，按页面分组（主站首页、创作者登录页、创作者首页、笔记管理页、发布页）。输出通过/失败汇总。

**当 MCP 某个功能出问题时，先跑这个命令看哪些选择器失效了。**

#### DOM 结构导出

```bash
./inspector dump-dom --profile bot10 --url "https://www.xiaohongshu.com/explore" --selector ".side-bar" --depth 4
```

导出指定元素的 DOM 树（标签、id、class、关键属性），用于了解页面结构变化。

### 公共参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--profile` | bot10 | Chrome profile 名称 |
| `--headful` | false | 有头模式（调试时看浏览器窗口） |
| `--timeout` | 30 | 超时秒数 |

## 典型排查流程

1. **功能报错 → 先查 cookie**
   ```bash
   python3 scripts/inspect_cookies.py bot7
   ```
   确认 `web_session` 和 `galaxy_creator_session_id` 存在且未过期。

2. **选择器可能失效 → 用 bot10 批量测试**
   ```bash
   ./inspector selectors --profile bot10
   ```
   看哪些选择器 ❌ 了。

3. **定位新选择器 → dump DOM**
   ```bash
   ./inspector dump-dom --profile bot10 --url URL --selector "body" --depth 5
   ```
   找到新的 class 名。

4. **验证新选择器 → dom 命令**
   ```bash
   ./inspector dom --profile bot10 --url URL --selectors ".new-selector"
   ```

5. **需要登录 bot10 → 有头模式**
   ```bash
   ./inspector screenshot --profile bot10 --url "https://www.xiaohongshu.com/explore" --headful
   ```
   浏览器窗口会弹出，手动扫码登录。

## 重新编译

```bash
cd /home/rooot/MCP/xiaohongshu-mcp
go build -o inspector ./cmd/inspector/
```

## 新增选择器

如果 xiaohongshu-mcp 代码中新增了 CSS 选择器，同步更新 `cmd/inspector/main.go` 中的 `selectorSuites` 变量。
