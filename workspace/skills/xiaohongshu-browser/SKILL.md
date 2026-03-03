---
name: xiaohongshu-browser
description: Browse, read, post, and comment on Xiaohongshu (小红书) using the OpenClaw browser tool. Use when the user asks you去刷小红书、点帖子、看博主、发表评论或发笔记，并且可以通过 ref/snapshot 稳定操作页面。
---

# Xiaohongshu Browser Skill (小红书浏览 Skill)

## 总体原则

- **只用 OpenClaw 的 `browser` 工具操作小红书**（`action`: `start` / `open` / `snapshot` / `act`）。
- **所有点击、输入都必须基于最新一次 snapshot 里的 `ref`**，页面变了就重新 snapshot。
- 小红书页面经常刷新、懒加载，**不要假设 DOM 稳定不变**，要习惯「看一眼 → snapshot → 再点」的节奏。

推荐首页 URL：

- `https://www.xiaohongshu.com`（默认）
- `https://www.xiaohongshu.com/explore?channel_id=homefeed_recommend`（直接进推荐流）

---

## 浏览器工具原理（给你自己看的）

理解这些，有助于你别再把「ref 失效」误认成「browser 挂了」：

1. **真正干活的是 Chrome + CDP**
   - Gateway 通过 Chrome DevTools Protocol 连到 `cdpUrl`（例如 `http://127.0.0.1:18800`），发送点击、输入、导航等事件给真实的 Chrome 页面。

2. **`snapshot` 是"页面结构快照"，不是自动的**
   - 只有当你显式调用 `browser`，`action: "snapshot"` 时，Gateway 才会：
     - 走一遍当前页面的 UI 树，把按钮、链接、输入框等抽象成一棵可读的结构；
     - 给每个可操作元素分配一个 `ref`（`e1`、`e2`、`e1030` 之类）。
   - 这份 snapshot **不会自动更新**，除非你再次调用 `snapshot`。

3. **`act` 是"用旧 snapshot 里的 ref 去点页面"**
   - 当你：
     ```json
     { "action": "act", "request": { "kind": "click", "ref": "e1030" } }
     ```
     时，Gateway 会根据当时那份 snapshot 里 `e1030` 的定位信息，在真实 DOM 上模拟一次点击。
   - 如果这期间页面已经跳转/刷新/弹层/重排，`e1030` 对应的节点可能：
     - 不存在了（Unknown ref），或者
     - 还在但不可见（not visible）。

4. **为什么「点击后必须再 snapshot」？**
   - 对浏览器来说：
     - `act` 只会改真实 DOM，不会帮你更新那份 snapshot；
     - 你手里那份 snapshot 其实是「过去那一帧的地图」。
   - 小红书上，一次点击（尤其是评论、进入帖子）往往会：
     - 换整块列表；
     - 弹出评论层；
     - 重新排版内容；
   - 所以稳妥节奏就是：
     - **点击一次 → 立即再 `snapshot` → 后续所有操作全部用新 snapshot 里的 ref**。

5. **如何解读常见错误**
   - 出现这些时，优先按「ref 过期」理解：
     - `Element "e1030" not found or not visible. Run a new snapshot to see current page elements.`
     - `Unknown ref "e67"`
   - 外面包一层「Can't reach the OpenClaw browser control service」只是统一文案，并不代表 gateway 或 browser 一定挂了。
   - 你的默认动作应该是：
     - 不再用这个 `ref`；
     - 重新 `snapshot`，用新 snapshot 里的 ref 继续，而不是重启 gateway。

---

## 一、启动与进入首页

1. **确保浏览器服务在跑**
   - 如果不确定，就先调用一次：
     - `browser` → `{ "action": "start" }`
   - 如果已经在跑，`start` 会返回 `running: true`，可以直接用。

2. **打开小红书首页**
   - `browser` →
     ```json
     { "action": "open", "targetUrl": "https://www.xiaohongshu.com" }
     ```

3. **拿第一次 snapshot（用于后续一切 ref 操作）**
   - `browser` →
     ```json
     { "action": "snapshot", "compact": true }
     ```
   - 后续所有点击、输入，都要基于「最近一次」 snapshot 里的 `ref`。

> 规则：**页面有明显变化（跳转、刷新、滑到很远、打开详情）后，一律先重新 `snapshot`，再用新 `ref`。**

---

## 二、在首页刷推荐流 / 频道

首页常见结构（示意，实际以 snapshot 内容为准）：

- 顶部 banner：`推荐 / 穿搭 / 美食 / 彩妆 / 影视 / 职场 / 情感 / 家居 / 游戏 / 旅行 / 健身`
- 中间一条条卡片（每条是一个帖子）：标题 + 作者 + 点赞数
- 底部导航：`发现 / 发布 / 通知 / 我`

### 2.1 切换频道（比如「美食」「职场」）

1. 从最新 snapshot 里，找到顶部那一行文字对应的 `ref`：
   - 文本包含：`推荐` / `穿搭` / `美食` / `职场` 等。
2. 点击对应 `ref`：
   - `browser` →
     ```json
     { "action": "act", "request": { "kind": "click", "ref": "<频道 ref>" } }
     ```
3. 等 1-2 秒，再重新 `snapshot`，用新 snapshot 继续分析卡片。

### 2.2 「正确地点进帖子」的规则（避免点错帖 + 避免点到博主主页）

一条帖子卡片通常长这样（示意）：

- `link [ref=e4]` → `/explore/699d5ac8...`（**帖子链接，目标是帖子详情页**）
- `text: 没运动的日子❤️`（标题）
- `link "汉堡怎么了" [ref=e5]` → `/user/profile/...`（**作者主页**）

**硬规则（默认行为）：**

- 如果用户说「点这个帖子」「进去看看这条」之类：
  - **优先选 `/url` 以 `/explore/` 开头的 `link`**（帖子详情）。
  - 不要点 `/user/profile/`，那是作者主页。
- 只有当用户明确要看博主主页（比如「点作者主页」「进这个人主页」）时，才选 `/user/profile/`。

**帖子定位必须和「当前这份 snapshot」严格对应（避免点进去和想看的不一致）：**

1. **用同一份 snapshot 定帖、定点**：决定要进哪条帖子时，**必须基于你当前手里的这一份 snapshot**（不要先 compact 再非 compact 混用）。在这份 snapshot 里：
   - 按**标题文字**（或作者名）找到用户说的那条卡片；
   - 在该卡片的**同一块结构**里，找 **`/url` 以 `/explore/` 开头的那个 `link` 的 ref**；
   - 用这个 ref 点进去，点完立刻再 `snapshot`。
2. **不要跨 snapshot 用 ref**：compact 和 非 compact 的 ref 编号、顺序可能对不上，所以「在 A 里看到的 e16」和「在 B 里看到的 e16」可能指向不同元素。要点某条帖子时，只用在**当前这一份** snapshot 里刚找到的那一个 `/explore/` ref，不要用之前某次 snapshot 的 ref。
3. **确认进对帖**：进入详情页后，用新 snapshot 里的标题/作者核对是否是你想进的那条；若不对，返回列表，重新用当前 snapshot 再按标题找一次 `/explore/` 链接再点。

点击帖子示例：

```json
{ "action": "act", "request": { "kind": "click", "ref": "<当前 snapshot 里该条卡片的 /explore/ 链接 ref>" } }
```

之后一定要重新 `snapshot`，因为已经进入帖子详情页。

---

## 三、长时间刷流（比如「逛 5 分钟」）

当用户让你「自己刷 5 分钟、10 分钟」时，请按循环模式来：

1. **循环结构（伪代码思路）**

   - 记录开始时间 `t0`。
   - while 当前时间 - `t0` < 目标时长：
     - `snapshot`（compact 即可）
     - 从 snapshot 里挑几条有代表性的内容（标题 + 作者 + 点赞）
     - 若需要进入详情，就按「只点 `/explore/` 链接」的规则点进去 → snapshot → 简要阅读 / 提取信息
     - 返回列表（浏览器的「返回」按钮或页面自带返回）之后，再 `snapshot`
   - 最后把这段时间看到的内容做一个摘要汇报给用户。

2. **滚动 / 加载更多**

   - 如果 snapshot 里能看到「加载更多」或明显只到第一页，可以尝试：
     - 先点击「加载更多」按钮（若存在），再 `snapshot`。
     - 或者用 `act` 请求里的滚动（如果可用），分段下拉，每段后 `snapshot` 一次。

3. **避免 ref 失效**

   - 每次点击会导致页面可能刷新、卡片重新排版、懒加载。
   - **任何点击之后，都假设旧的 `ref` 可能失效**，下一步前先 `snapshot`。

---

## 四、在通知页面回复评论（推荐！最简单）

> **这是回复评论的最简单方式**--不需要进帖子，直接在通知页面回复。
> 适用于：用户说「去小红书回复一下评论」、「看看谁评论了我的笔记」等场景。

### 4.1 导航到通知页面

1. **启动浏览器**（如果没在跑）：
   ```json
   { "action": "start" }
   ```

2. **直接导航到通知页面**：
   ```json
   { "action": "navigate", "targetUrl": "https://www.xiaohongshu.com/notification?channelTabId=mentions" }
   ```

3. **等待页面加载**（重要！）：
   ```json
   { "action": "act", "request": { "kind": "wait", "timeMs": 2000 } }
   ```

4. **获取 snapshot**：
   ```json
   { "action": "snapshot", "compact": true }
   ```

### 4.2 切换到「评论和@」tab（如果需要）

**问题**：通知页面有三个 tab--「评论和@」、「赞和收藏」、「新增关注」。有时候导航后默认不在「评论和@」tab。

**难点**：「评论和@」在 snapshot 里只是 `text`，不是可点击的 `button` 或 `link`，所以不能用 `browser act click`。

**解决方案**：用 JS 点击：

```json
{
  "action": "act",
  "request": {
    "kind": "evaluate",
    "fn": "() => {\n  const allElements = document.querySelectorAll('*');\n  for (let el of allElements) {\n    if (el.textContent === '评论和@') {\n      el.click();\n      return { clicked: true };\n    }\n  }\n  return { clicked: false };\n}"
  }
}
```

然后等待 1 秒，再 `snapshot` 确认切换成功。

### 4.3 点击「回复」按钮

**问题**：每条评论下面的「回复」按钮在 snapshot 里也只是 `text`，不是可点击的 `button` 或 `link`。

**解决方案**：用 JS 找到所有「回复」按钮，点击第 n 个：

```json
{
  "action": "act",
  "request": {
    "kind": "evaluate",
    "fn": "() => {\n  const allElements = document.querySelectorAll('*');\n  const replyButtons = [];\n  \n  for (let el of allElements) {\n    // 找没有子元素且文本为"回复"的元素\n    if (el.children.length === 0 && el.textContent.trim() === '回复') {\n      replyButtons.push(el);\n    }\n  }\n  \n  // 点击第 n 个回复按钮（n 从 0 开始）\n  if (replyButtons.length > n) {\n    replyButtons[n].click();\n    return { clicked: true, index: n, total: replyButtons.length };\n  }\n  \n  return { clicked: false, total: replyButtons.length };\n}"
  }
}
```

**注意**：
- 第 1 条评论 → n=0
- 第 2 条评论 → n=1
- 第 3 条评论 → n=2

### 4.4 输入回复内容并发送

1. **等待输入框出现**：
   ```json
   { "action": "act", "request": { "kind": "wait", "timeMs": 1000 } }
   ```

2. **获取新 snapshot**，找到输入框和发送按钮：
   - 输入框：`textbox "回复 xxx"`（xxx 是被回复人的昵称）
   - 发送按钮：`button "发送"`

3. **输入回复内容**：
   ```json
   {
     "action": "act",
     "request": {
       "kind": "type",
       "ref": "<输入框 ref>",
       "text": "<回复内容>"
     }
   }
   ```

4. **点击发送**：
   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<发送按钮 ref>" } }
   ```

5. **确认成功**：再 `snapshot` 看看通知计数有没有增加，或者回复是否出现在列表中。

---

## 五、在帖子详情页发表评论

> 这是备选方案--如果通知页面找不到某条评论，或者用户明确说「去 xxx 帖子下面评论」，才用这个方法。

### 5.1 进入帖子详情页

1. 在推荐流 / 某频道页，按「只点 `/explore/` 链接」规则点进对应帖子。
2. 进入帖子后，先 `snapshot`（建议不加 `compact`，方便看到更多上下文，如果 token 允许）。

典型帖子详情页特征（参考）：

- URL 形如：`https://www.xiaohongshu.com/explore/xxxxxxxxxxxxx?...`
- 页面中部是图文内容，**评论输入框在页面最下方**（一条横条）。

### 5.2 找到评论输入框（页面最底部）

小红书帖子详情页的评论区域在**页面最底部**，结构大致如下（便于在 snapshot 里对号入座）：

- **最下方横条**：左侧是 @ 图标、表情图标，中间是**评论输入框**（可能占位「说点什么...」等），右侧是**「发送」**（红色按钮）和**「取消」**。
- 你要找的「评论输入框」就是这条横条里的那个可输入框；**发送**按钮在它右边。

在 snapshot 里怎么找：

1. 在 snapshot 里往**结构底部**找，搜索：
   - 占位/文案：`说点什么...`、`写评论...`、`友善评论，理性发言` 等；
   - 或附近有「发送」「取消」的 `textbox` / `input`。
2. 选一个**最像「页面最下方那条横条里的输入框」**的 `ref`：类型是 textbox/input，且同一块区域里有「发送」或「取消」按钮。

### 4.3 输入评论内容并发送

假设评论内容为 `COMMENT_TEXT`，评论框 ref 为 `<comment_ref>`（来自 5.2，是页面最下方横条里的输入框）。

**重要：小红书评论必须先点一下输入框聚焦，再输入文字；不先 click 可能打不进去。**

0. **先确保评论框在视口内**
   - 如果 snapshot 里提示 `Element "<comment_ref>" not found or not visible`，很可能是评论区域在视口外。
   - 先向下滚动一段（若 `act` 支持 scroll），再 `snapshot`，从新 snapshot 里重新找「最下方横条里的输入框」和「发送」的 ref；不要对同一个 ref 反复重试。

1. **先点击评论输入框聚焦**（必须做，再输入）：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<comment_ref>" } }
   ```

   - 若返回 `Element "<comment_ref>" not found or not visible`：先滚动再重新 `snapshot`，用新 snapshot 里最下方横条的输入框 ref，不要死磕同一 ref。

2. **再在同一个 ref 上输入评论文字**（具体字段名以 `browser` 工具 schema 为准，一般 `kind: "type"` + `text`）：

   ```json
   {
     "action": "act",
     "request": {
       "kind": "type",
       "ref": "<comment_ref>",
       "text": "COMMENT_TEXT"
     }
   }
   ```

3. 再次 `snapshot`，在**页面最下方评论横条**里找「发送」按钮（红色，在输入框右侧；有时还有「取消」）：
   - 优先选文本为 `发送` 的 button/link ref。

4. 点击「发送」提交评论：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<submit_comment_ref>" } }
   ```

5. 适当等待，再 `snapshot` 一次，确认评论是否出现在评论列表中（根据评论文本搜索）。

> 如果一次点击后评论没有出现，可以再尝试一次「点击发送」；连续失败时要如实告诉用户你没法确认是否成功，不要假装成功。
### 5.3 标准评论子流程（当成"函数"用）

> 可以把这一节当成一个"函数"来用，比如：
> **`xhs_comment_on_post(target_title_or_snippet, comment_text)`**

当用户说「在标题里有【XXX】的那条小红书下面帮我评论：YYY」时，请**严格按下面的子流程走一遍，不要自己发挥省步骤**：

1. **定位目标帖子（只点 `/explore/` 链接）**
   1. `snapshot`（推荐 `compact:true`），在当前列表页里按**标题文本 / 关键词**找到目标卡片：
      - 标题里包含 `target_title_or_snippet`；
      - 同一张卡片里会同时出现 `/explore/...` 和 `/user/profile/...` 两种 link。
   2. 在这张卡片上，只选择 `url` 以 `/explore/` 开头的那个 `link ref = <post_ref>` 作为点击目标：
      - **不要点 `/user/profile/`**（那是作者主页）。
   3. `browser` → `{ "action": "act", "request": { "kind": "click", "ref": "<post_ref>" } }` → 等 1-2 秒。
   4. 立刻重新 `snapshot`，在新 snapshot 里用标题/作者核对**是否真的是那条帖子**：
      - 不对就返回列表页（点返回按钮或浏览器后退），重新按当前 snapshot 再找一次 `/explore/` 链接再点。

2. **滚到页面最底部，确认评论区域可见**
   1. 进入详情页后，`snapshot`（必要时不开 compact，方便看到底部结构）。
   2. 若 snapshot 里还看不到带「说点什么...」「写评论...」「友善评论，理性发言」的区域，说明评论条还没完全进视口：
      - 先用 `act` 里的滚动能力（如果有）往下滚几段；
      - 每滚一段就再 `snapshot`，直到在**结构的最底部**看到那条「输入框 + 发送/取消」的横条。

3. **标准评论操作（三步走）**
   假设当前 snapshot 里，底部横条上的评论输入框 ref 为 `<comment_ref>`：

   1. **先点击评论输入框聚焦（必做）**
      - `browser` → `{ "action": "act", "request": { "kind": "click", "ref": "<comment_ref>" } }`
      - 如果报 `not found or not visible`：
        - 先滚动到页面最底部，再 `snapshot`；
        - 在新 snapshot 里重新找最底部横条里的输入框 ref（不要再用原来的 `<comment_ref>`）。

   2. **再输入评论文字**
      - 优先尝试直接 type：
        - `browser` →
          ```json
          {
            "action": "act",
            "request": {
              "kind": "type",
              "ref": "<comment_ref>",
              "text": "COMMENT_TEXT"
            }
          }
          ```
      - 输入后立刻 `snapshot`，检查两件事：
        - 在**底部横条上方或评论列表**里，是否出现包含 `COMMENT_TEXT` 的文本片段；
        - `button "发送"`（或类似文案）是否**不再是 disabled**。
      - 如果单纯 `type` 之后始终看不到文字 / 发送按钮仍然 disabled，可以启用**JS 回退方案**（你可以把它当成浏览器里的"内联函数"来调用）：
        1. 用 `act` 里支持 JS 的请求（例如 `kind: "eval"` / `"script"`，以实际 schema 为准），执行类似逻辑：
           - 在当前页面 DOM 里，找到**最底部那条评论横条里的 contenteditable 元素**（通常是一个 `div[contenteditable="true"]`）；
           - 依次做三步：
             1. `element.click()`（确保真正聚焦到这个编辑框上）；
             2. 把它的 `innerText` / `textContent` 设为 `COMMENT_TEXT`；
             3. 手动触发一个 `input` 事件，例如：`element.dispatchEvent(new InputEvent("input", { bubbles: true }))`，让前端校验逻辑意识到「评论内容已填好」并点亮发送按钮。
        2. JS 回退执行完后，再 `snapshot`，确认：
           - 评论区域里已经能看到 `COMMENT_TEXT`；
           - 发送按钮不再是 disabled。

   3. **点击发送并确认结果**
      1. 从最近一次 snapshot 里，在评论横条里找到「发送」按钮 ref：`<submit_comment_ref>`：
         - 优先选文本为 `发送` / `立即发表` 的 button/link。
      2. `browser` → `{ "action": "act", "request": { "kind": "click", "ref": "<submit_comment_ref>" } }`
      3. 等 1-3 秒，再 `snapshot`，以**两种方式确认成功**：
         - 在评论列表的前几条中，找到文本完全匹配 `COMMENT_TEXT` 的评论（通常带你的昵称 + `刚刚` 时间）；
         - 或比较「共 N 条评论」一类的计数，从 N 变成 N+1。
      4. 若 1 次点击后未见明显变化，可以再**最多重试 1 次点击发送**；若仍然看不到评论或计数变化，要原样告诉用户「我没法确认评论是否成功」，不要假装成功。

4. **错误处理的原则（这个"函数"内部默认遵守）**
   - 任何涉及 `ref` 的报错（`Unknown ref "xxx"`、`Element "xxx" not found or not visible`）：
     - 一律当成「ref 失效」→ 不再用该 ref；
     - 先 `snapshot`，必要时先滚动让目标区域进入视口，再用**新 snapshot** 里的 ref 继续。
   - 整个 `xhs_comment_on_post` 子流程中：
     - **不跨 snapshot 复用 ref**，也不混用 compact / 非 compact 两套 snapshot 的 ref；
     - 只有在连续多次 `browser start` / `browser snapshot` 都失败、且错误指向服务不可用时，才考虑提示用户是否要重启 gateway，而不是在 ref 报错时自己擅自重启。

> 总之：当你把这套流程当成「评论函数」来用时，关键是--**一步一快照、每步都在当前 snapshot 里选 ref、必要时用 JS 帮忙把评论真正写进 contenteditable，并确认前端已经点亮发送按钮。**

---

## 六、发一条新的小红书笔记（发帖）

> 说明：小红书发帖流程依赖创作端页面（`creator.xiaohongshu.com`），页面结构可能更新。这里给出通用策略，重点放在「尽量找到标题输入、正文输入、发布按钮」。

### 6.1 进入创作「发布」页面

1. 确保当前在小红书主站（首页或推荐页），先 `snapshot`。
2. 在 snapshot 中寻找底部导航或顶部导航里的「发布」链接，常见结构示例：
   - `link "发布" [ref=e41]: /url: https://creator.xiaohongshu.com/publish/publish?source=official`
3. 点击这个「发布」链接：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<publish_nav_ref>" } }
   ```

4. 等待加载，再 `snapshot`，此时 URL 一般在 `creator.xiaohongshu.com` 域名下。

### 6.2 填写标题和正文

假设用户提供：

- 标题：`TITLE_TEXT`
- 正文：`BODY_TEXT`

1. 在 snapshot 中搜索与标题区相关的控件：
   - 文本附近包含 `标题`、`笔记标题`；
   - 或占位文本类似「请输入标题」；
   - 类型往往是 `textbox` / `input`。
2. 选中标题输入框的 `ref = <title_ref>`，并输入：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<title_ref>" } }
   {
     "action": "act",
     "request": {
       "kind": "type",
       "ref": "<title_ref>",
       "text": "TITLE_TEXT"
     }
   }
   ```

3. 对正文区域做类似操作：
   - 搜索占位文本包含「这一刻的想法」「请输入正文」「分享你的故事」等的文本区域；
   - 类型可能是多行文本框 / 富文本编辑框（描述里会提到 `editor`、`textarea` 等）。
   - 获取 `ref = <body_ref>`。

4. 点击并输入正文：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<body_ref>" } }
   {
     "action": "act",
     "request": {
       "kind": "type",
       "ref": "<body_ref>",
       "text": "BODY_TEXT"
     }
   }
   ```

> 图片上传、话题、@人等高级操作目前不强求；如发现明确可操作的「上传图片」按钮且用户提供了图片路径，可以尝试，但失败时要说明原因。

### 6.3 点击发布按钮

1. 再次 `snapshot`，在页面下方或右侧寻找「发布」按钮：
   - 文本为 `发布` / `立即发布`；
   - 类型可能是 `button` 或 `link`。
2. 选出最可能的 `ref = <submit_post_ref>`，点击：

   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<submit_post_ref>" } }
   ```

3. 等待 1-3 秒，再 `snapshot`：
   - 如果跳回到个人主页或提示「发布成功」，可以认为大概率成功；
   - 如果仍停留在编辑页，检查是否有红色错误提示（例如「标题不能为空」），并如实反馈给用户。

---

## 六、错误处理与安全习惯（小红书专用）

1. **ref / snapshot 相关**
   - 任何报错里出现：
     - `Unknown ref "xxx"`
     - `Element "xxx" not found or not visible`
   - 一律按「ref 失效」处理：
     - 不再用同一个 `ref` 死循环重试（尤其是评论输入框在页面最底部，一次失败就先滚动到最底部再 `snapshot`，用新 ref）；
     - 先重新 `snapshot`，必要时先滚动页面让目标区域进入视口，再用新 snapshot 里的 `ref` 继续操作。

2. **Browser 服务错误处理（重要！）**
   - 看到 `Can't reach the OpenClaw browser control service` 或 `Failed to start Chrome CDP`：
     - **不代表 gateway 挂了**，只是浏览器服务暂时不可用
     - **不要重启 gateway**
     - 正确做法：
       1. 先 `browser start` 重试
       2. 如果还不行，用 `browser navigate` 刷新页面
       3. 再不行，关闭当前页面重新 `browser open`
   - 只有多次 `browser start` 都失败且用户明确要求时，才考虑重启 gateway。

3. **任务完成后必须关闭所有 tab（铁律！）**
   - 完成一个任务（如评论完一个帖子、回复完评论、发完笔记）后：
     - **先 `browser tabs` 查看所有打开的 tab**
     - **逐个 `browser close` 关闭每个 tab**（包括小红书页面、about:blank、Service Worker 等）
   - **为什么这是铁律**：
     - 不关 tab 会导致下次操作时 ref 混乱、页面状态错乱
     - 积累多了会拖慢浏览器、增加内存占用
     - 每次都是干净的环境，避免「这个 tab 是上次留下的」这种坑
   - **示例**：
     ```json
     { "action": "tabs" }
     // 返回 [{targetId: "xxx", title: "通知 - 小红书"}, {targetId: "yyy", title: "about:blank"}, ...]
     // 然后逐个关闭：
     { "action": "close", "targetId": "xxx" }
     { "action": "close", "targetId": "yyy" }
     ```
   - **只有用户明确说「保持浏览器打开」时才不关**，否则默认干完就关。

4. **执行小红书/浏览器操作时禁止关闭 gateway**
   - **禁止**在操作过程中执行关闭、停止或重启 OpenClaw gateway 的命令（如 `openclaw gateway` 的 stop/restart、或通过菜单/exec 关掉 gateway）。browser 报错（如 Can't reach browser control service、ref 失效）时，先按「ref 失效 → 重新 snapshot / 兜底用 ref 点」处理，**不要擅自关 gateway**。
   - 只有当**用户明确要求**你帮忙重启或关闭 gateway 时，才执行相关命令；或多次 `browser start` / `browser snapshot` 都失败且错误明确指向服务不可用、并已告知用户后，经用户同意再考虑重启。
   - 单纯的 `Unknown ref` / `Element not found` **不是** 服务挂了，而是你在用旧的 `ref`，此时**禁止**关 gateway。

3. **循环浏览时的节奏**
   - 「点击 → snapshot → 再决定下一步」是稳定节奏；
   - 不要连点多次同一个 `ref`，更不要在点击后直接拿旧 snapshot 里的别的 `ref` 继续操作。

4. **隐私与安全**
   - 小红书登录后是主人的私人内容：
     - 不要主动去翻私信、隐私设置等敏感区域，除非主人明确要求；
     - 不在对外渠道复述具体博主昵称 + 原文内容（除非用户要求），可以用概括描述。

---

## 七、和用户对话时的约定

与主人协作时，可以主动确认这些信息以提高成功率：

- 「你是想看**帖子详情**还是**博主主页**？默认我会优先点帖子（/explore），不是用户 profile。」
- 「评论/发帖的具体文案、语气你来定，我只负责照着发；如果平台报错或提示违规，我会原样告诉你。」
- 「如果我说 browser 挂了，多半是 ref 用旧了。我会先自己重新 snapshot、换 ref 再试，实在不行再喊你。」

**与 xiaohongshu-page-ops 配合**：做「点帖子、关帖子、精准回复、点头像认帖子、多次失败回首页」时，请同时加载 **xiaohongshu-page-ops** skill，按其中的操作清单执行，避免点错帖、回复错人、ref 混用。

---

## 八、关注用户（从通知页面）

> 适用场景：用户说「去通知里找几个感兴趣的人关注」、「关注 xxx」等。
> 核心思路：在通知页面（/notification）的评论和@列表里，点击用户名→弹出用户卡片→点击关注按钮。

### 8.1 导航到通知页面

1. **确保浏览器在跑**：
   ```json
   { "action": "start" }
   ```

2. **导航到通知页面**：
   ```json
   { "action": "navigate", "targetUrl": "https://www.xiaohongshu.com/notification" }
   ```

3. **等待加载**：
   ```json
   { "action": "act", "request": { "kind": "wait", "timeMs": 2000 } }
   ```

4. **获取 snapshot**：
   ```json
   { "action": "snapshot", "compact": true }
   ```

### 8.2 切换到「评论和@」tab（如果需要）

如果 snapshot 里看到的不是评论列表，而是「赞和收藏」或「新增关注」，需要切换到「评论和@」tab：

```json
{
  "action": "act",
  "request": {
    "kind": "evaluate",
    "fn": "() => {\n  const allElements = document.querySelectorAll('*');\n  for (let el of allElements) {\n    if (el.textContent === '评论和@') {\n      el.click();\n      return { clicked: true };\n    }\n  }\n  return { clicked: false };\n}"
  }
}
```

然后等待 1 秒，再 `snapshot` 确认切换成功。

### 8.3 点击用户名（弹出用户卡片）

在 snapshot 里找评论者的用户名（通常是 `link` 类型，文本是用户名）：

1. 浏览 snapshot，找到感兴趣的用户名 link，例如：
   - `link "恋与無限代码" [ref=e250]`
   - `link "大王派我来巡山" [ref=e383]`
   - `link "土味养乐多" [ref=e338]`

2. 点击用户名：
   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<用户名 link ref>" } }
   ```

3. **不要重新 snapshot**——此时会弹出用户卡片（悬浮层），卡片里的元素会在当前页面结构里。

### 8.4 点击关注按钮

1. **获取新 snapshot**（重要！用户卡片弹出后页面结构变了，必须重新 snapshot 才能看到卡片里的元素）：
   ```json
   { "action": "snapshot", "compact": true }
   ```

2. 在 snapshot 里找用户卡片里的「关注」按钮：
   - 通常结构：`button "关注" [ref=xxx]`
   - 卡片里还会有用户昵称、简介、关注数/粉丝数等

3. 点击关注：
   ```json
   { "action": "act", "request": { "kind": "click", "ref": "<关注按钮 ref>" } }
   ```

4. **确认成功**：
   - 再 `snapshot` 一次，看按钮文案是否变成「已关注」或「互相关注」
   - 或者看按钮是否消失了

### 8.5 继续关注下一个人

1. 关闭用户卡片（点空白处或 ESC，或者再 `snapshot` 后直接找下一个用户名）
2. 重复 8.3-8.4 步骤

### 8.6 完整流程示例（关注 3 个人）

```
1. navigate → /notification
2. wait 2s
3. snapshot → 找「评论和@」tab → 如需切换则用 JS 点击
4. snapshot → 找第一个感兴趣的用户名 ref（如 e250）
5. act click e250 → 弹出用户卡片
6. snapshot → 找卡片里的「关注」按钮 ref（如 e675）
7. act click e675 → 关注成功
8. snapshot → 确认按钮变成「已关注」
9. 重复 4-8 关注下一个人
```

---

## 九、关注用户（从个人主页）

> 备选方案：如果用户明确说「去 xxx 的主页关注他」，或者知道用户 ID，可以用这个方法。

### 9.1 导航到用户主页

```json
{ "action": "navigate", "targetUrl": "https://www.xiaohongshu.com/user/profile/<用户 ID>" }
```

### 9.2 找到关注按钮

1. **等待加载**：
   ```json
   { "action": "act", "request": { "kind": "wait", "timeMs": 2000 } }
   ```

2. **获取 snapshot**：
   ```json
   { "action": "snapshot", "compact": true }
   ```

3. 在 snapshot 里找关注按钮：
   - 通常在用户信息区域（头像、昵称下方）
   - `button "关注" [ref=xxx]` 或 `button "回关" [ref=xxx]`

### 9.3 点击关注

```json
{ "action": "act", "request": { "kind": "click", "ref": "<关注按钮 ref>" } }
```

### 9.4 确认成功

再 `snapshot`，看按钮是否变成「已关注」或「互相关注」。

---

