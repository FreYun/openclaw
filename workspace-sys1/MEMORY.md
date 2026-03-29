# MEMORY.md - 印务局长期记忆

## 特殊关怀面板

> 由 bot_main（魏忠贤）或研究部维护。处理投稿时先读此面板，按指令执行。一次性指令用后删除。

（当前无待执行指令）

---

## 永久规则

### 文字配图（text_to_image）投稿核查铁律
- 收到 `content_mode: text_to_image` 的投稿，必须核查：
  - `text_image`（图片卡片上的文字）：不为空
  - `content`（图片下方的正文）：不为空
- 缺一打回，附提示："text_to_image 模式必须同时提供 text_image（卡片文字）和 content（图下正文），请补全后重新投稿"

**解析路径（2026-03-18 教训）**：
- `content` MCP param = frontmatter 的 `content` 字段 → 图片下方长正文
- `text_image` MCP param = body（`---` 之后）→ 图片卡片上的短文字
- body 非空 = text_image 已提供，不属于 fallback，不得打回
- **参数绝对不能对调：text_image 是短的（body），content 是长的（frontmatter content）。传反会导致 XHS 页面卡死。**
