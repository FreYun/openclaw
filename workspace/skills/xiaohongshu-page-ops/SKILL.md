---
name: xiaohongshu-page-ops
description: Precise Xiaohongshu (小红书) page operations: click post, close post, click reply target, click avatar and recognize posts on profile, return home after failures, and reply to comments from notification page (日常运营). Use when operating 小红书页面、点帖子、关帖子、精准回复、通知页回复评论、点头像、进主页认帖子、多次失败后返回首页.
---

# 小红书页面操作清单 (Xiaohongshu Page Operations)

本 skill 与 **xiaohongshu-browser** 配合使用：先读 xiaohongshu-browser 掌握 browser 工具与 ref/snapshot 规则，再按本清单执行以下 6 类操作，避免点错、回复错人、ref 混用。

**铁律**：每次点击/跳转后必须重新 `snapshot`，后续操作只用**当前这份** snapshot 里的 ref，不跨 snapshot 用 ref。

**执行本清单时禁止关闭 gateway**：在点帖子、关帖子、通知页回复、点头像等任何使用 browser 的操作过程中，**不得**关闭或重启 OpenClaw gateway；browser 报错时先按 ref 失效/兜底处理，只有用户明确要求时才可动 gateway。

**执行本清单时禁止关闭 gateway**：进行小红书页面操作（点帖子、回复、通知页等）期间，**禁止**执行关闭、停止或重启 OpenClaw gateway 的命令或操作。即使 browser 报错（如连不上、ref 失效），也先按技能内的兜底/重试处理，不要擅自关 gateway；只有用户明确要求重启/关闭时才执行。

---

## 1. 点击帖子（进入帖子详情）

**目标**：从列表（首页推荐流 / 频道流 / 通知列表）正确点进**某一条帖子**，而不是点成用户主页。

### 1.1 在首页/推荐流

- 当前 snapshot 里，每条卡片通常有：
  - **帖子链接**：`link [ref=ex]`，`/url` 以 **`/explore/`** 开头（点进去是帖子详情）。
  - **作者链接**：`link "昵称" [ref=ey]`，`/url` 以 **`/user/profile/`** 开头（点进去是用户主页）。
- **只点 `/explore/` 的 ref**。要点哪条帖，就按标题/作者名找到那张卡片，在该卡片**同一块结构**里取 `/explore/` 的 ref，再 `act` click。
- 点完立刻 `snapshot`，用新 snapshot 的标题/作者核对是否进对帖；不对就返回列表，用**当前** snapshot 再找一次再点。

### 1.2 若点的是帖子图片且页面没跳转、只是放大

- 有时点的是卡片里的**图片**而不是帖子链接，页面不会跳转到详情，只会弹出大图/放大层（如 lightbox）。
- 此时 DOM 已变（多了遮罩、大图、关闭按钮等），**直接再执行一次 `snapshot`** 即可：用新 snapshot 里的 ref 操作当前画面（例如点「关闭」退出放大，再点正确的 `/explore/` 链接进帖子）。

### 1.3 在通知页（评论和@）

- 通知页每条是「谁 · 评论了你的笔记/回复了你的评论 · 时间 · 评论内容 · **回复**」。
- **要回复时：只点该条内的「回复」按钮**（在 snapshot 里找该条对应的「回复」文案/按钮的 ref），点后会出现回复输入框或跳转到回复场景，再输入发送即可。**不要点用户头像/用户链接**（`/user/profile/`），点进去是用户首页，无法在该条评论下回复，也容易搞错对象。
- 若要进帖子详情看全文：再找该条内「进入笔记」/「查看笔记」等 `/explore/` 的 ref；只点该条所在行内的 ref，不用其他行的 ref。

---

## 2. 关闭帖子 / 关闭放大图（退出详情或弹层）

**目标**：从帖子详情页、或从「只放大图片未跳转」的弹层，回到上一级（列表/通知），不依赖失效 ref。

### 2.1 优先方式

- **浏览器后退**：`browser` → `{ "action": "navigate", "targetUrl": "上一页 URL" }`，或若工具有 `goBack` 则用其。
- 或当前 snapshot 里找 **返回/关闭**：如「返回」按钮、箭头、关闭图标，取该 ref 后 `act` click。
- **若是点了图片只放大、没跳转**：先 `snapshot` 拿到当前弹层结构，在 snapshot 里找放大层的**关闭**按钮/图标 ref，点掉后再 snapshot，即可回到列表继续点 `/explore/` 进帖。
- 若在其它弹层/浮层内：先找该层内的关闭/返回，用其 ref 点一次，再 `snapshot` 确认是否回到列表。

### 2.2 注意

- 关闭/返回后 DOM 会变，**必须**再 `snapshot`，后续操作全部用新 ref。

---

## 3. 精准点击回复（回复要对人、对帖）

**目标**：在「回复某人某条评论」时，确保点的是**该条评论对应的入口**，不把 A 的回复发到 B 的评论下。

### 3.1 在帖子详情页内回复某条评论

- 先 `snapshot`（建议非 compact，便于看到评论树）。
- 按**评论者昵称 + 评论内容片段 + 时间**在 snapshot 里定位**唯一一条**评论。
- 在该条评论**同一块结构**里找「回复」按钮/链接的 ref，用该 ref 点「回复」。
- 点后再 `snapshot`，确认输入框/回复对象是否对（例如是否 @ 了正确的人），再输入、发送。

### 3.2 从通知页去回复

- 通知页每条结构类似：`link 用户 [ref]` + 文案「评论了你的笔记…」/「回复了你的评论…」+ 时间 + 评论内容 + **「回复」**。
- **回复方式**：**只点该条内的「回复」按钮/链接**（在 snapshot 里找该条对应的「回复」的 ref），点后输入回复并发送即可。**不要点用户头像或用户链接**，点进去是用户首页，不能在该条评论下回复，且容易把 A 的回复搞到 B。
- **精准对应**：要回复哪一条，就在**那一条通知块内**找「回复」的 ref，不要用其他行的 ref（例如第 1 条有 e33、e34…，第 2 条有 e35、e36…，要回第 1 条就只点第 1 条里的「回复」ref）。

### 3.3 禁止

- **禁止**用「上一份 snapshot 的 ref」或「随便一个回复/链接」来回复，否则极易出现「A 的回复给了 B」。

---

## 4. 精准点击用户头像（进主页后能识别帖子）

**目标**：点用户头像/昵称进入其主页，并在主页上正确识别「帖子」（笔记）而非其他内容。

### 4.1 点头像/昵称

- 在**当前** snapshot 里找到对应用户的 link：通常为 `link "昵称" [ref=ex]` 或头像图对应的 link，`/url` 为 `/user/profile/...`。
- 用该 ref 做一次 click，等 1–2 秒后 `snapshot`。

### 4.2 在用户主页识别帖子

- 用户主页 URL 形如：`/user/profile/xxx`。新 snapshot 里会有该用户的笔记流。
- **帖子（笔记）**：`link [ref=ex]` 的 `/url` 以 **`/explore/`** 开头，且同一块常有标题、点赞数等。
- **非帖子**：如「收藏」「赞过」、广告、关注按钮等，不要误当成帖子点。
- 需要进某条笔记时，只点该条对应的 **`/explore/`** ref；要点另一条就再 `snapshot` 后在新 snapshot 里取新 ref。

### 4.3 返回

- 从主页返回：用 2 的「关闭/返回」或浏览器后退，再 `snapshot`。

---

## 5. 多次失败后返回首页

**目标**：连续多次操作失败（ref 失效、点错页、找不到元素）时，不反复用旧 ref 死磕，而是回到已知状态再继续。

### 5.1 何时视为「多次失败」

- 同一 ref 报错 `Unknown ref` / `Element not found or not visible` 等 ≥ 1 次，且重试仍失败；或
- 连续 2～3 次 `act` 或 `snapshot` 后仍达不到目标（例如始终进不到帖子、始终点不到回复）。

### 5.2 标准动作

1. **立即停止**用当前 ref 和当前 snapshot 继续操作。
2. **直接导航回首页**：  
   `browser` → `{ "action": "navigate", "targetUrl": "https://www.xiaohongshu.com/explore" }` 或 `https://www.xiaohongshu.com`。
3. 等 1–2 秒后 **重新 snapshot**。
4. 后续所有操作基于这份**新 snapshot** 的 ref：要进帖就再按 1 找 `/explore/` 点；要进通知就再导航到通知页再 snapshot 再按 3 精准回复。

### 5.3 不要

- 不要在同一失效 ref 上反复重试超过 2 次。
- 不要在不 snapshot 的情况下用「记忆里的 ref」继续点。

---

## 6. 在通知页面精准回复用户评论（日常运营）

**目标**：从「通知 → 评论和@」列表里，**先锁定要回复的那一条通知**，再**只点该条内的「回复」按钮**完成回复；**不要点用户头像/用户链接**，否则会进用户首页、无法在该条评论下回复且容易串行。这是日常运营里最常用的一环。

### 6.1 进入通知页并拿到当前 snapshot

1. 导航到通知页：  
   `navigate` → `https://www.xiaohongshu.com/notification?channelTabId=mentions`（评论和@）。
2. 等 1～2 秒后执行 **snapshot**（建议 `compact: true` 先看全貌）。
3. 后续所有「选哪一条、点哪个 ref」都基于**这一份** snapshot，不跨 snapshot 用 ref。

### 6.2 在 snapshot 里锁定「要回复的那一条」

通知列表每条大致结构（顺序可能略有出入）：

- 一条里的内容：**用户链接/头像**（常带 ref） + **「评论了你的笔记」/「回复了你的评论」** + **时间** + **评论内容摘要** + 有时有 **「回复」** 文案或可点区域。
- 用 **「谁 + 评论内容片段 + 时间」** 在 snapshot 里唯一确定一条，例如：「Wedi（Root）」「别纠结出厂序列…」「18分钟前」对应同一条。

**规则**：只认「用户名 + 评论内容 + 时间」都匹配的那一条；若有多条相似，用更长的评论片段或时间区分。

### 6.3 用 JS 直接点击该条的「回复」按钮（推荐）与兜底

**优先用 JS 在页面内找到目标条目的「回复」并点击**；若 JS 报错（如 `querySelectorAll` on null），**必须判空并改用 snapshot 的 ref 点「回复」**，不要对同一段脚本反复重试。

#### 6.3.1 JS 写法要求（避免 null 报错）

- 错误原因常见为：脚本里对「容器」调用了 `querySelectorAll`，但容器没找到（`querySelector` 等返回 null），导致 `null.querySelectorAll` 抛错。
- **硬性要求**：凡是对「可能为 null」的变量调用 `.querySelector`、`.querySelectorAll`、`.closest` 等，**必须先判空**。示例：
  - `const container = document.querySelector('...'); if (!container) return { ok: false, reason: 'container not found' }; container.querySelectorAll(...)`
  - 或：**不依赖容器**——用 `document.querySelectorAll` 在整页找所有文本为「回复」的按钮/链接，再遍历判断其父节点链是否包含目标用户名/评论内容，锁定属于「那一条」的按钮再 `el.click()`。这样不会因为「容器」不存在而挂掉。
- 若执行脚本后报错含 `Cannot read properties of null (reading 'querySelectorAll')`（或类似）：**立即改用 6.3.2 兜底**，不要原样重试同一段 JS。

#### 6.3.2 兜底：用 snapshot 里该条的「回复」ref 点

- 在**当前**通知页 snapshot 里，用 6.2 锁定的「谁+内容+时间」找到**那一条**，在该条对应的结构里找文案为「回复」的 **link/button 的 ref**（不要用用户头像/用户链接的 ref）。
- 用 `browser` → `act` → `{ "kind": "click", "ref": "<该 ref>" }` 点击。点完再 snapshot，确认进入回复输入或跳转，再按 6.5 输入发送。
- 若 snapshot 里「回复」没有独立可点 ref（只有纯文案）：可再试一次「进笔记」类 link（该条内的 `/explore/`）进帖子详情，在详情里点该条评论的「回复」。

#### 6.3.3 若 JS 可用时的逻辑示例（必须判空）

1. **定位到「要回复的那一条」**：用 6.2 的「用户名」或「评论内容片段」在 DOM 里找包含该文本的节点，再 `node.closest('li')` 或 `closest('[class*="item"]')` 等得到容器；**若 `container` 为 null，直接 return，走 6.3.2 兜底**。
2. **在该容器内找「回复」**：`const replyBtn = container.querySelector(...)` 或遍历子节点找 `textContent.trim() === '回复'` 的可点击元素；**若 `replyBtn` 为 null，return 并走兜底**。
3. **点击**：`replyBtn.scrollIntoView({ block: 'center' }); replyBtn.click();`。

执行完后 **snapshot** 一次，再按 6.5 输入并发送。**不要点用户头像/用户链接**（会进用户首页）。

### 6.4 若点击「回复」后进入帖子详情或弹层

- 再 **snapshot** 一次，看当前是帖子详情还是弹层内的回复框。
- 若已是回复输入框：直接按 6.5 输入并发送。
- 若在帖子详情页：在评论列表里用 **「昵称 + 评论内容片段」** 找到同一条评论，用 ref 或再用 JS 在该条内点「回复」，再输入发送。

### 6.5 输入回复并发送（与 xiaohongshu-browser 评论流程一致）

- 先 **click 评论输入框** 聚焦，再 **type** 回复内容，再在**当前 snapshot** 里找「发送」按钮的 ref 并 click。
- 若输入框在视口外或报 `not found or not visible`：先滚动到输入框区域再 snapshot，用新 ref 再点、再输入、再发。
- 发送后可再 snapshot，在评论列表里确认是否出现刚发的回复（内容或条数变化）。

### 6.6 回复完一条后，继续回复下一条

- 若要从通知页再回列表：**navigate** 回 `https://www.xiaohongshu.com/notification?channelTabId=mentions`，再 **snapshot**。
- 在**新 snapshot** 里再按 6.2～6.5 锁定下一条、选入口、进帖/点回复、输入发送。**每条都重新 snapshot，每条都用当前 snapshot 的 ref**，不复用上一条的 ref。

### 6.7 禁止与小结

- **禁止**：点用户头像/用户链接（会进用户首页）；用「上一份 snapshot」的 ref 或「别的行的 ref」点回复，否则极易「A 的回复给了 B」。
- **常见错误**：若 browser act 报错含 `querySelectorAll`、`null`、`Invalid evaluate function`：多为脚本里对未找到的容器调用了 `.querySelectorAll`。**不要重试同一段 JS**，改用在当前 snapshot 里该条对应的「回复」ref 做 act click（见 6.3.2 兜底）。
- **小结**：通知页精准回复 = **进通知页 snapshot → 用「谁+内容+时间」锁定一条 → 优先用 JS 在该条内点「回复」（脚本必须判空）；若 JS 报错则用该条「回复」ref 点 → 输入发送 → 下一条重新 snapshot 再重复**。

---

## 速查表

| 操作                 | 关键点                                                                 |
|----------------------|------------------------------------------------------------------------|
| 点击帖子             | 只点 **`/explore/`** 的 ref；同卡片内取 ref；点完 snapshot 核对       |
| 关闭帖子             | 后退或点返回/关闭；之后必 snapshot                                    |
| 精准点击回复         | 按「谁+评论内容」定位到**同一条**，只用该条内的回复/进笔记 ref         |
| **通知页精准回复**   | 通知页 snapshot → 锁定一条 → 用 JS 点该条「回复」（脚本须判空，避免 querySelectorAll on null）；若 JS 报错则用该条「回复」ref 点 → 输入发送 |
| 点用户头像           | 用 `/user/profile/` 的 ref；进主页后只把 **`/explore/`** 当帖子       |
| 多次失败后           | 停用旧 ref → navigate 回首页 → 再 snapshot → 用新 ref 继续            |

与 xiaohongshu-browser 一起用时：**先 snapshot，再在当页用当前 ref 做一件事，做完再 snapshot**，可最大程度避免点错、回复错人、ref 失效。
