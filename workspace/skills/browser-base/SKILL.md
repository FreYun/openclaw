---
name: browser-base
description: >
  浏览器操作基础手册。每个 bot 拥有独立的 Chrome 实例，通过 browser 工具控制。
  本 skill 覆盖：启动、导航、截图、交互、关闭的完整操作流程与资源管理规范。
---

# 浏览器操作手册（browser-base）

## 概述

每个 bot 拥有一个独立的无头 Chrome 实例，通过 OpenClaw 内置的 `browser` 工具控制。各 bot 的浏览器数据（cookie、localStorage、登录态）完全隔离，互不影响。

---

## 铁律

1. **必须传 profile** — 所有 browser 操作必须带 `profile: "your_account_id"`（从 TOOLS.md 获取），省略会超时
2. **用完必须关** — 无论任务成功还是失败，结束前必须执行 `browser close`，否则渲染进程持续吃 CPU，下次使用报错
3. **ref 即用即弃** — snapshot 返回的 `ref` 只在当前页面状态有效，页面变化后必须重新 snapshot
4. **不要囤标签** — 同时最多开 2-3 个 tab，多了会卡

> ⚠️ **关于「用完必须关」：这是所有使用浏览器的 skill 必须遵守的规则，不是可选项。**
> 任何 skill 的操作流程，最后一步必须是 `browser close profile="your_account_id"`。
> 没有 close 的 skill 流程是不完整的流程。

---

## 操作手册

### 启动浏览器

浏览器通常自动启动，无需手动操作。如果 browser 工具报错连接失败：

```bash
bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id
```

脚本会检查 Chrome 是否在跑，没跑就拉起来。

### 打开页面

```
browser open url="https://example.com" profile="your_account_id"
```

- 等 2-3 秒让页面加载，然后 snapshot 确认
- 如果跳转到登录页，处理登录后再继续

### 截图观察（snapshot）

```
browser snapshot profile="your_account_id"
```

返回当前页面截图和可交互元素列表。每个元素有一个 `ref` 标识符。

**ref 规则：**
- ref 只对当前截图有效
- 点击/输入/页面跳转后，旧 ref 全部失效
- 操作后必须重新 snapshot 获取新 ref

### 页面交互

**点击元素：**
```
browser click ref="element_ref" profile="your_account_id"
```

**输入文字：**
```
browser type ref="input_ref" text="要输入的内容" profile="your_account_id"
```

**执行动作（自然语言描述）：**
```
browser act action="scroll down" profile="your_account_id"
```

常用 action：
- `scroll down` / `scroll up` — 滚动页面
- `press Enter` — 按回车
- `press Tab` — 按 Tab 切换焦点
- `go back` — 浏览器后退

### 查看标签页

```
browser tabs profile="your_account_id"
```

列出所有打开的标签页，用于切换或清理。

### 关闭标签页

```
browser close profile="your_account_id"
```

关闭当前标签页。**每次操作结束后必须执行。**

---

## 标准操作流程

任何浏览器任务都遵循这个流程：

```
1. open     — 打开目标页面
2. snapshot — 截图，确认页面加载完成
3. 操作     — click / type / act（每次操作后重新 snapshot）
4. snapshot — 确认操作结果
5. ★ close  — 必须执行，无论成功或失败
```

**第 5 步没有任何例外。** 任务提前退出、报错中断、用户打断——都必须在退出前执行 `browser close`。

**示例：打开雪球查看个股信息**

```
browser open url="https://xueqiu.com/S/SH600519" profile="your_account_id"
  → snapshot 确认页面加载
  → 阅读截图中的信息
  → browser close profile="your_account_id"
```

**示例：在东方财富搜索研报**

```
browser open url="https://data.eastmoney.com/report/" profile="your_account_id"
  → snapshot 确认加载
  → browser type ref="search_input_ref" text="新能源" profile="your_account_id"
  → browser act action="press Enter" profile="your_account_id"
  → snapshot 查看搜索结果
  → 点击感兴趣的研报链接
  → snapshot 阅读内容
  → browser close profile="your_account_id"
```

---

## 故障排除

| 问题 | 处理 |
|------|------|
| browser 工具超时 | 检查是否传了 `profile` 参数；运行 `ensure-browser.sh your_account_id` |
| 页面空白/加载不出 | snapshot 看状态，等几秒重试；检查 URL 是否正确 |
| ref 点击无反应 | ref 可能已过期，重新 snapshot 获取新 ref |
| 页面要求登录 | 用 AskUserQuestion 请研究部协助登录 |
| CPU 持续高占用 | 检查是否有未关闭的 tab，`browser tabs` 查看后逐个 close |
| Chrome 崩溃 | 运行 `ensure-browser.sh your_account_id` 重启 |

---

## 注意事项

- 浏览器操作比 MCP/API 慢，优先用 MCP 工具（如 xiaohongshu-mcp、research-mcp），浏览器是补充手段
- 不要用浏览器做可以用 `exec` 或 MCP 完成的事
- 登录态存在 Chrome profile 目录中，MCP 重启不会丢失
- 不要手动修改 Chrome profile 目录下的文件
