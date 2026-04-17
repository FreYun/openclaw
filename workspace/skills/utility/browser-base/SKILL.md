---
name: browser-base
description: ">"
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
5. **🔴 飞书扫码必须发图** — 若会话来自飞书且页面出现二维码，必须立即将二维码截图发送到飞书对话，再用 AskUserQuestion 通知用户扫码。用户在飞书中看不到 AI 侧截图，不发图则用户永远看不到二维码，任务卡死。

> 🚨🚨🚨 **【强制铁律·绝无例外】用完必须关闭浏览器** 🚨🚨🚨
>
> **任何情况下，浏览器使用结束后的最后一步必须是：**
> ```
> browser(action="close", profile="your_account_id")
> ```
> - 任务成功完成 → 必须 close
> - 任务中途报错 → 必须 close
> - 用户打断任务 → 必须 close
> - 找不到目标内容 → 必须 close
> - 任何其他情况 → 必须 close
>
>
> **⚠️ 唯一例外：扫码登录** — 若页面显示二维码：①不要关闭浏览器 ②snapshot 确认二维码可见 ③**🔴 若会话来自飞书：立即将截图发送到飞书对话**（不发图用户看不到二维码）④AskUserQuestion 通知用户扫码 ⑤等待登录成功后继续任务 ⑥任务完成后再执行 close。
> **没有 close 的流程 = 错误的流程。渲染进程将持续占用 CPU，下次使用浏览器将报错。**
> **如果你只记得一件事，记住这件事：用完关浏览器。**

---

## 操作手册

### 启动浏览器

浏览器通常自动启动，无需手动操作。如果 browser 工具报错连接失败：

```bash
bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id
```

脚本会检查 Chrome 是否在跑，没跑就拉起来。

### 打开页面

**实际调用：**
```
browser(action="open", url="https://example.com", profile="your_account_id")
```

- 等 2-3 秒让页面加载，然后 snapshot 确认
- 如果跳转到登录页，处理登录后再继续

### 截图观察（snapshot）

**实际调用：**
```
browser(action="snapshot", profile="your_account_id")
```

返回当前页面截图和可交互元素列表。每个元素有一个 `ref` 标识符。

**ref 规则：**
- ref 只对当前截图有效
- 点击/输入/页面跳转后，旧 ref 全部失效
- 操作后必须重新 snapshot 获取新 ref

### 页面交互

**点击元素：**
```
browser(action="act", request={"kind": "click", "ref": "element_ref"}, profile="your_account_id")
```

**输入文字：**
```
browser(action="act", request={"kind": "type", "ref": "input_ref", "text": "要输入的内容"}, profile="your_account_id")
```

**执行动作（自然语言描述）：**
```
browser(action="act", request={"kind": "act", "action": "scroll down"}, profile="your_account_id")
```

常用 action：
- `scroll down` / `scroll up` — 滚动页面
- `press Enter` — 按回车
- `press Tab` — 按 Tab 切换焦点
- `go back` — 浏览器后退

### 查看标签页

**实际调用：**
```
browser(action="tabs", profile="your_account_id")
```

列出所有打开的标签页，用于切换或清理。

### 关闭标签页

**实际调用：**
```
browser(action="close", profile="your_account_id")
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

**第 5 步几乎没有例外。** 任务提前退出、报错中断、用户打断、找不到内容——所有情况都必须在退出前执行 `browser close`。**唯一例外：扫码登录分支（见下）。**

**扫码登录分支（替代标准第 3-5 步）：**
```
3a. snapshot        — 确认二维码可见
3b. 发图到飞书       — 🔴 若会话来自飞书：必须将截图发送到飞书对话（用户在飞书看不到 AI 侧截图，不发图任务卡死）
3c. AskUserQuestion — 通知用户扫码
3d. 等待            — 等用户确认登录成功
3e. 继续任务         — 执行原本的操作步骤
5.  ★ close         — 任务完成后执行
```

> 🔴 **close 检查清单**（在结束任何浏览器任务前自问）：
> - [ ] 我是否执行了 `browser(action="close", profile="your_account_id")`？
> - 如果答案是"否"或"还没有"，立即执行，然后再退出。

**示例：打开雪球查看个股信息**

**概念流程：** open → snapshot → 阅读 → close

**实际调用：**
```
browser(action="open", url="https://xueqiu.com/S/SH600519", profile="your_account_id")
browser(action="snapshot", profile="your_account_id")
# 阅读截图内容
browser(action="close", profile="your_account_id")
```

**示例：在东方财富搜索研报**

**概念流程：** open → snapshot → type → Enter → snapshot → click → snapshot → close

**实际调用：**
```
browser(action="open", url="https://data.eastmoney.com/report/", profile="your_account_id")
browser(action="snapshot", profile="your_account_id")
browser(action="act", request={"kind": "type", "ref": "search_input_ref", "text": "新能源"}, profile="your_account_id")
browser(action="act", request={"kind": "act", "action": "press Enter"}, profile="your_account_id")
browser(action="snapshot", profile="your_account_id")
browser(action="act", request={"kind": "click", "ref": "report_link_ref"}, profile="your_account_id")
browser(action="snapshot", profile="your_account_id")
browser(action="close", profile="your_account_id")
```

---

## 故障排除

| 问题 | 处理 |
|------|------|
| browser 工具超时 | 检查是否传了 `profile` 参数；运行 `ensure-browser.sh your_account_id` |
| 页面空白/加载不出 | snapshot 看状态，等几秒重试；检查 URL 是否正确 |
| ref 点击无反应 | ref 可能已过期，重新 snapshot 获取新 ref |
| 页面显示扫码登录 | **保持浏览器打开**，snapshot 确认二维码可见，**🔴 若会话来自飞书：必须立即将二维码截图发送到飞书对话**（用户在飞书中看不到截图，不发图则无法扫码），再用 AskUserQuestion 通知用户扫码，等登录成功后继续，最后再 close |
| 页面要求账号密码登录 | 用 AskUserQuestion 请用户提供凭据或协助登录 |
| CPU 持续高占用 | 检查是否有未关闭的 tab，`browser tabs` 查看后逐个 close |
| Chrome 崩溃 | 运行 `ensure-browser.sh your_account_id` 重启 |

---

## 注意事项

> 📱 **【扫码登录·飞书专项】**
>
> 当页面出现二维码需要扫码登录时：
> 1. **不要关闭浏览器**
> 2. 执行 `browser(action="snapshot", ...)` 获取含二维码的截图
> 3. **🔴 若会话来自飞书：必须将二维码截图发送到飞书对话** — 用户在飞书里看不到 AI 侧的截图，不主动发图则用户永远看不到二维码
> 4. 用 `AskUserQuestion` 告知用户扫码
> 5. 等待用户确认登录成功后继续任务
> 6. 任务完成后执行 `browser(action="close", ...)`
>
> **忘记发图 = 用户看不到二维码 = 任务卡死。**

- 浏览器操作比 MCP/API 慢，优先用 MCP 工具（如 xiaohongshu-mcp、research-mcp），浏览器是补充手段
- 不要用浏览器做可以用 `exec` 或 MCP 完成的事
- 登录态存在 Chrome profile 目录中，MCP 重启不会丢失
- 不要手动修改 Chrome profile 目录下的文件
