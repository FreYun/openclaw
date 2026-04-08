# 生图模板（STYLE.md）

> Step 4 生图时 Read 此文件。直接复制模板填入变量。

---

## 模板 A — 封面卡

```
A vertical knowledge card, 3:4 aspect ratio (1080x1440px). Solid {背景色} background. Clean, minimal, generous whitespace.

TOP (~25%): Large bold Chinese title "{标题}" with emoji, centered or left-aligned. Smaller subtitle line below: "{副标题}".

MIDDLE (~40%): Three/four concept items in a horizontal row (ROW layout), each with a simple flat icon (or emoji) above and a bold Chinese keyword below, evenly spaced. Below the row, 1-2 lines of hook text in regular weight.

BOTTOM (~30%): Decorative area with subtle thematic illustration (hand-drawn style, related to the topic). No photographs.

FOOTER (~5%): Small gray text "市场有风险，投资需谨慎。" centered, tiny "广告" label bottom-right.

Style: Clean educational card, flat design, warm pastel palette, Chinese text, no 3D, no people.
```

---

## 模板 B — 逻辑讲解卡（上文下图）

```
A vertical knowledge card, 3:4 aspect ratio (1080x1440px). Solid {背景色} background. Clean layout.

TOP (~10%): Bold Chinese subtitle "{小标题}" with emoji, left-aligned.

MIDDLE-TEXT (~35%): 2-3 text blocks separated by generous whitespace (no lines or dividers). Each block: highlighted subtitle with {高亮色} background pill + 1-2 lines body text. Left-aligned, comfortable line spacing.

MIDDLE-DIAGRAM (~45%): A centered hand-drawn style infographic diagram. Title: "{图解标题}" in bold. Central rounded element labeled "{核心概念}". Surrounding 3 factor nodes with numbered circles, each with colored keyword + one-line explanation + small flat icon. Arrows/lines connecting factors to center. {图解类型}.

FOOTER (~5%): Small gray text "市场有风险，投资需谨慎。" centered, tiny "广告" label bottom-right.

Style: Educational infographic, hand-drawn diagram, flat icons, clean lines, warm pastels, Chinese text, no photographs, no 3D.
```

---

## 模板 C — 逻辑讲解卡（左右对比）

```
A vertical knowledge card, 3:4 aspect ratio (1080x1440px). Solid {背景色} background.

TOP (~10%): Bold Chinese subtitle with emoji.

MIDDLE (~50%): Split into two columns (LR layout) with subtle vertical divider. LEFT column: "✅ {左标题}" header in green, 3 bullet points. RIGHT column: "❌ {右标题}" header in red, 3 bullet points.

BOTTOM (~30%): Simple summary diagram or key takeaway, hand-drawn style, centered.

FOOTER (~5%): Small gray "市场有风险，投资需谨慎。" + "广告".

Style: Clean comparison card, flat design, warm pastels, Chinese text.
```

---

## 模板 D — 业绩 + 逻辑总结卡（LR 布局）

> 左栏逻辑阐述，右栏预留区域给研究部提供的真实业绩走势图。

```
A vertical knowledge card, 3:4 aspect ratio (1080x1440px). Solid {背景色} background.

TOP (~8%): Bold Chinese label "{小标题}" with emoji.

MIDDLE (~60%): Split into two columns (LR layout). LEFT column (~50%): 2-3 text blocks with highlighted subtitles and body text, separated by generous whitespace (no lines or dividers). Content explains investment logic / key metrics interpretation. RIGHT column (~50%): A designated image area with thin rounded border and subtle shadow, labeled "[PERFORMANCE CHART HERE]" — this will be replaced with a real chart screenshot provided by the research team. The image area should be vertically centered within the column.

RISK SECTION (~25%): Full-width risk disclosure text block at the bottom, light gray background, small regular font: "{完整风险提示}". Multiple lines allowed.

FOOTER (~5%): Small gray "市场有风险，投资需谨慎。" + "广告".

Style: Clean data card, minimal, professional, warm pastels, Chinese text, no decorative elements, no AI-generated charts.
```

**⚠️ 重要：右栏的业绩走势图不要让 AI 画，必须用研究部提供的真实截图。**

生成卡片后有两种处理方式：
1. **能合成**：用图片编辑工具将真实截图贴入右栏预留区域
2. **不能合成**：只生成左栏内容的卡片，业绩走势图作为帖子的下一张独立图片发布

---

## 背景色速查

| 主题 | 背景色 |
|------|--------|
| 理财/投资 | `Warm cream (#FFF8E7)` |
| 健康/养生 | `Soft sage green (#E8F5E9)` |
| 科技/数码 | `Light steel blue (#E3F2FD)` |
| 美妆/护肤 | `Soft pink (#FCE4EC)` |
| 家居/生活 | `Warm beige (#FFF3E0)` |
| 教育/学习 | `Soft lavender (#F3E5F5)` |

---

## 生图调用

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制上方模板，填入变量}",
  content: "{具体文字内容}",
  size: "1080x1440",
  workspace: "{bot workspace 路径}"
)'
```
