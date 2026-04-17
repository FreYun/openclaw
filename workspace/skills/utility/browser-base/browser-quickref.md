---
name: browser-quickref
description: "Compact browser cheat-sheet: 5-step flow, 4 iron laws, QR exception — fast reminder, minimal tokens"
---

# 浏览器速查卡（browser-quickref）

## 四大铁律
1. **必须传 profile** — 所有操作带 `profile: "your_account_id"`，省略会超时
2. **用完必须关** — 结束前必须 `browser(action="close", profile="your_account_id")`
3. **ref 即用即弃** — 页面变化后旧 ref 全部失效，操作后重新 snapshot
4. **不囤标签** — 同时最多 2-3 个 tab

## 标准五步流程

1. open     → browser(action="open",     url="…",              profile="id")
2. snapshot → browser(action="snapshot",                        profile="id")
3. act      → browser(action="act",      request={kind/ref/…}, profile="id")
4. snapshot → browser(action="snapshot",                        profile="id")  # 确认结果
5. ★close   → browser(action="close",                          profile="id")  # 必须执行

## 交互三种 kind
| kind | 用途 | 关键字段 |
|------|------|---------|
| `click` | 点击元素 | `ref` |
| `type`  | 输入文字 | `ref`, `text` |
| `act`   | 自然语言动作（scroll/press Enter/go back…） | `action` |

## ⚠️ 唯一例外：扫码登录
> **不要立即关闭浏览器**，按以下步骤处理：
> 1. snapshot 确认二维码可见
> 2. 🔴 **若会话来自飞书：必须将二维码截图发送到飞书对话**（用户看不到 AI 侧截图）
> 3. AskUserQuestion 通知用户扫码
> 4. 等用户确认登录成功后继续任务
> 5. 任务完成后再执行 close

## close 检查清单
- [ ] 已执行 `browser(action="close", profile="your_account_id")`？→ 否则立即执行

## 故障速查
| 症状 | 处理 |
|------|------|
| 超时 | 检查 profile；运行 `ensure-browser.sh your_account_id` |
| ref 无反应 | 重新 snapshot 获取新 ref |
| 页面空白 | 等几秒重新 snapshot |
| CPU 高占用 | `browser(action="tabs")` 查看后逐个 close |
