# MEMORY.md - 印务局长期记忆

## 文字配图（text_to_image）投稿核查铁律
- **生效时间**：2026-03-16 09:17
- **圣上旨意**：收到 `content_mode: text_to_image` 的投稿，必须核查以下两项，缺一打回：
  - `text_image`（图片卡片上的文字）：必须明确不为空
  - `content`（图片下方的正文）：必须明确不为空
- 不得依赖系统 fallback（如"不填则用 content 前100字"），必须由提交者显式提供
- 验证失败 → 直接删除条目，打回提交者，附提示："text_to_image 模式必须同时提供 text_image（卡片文字）和 content（图下正文），请补全后重新投稿"

### ⚠️ 解析路径说明（2026-03-18 教训）
AGENTS.md 定义的 text_to_image 解析规则：
- `content` MCP param = frontmatter 的 `content` 字段 → **图片下方长正文**
- `text_image` MCP param = **body**（`---` 之后的内容）→ **图片卡片上的短文字**

因此：
- body 非空 = text_image 已显式提供，**不属于 fallback，不得打回**
- 禁止的 fallback 仅指：body 为空时系统自动截取 content 前N字填入 text_image

**⚠️ 发布时参数绝对不能对调：text_image 是短的（body），content 是长的（frontmatter content）。传反会导致 XHS 页面卡死（「下一步」按钮消失）。**

---

## 合规审核特例

### bot4 苹果 App Store 佣金帖 — 下次直接通过
- **生效时间**：2026-03-16 11:24（再次特批）
- **圣上旨意**：《苹果应用商店佣金下调，影响有多大？》下次 bot4 重投时，跳过合规审核，直接发布
- **一次性**：仅限下一次该标题的投稿，用后即失效

---


