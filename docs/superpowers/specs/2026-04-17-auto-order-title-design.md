# 订单标题自动生成 — 设计文档

**日期**: 2026-04-17
**模块**: commercial(订单/草稿系统)
**类比**: Claude 给会话自动取标题

## 背景与目标

当前订单详情页的"订单标题"字段(`orders.title`)默认为空字符串,UI 上显示占位符 `(点击添加订单标题)`,需要用户手动点击编辑。客户实际并不愿意为每个订单想一个标题,标题字段长期为空,详情页可读性差。

**目标**: V1 草稿生成完成后,后端异步调用 Qwen 3.5 根据草稿内容总结一个 ≤30 字的中文标题,写回 `orders.title`。用户不再可手动编辑该字段。

## 范围

### In scope

- 新增后端服务 `title-gen.js` 调用现有 Qwen 3.5 端点
- 在 V1 草稿生成的 `ready` 节点之后异步触发标题生成
- 移除后端 `PATCH /api/orders/:id` 对 `title` 字段的修改能力
- 移除前端 `OrderDetail.vue` 订单标题的点击编辑 UI
- 修改占位符文案为"生成中"语义

### Out of scope

- 不动 `draft.title`(草稿正文标题,由 bot 在生成草稿时给出,与订单标题是两个独立字段)
- V2/V3 草稿不触发标题重生成(只 V1 触发一次)
- 不提供"重新生成订单标题"按钮
- 不引入新的 LLM 依赖(不接 Anthropic SDK,不改 `package.json`)

## 架构

### 数据流

```
client → POST /api/orders/:id/generate
   ↓
draft_generation_request 进入 pending_review (研究部审批)
   ↓
研究部批准 → startDraftGenerationFromRequest()
   ↓
spawn openclaw agent → 生成 draft (含 draft.title / content / tags)
   ↓
UPDATE drafts SET status='ready' (主流程结束,返回客户端)
   ↓
判断 (request.version === 1 && order.title 为空)
   ├─ 否 → 流程结束
   └─ 是 → setImmediate(autoFillOrderTitle)  // fire-and-forget
              ↓
           generateOrderTitle(draft.title, draft.content)  via Qwen 3.5
              ↓
           UPDATE orders SET title = ? WHERE id = ? AND (title = '' OR title IS NULL)
              ↓
           前端下次 refreshOrder() 拉到新 title
```

### 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 触发时机 | 仅 V1,且 `order.title` 为空 | 类似 Claude 会话取名,首次生成,不覆盖 |
| 模型 | 复用 Qwen 3.5 (image-gen.js 已接) | 不引入新依赖,Qwen 中文短文本足够 |
| 同步/异步 | `setImmediate` fire-and-forget | 标题生成失败不阻塞草稿主流程 |
| 标题长度 | ≤30 字 | UI `<h3>` 单行展示,数据库 `title` 字段无硬上限,但订单 PATCH 原本限 100,这里更严 |
| 用户编辑 | 关闭手动编辑 | 用户答复"用户不能自己改 title" |

## 实现细节

### 1. 新建 `commercial/server/src/services/title-gen.js`

复用 `image-gen.js` 的 Qwen 客户端模式(常量直接重新声明,**不**从 image-gen.js export 共享,保持服务文件自包含)。

```js
// 与 image-gen.js 同样硬编码,不跨文件 import,保持服务文件自包含
const QWEN_BASE_URL = "https://dd-ai-api.eastmoney.com/v1";
const QWEN_API_KEY = "XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69";
const QWEN_MODEL = "qwen3.5-plus-2026-02-15";
const TITLE_MAX_CHARS = 30;
const REQUEST_TIMEOUT_MS = 15000;

export async function generateOrderTitle(draftTitle, draftContent) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${QWEN_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${QWEN_API_KEY}` },
      body: JSON.stringify({
        model: QWEN_MODEL,
        messages: [
          {
            role: "system",
            content:
              "你是订单命名助手。根据下方小红书草稿,生成一个不超过 30 字的中文订单标题,简洁概括主题。\n" +
              "要求:\n" +
              "1. 不要带引号、书名号、emoji\n" +
              "2. 不要前缀(如'订单:'、'标题:')\n" +
              "3. 直接返回标题字符串本身,不要任何解释",
          },
          {
            role: "user",
            content: `草稿标题:${draftTitle || "(无)"}\n\n草稿正文:\n${(draftContent || "").slice(0, 2000)}`,
          },
        ],
        temperature: 0.3,
        max_tokens: 80,
      }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`Qwen 标题生成失败 (${res.status})`);
    }
    const data = await res.json();
    let text = (data.choices?.[0]?.message?.content || "").trim();
    text = text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
    text = text.replace(/^["「『《]+|["」』》]+$/g, "").trim();
    text = text.replace(/^标题[:：]\s*/, "").trim();
    if (!text) throw new Error("Qwen 返回空标题");
    if ([...text].length > TITLE_MAX_CHARS) {
      text = [...text].slice(0, TITLE_MAX_CHARS).join("");
    }
    return text;
  } finally {
    clearTimeout(timer);
  }
}
```

注:用 `[...text]` 而非 `.slice()` 切割,避免中文 emoji 等多字节字符截一半。

### 2. 修改 `commercial/server/src/routes/drafts.js`

在 `startDraftGenerationFromRequest()` 第 170 行 `UPDATE drafts SET status='ready'` 之后,新增:

```js
if (request.version === 1 && (!order.title || order.title === "")) {
  setImmediate(() => {
    autoFillOrderTitle(order.id, result).catch((err) =>
      console.error(`[auto-title] order ${order.id} failed:`, err.message)
    );
  });
}
```

新增辅助函数:

```js
async function autoFillOrderTitle(orderId, draftResult) {
  const db = getDb();
  // 防御性二次检查:可能用户在生成期间手动改过(虽然 PATCH 已禁,但保留)
  const current = db.prepare("SELECT title FROM orders WHERE id = ?").get(orderId);
  if (!current || (current.title && current.title !== "")) return;

  const title = await generateOrderTitle(draftResult.title || "", draftResult.content || "");

  // 幂等更新:仅当 title 仍为空时才写入
  db.prepare(
    "UPDATE orders SET title = ?, updated_at = datetime('now') WHERE id = ? AND (title = '' OR title IS NULL)"
  ).run(title, orderId);
}
```

import 新增: `import { generateOrderTitle } from "../services/title-gen.js";`

### 3. 修改 `commercial/server/src/routes/orders.js`

删除 PATCH handler 中的 title 字段处理(59-63 行):

```diff
-  if (typeof body.title === "string") {
-    if (body.title.length > 100) return res.status(400).json({ error: "标题过长" });
-    updates.push("title = ?");
-    params.push(body.title);
-  }
```

也更新文件头注释(10-12 行)把 `title` 从可编辑字段列表里删掉。

### 4. 修改 `commercial/client/src/views/OrderDetail.vue`

订单标题的点击编辑相关逻辑全部移除:

- 删除 `editingOrderField === 'title'` 分支的 input + 按钮(约 880-902 行)
- 第 903-909 行 `<h3>` 简化为非编辑形式:

```diff
-<h3
-  v-else
-  :class="{ 'editable-field': canEditOrder }"
-  :title="canEditOrder ? '点击编辑标题' : ''"
-  style="margin: 0 0 8px"
-  @click="canEditOrder && startOrderEdit('title')"
->{{ order.title || '(点击添加订单标题)' }}</h3>
+<h3 style="margin: 0 0 8px">
+  {{ order.title || (isFirstDraftPending ? '(订单标题生成中…)' : `订单 #${order.id.slice(0, 8)}`) }}
+</h3>
```

`isFirstDraftPending` 计算属性定义为:V1 还未 ready 之前(`order.status` ∈ pending/awaiting_review/generating 且尚无 `draft_ready`)显示"生成中",其他情况(罕见 — Qwen 失败导致永久空)回退到 `订单 #xxxxxxxx` 短 ID。

清理动作:
- `startOrderEdit('title')`、`saveOrderEdit('title')` 调用方删除即可,函数本身保留(其他字段还在用)
- 如果 `editingOrderField` 在 ts/state 里有 union type 包含 `'title'`,移除该枚举值

### 错误处理

- Qwen 调用失败 / 超时:console.error,**不**重试,保持订单 title 为空,UI 显示回退文案
- 数据库 UPDATE 用 `WHERE (title='' OR title IS NULL)` 双写防御,即使函数被多次触发也只第一次生效
- `autoFillOrderTitle` 里所有异常都被 `.catch()` 捕获,绝不抛出到 setImmediate 顶层(否则会 crash node 进程)

### 测试

无现有测试框架(server 端 `package.json` 无 test script),按现有项目惯例**不补单测**。

手动验收:
1. 创建一个新订单,清空 title → 提交生成 → 研究部批准 → V1 ready 后等 ≤15s → 刷新订单页应看到自动填好的标题
2. 把 Qwen API_KEY 改坏 → V1 ready,标题不出现,日志看到 `[auto-title]` 报错,订单 title 仍为空,UI 显示 `订单 #xxxxxxxx` 兜底
3. V2 草稿生成不应再次触发(检查日志无 `[auto-title]` 输出)
4. 前端订单标题处不再有 hover 高亮 / 点击响应
5. 直接 `curl PATCH /api/orders/:id -d '{"title":"xxx"}'` 应返回 `没有可更新字段`(因为 body.title 分支已删,其他字段未提供)

## 风险

| 风险 | 缓解 |
|------|------|
| Qwen 服务 dd-ai-api.eastmoney.com 不可用 | 15s 超时 + 不重试 + 日志告警,UI 回退到短 ID |
| 标题生成内容不合规(出现敏感词) | system prompt 已限定输出格式;若实际遇到再加正则过滤,本期不做 |
| 旧订单(已经手动填过 title 的)被覆盖 | 不会:`WHERE title='' OR title IS NULL` 守住 |
| V1 已生成但当时 Qwen 挂了的旧订单 | 本期不做回填脚本,以后人工或后续迭代补 |

## 文件清单

| 文件 | 改动 |
|------|------|
| `commercial/server/src/services/title-gen.js` | **新增** |
| `commercial/server/src/routes/drafts.js` | 修改:V1 ready 后异步触发,新增 `autoFillOrderTitle` |
| `commercial/server/src/routes/orders.js` | 修改:PATCH 删除 title 字段处理 |
| `commercial/client/src/views/OrderDetail.vue` | 修改:移除标题点击编辑,占位符改文案 |
