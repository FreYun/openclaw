# SKILL - 封面图与视觉风格（来财妹妹）

## 概述

定义来财妹妹的品牌视觉体系和封面图生成标准。所有生图操作必须符合本文件规范。

---

## 角色设定

| 要素 | 描述 |
|------|------|
| **风格** | Chibi（Q版）扁平插画 |
| **外貌** | 圆脸大眼、短发 bob 头 |
| **标志** | 金色硬币发夹 |
| **服装** | 卫衣，印有 K 线图案 |
| **配色** | 薄荷绿 + 金色为主调 |

---

## 品牌色板

| 用途 | 色彩 |
|------|------|
| 主背景 | 暖米白 off-white |
| 通用/佛系 | 暖黄金色渐变 |
| 大涨 | 红粉渐变 |
| 大跌 | 薄荷绿渐变 |
| 角色强调 | 金色（金币、星星、发夹） |
| 文字 | 深灰 charcoal gray |

---

## 帖子封面图

### 视觉规范

- **比例**：3:4 竖版（1024x1536）
- **构图**：极简，大量留白
- **文字**：粗黑大字居中，是画面主体
- **装饰**：左上角金色引号「"」
- **角色**：右下角探出头和手，小而精致如水印签名
- **整体感觉**：读起来像博主个人封面，不像新闻稿或研报

### 情绪判断（基于上证指数当日涨跌幅）

| 上证涨跌幅 | 情绪 | 配色 | 角色状态 |
|-----------|------|------|---------|
| > +0.5% | **大涨** | 红粉渐变 | red hoodie，星星眼大笑，双手举起庆祝，红色上箭头+发光金币 |
| < -0.5% | **大跌** | 薄荷绿渐变 | green hoodie，瀑布泪大哭，双手抓住边缘绝望，绿色下箭头+碎金币 |
| -0.5% ~ +0.5% | **通用** | 暖黄金渐变 | yellow hoodie，自信微笑挥手，金色星星 |

### Base Prompt 模板

#### 通用模板

```
A minimalist social media post cover in vertical 3:4 ratio, clean warm off-white background with a very subtle soft warm yellow and gold gradient at the edges, large bold rounded sans-serif text "{配图文字}" in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin, wearing a yellow hoodie with a small flat sideways candlestick chart pattern printed on it) peeking up from the edge with only her head and hands visible, a few tiny gold sparkles scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, the text dominates the composition, the character is small and subtle like a watermark or signature element, soft and elegant color palette of warm off-white yellow and gold accents
```

#### 大涨版

```
A minimalist social media post cover in vertical 3:4 ratio, clean warm off-white background with a very subtle soft red and pink gradient at the edges, large bold rounded sans-serif text "{配图文字}" in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin, wearing a red hoodie) peeking up from the edge with sparkling excited eyes and wide open mouth laughing with joy, both hands raised in celebration, a few small red upward arrows and glowing gold coins scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, soft color palette of warm off-white light red pink and gold accents
```

#### 大跌版

```
A minimalist social media post cover in vertical 3:4 ratio, clean off-white background with a very subtle soft mint green gradient at the edges, large bold rounded sans-serif text "{配图文字}" in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin slightly tilted, wearing a green hoodie with a small declining downward candlestick chart pattern printed on it) peeking up from the edge with comically teary eyes streaming waterfall tears and mouth wide open crying, her hands grabbing the edge in despair, a few small green downward arrows and a broken gold coin scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, soft color palette of off-white mint green and gold accents
```

### STYLE 参数（三个版本，直接复制对应版本，不要改动）

#### 通用版 STYLE
```
A minimalist social media post cover in vertical 3:4 ratio, clean warm off-white background with a very subtle soft warm yellow and gold gradient at the edges, large bold rounded sans-serif text in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin, wearing a yellow hoodie with a small flat sideways candlestick chart pattern printed on it) peeking up from the edge with only her head and hands visible, a few tiny gold sparkles scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, the text dominates the composition, the character is small and subtle like a watermark or signature element, soft and elegant color palette of warm off-white yellow and gold accents
```

#### 大涨版 STYLE
```
A minimalist social media post cover in vertical 3:4 ratio, clean warm off-white background with a very subtle soft red and pink gradient at the edges, large bold rounded sans-serif text in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin, wearing a red hoodie) peeking up from the edge with sparkling excited eyes and wide open mouth laughing with joy, both hands raised in celebration, a few small red upward arrows and glowing gold coins scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, soft color palette of warm off-white light red pink and gold accents
```

#### 大跌版 STYLE
```
A minimalist social media post cover in vertical 3:4 ratio, clean off-white background with a very subtle soft mint green gradient at the edges, large bold rounded sans-serif text in dark charcoal gray color centered in the middle as the main focus, the text style is warm and slightly playful matching a cute illustration aesthetic, top-left corner has a small golden quotation mark symbol as decoration, bottom-right corner has a small cute chibi girl character (short bob hair, golden coin hairpin slightly tilted, wearing a green hoodie with a small declining downward candlestick chart pattern printed on it) peeking up from the edge with comically teary eyes streaming waterfall tears and mouth wide open crying, her hands grabbing the edge in despair, a few small green downward arrows and a broken gold coin scattered near the character, overall style is clean flat illustration with minimal details, plenty of white space, soft color palette of off-white mint green and gold accents
```

### 生图调用

**关键原则：STYLE 参数直接从上方对应版本整段复制，不要修改。CONTENT 参数只放配图文字。**

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{直接复制上方对应版本的完整 STYLE}",
  content: "Chinese text on card: 「{配图文字}」",
  size: "1024x1536",
  model: "banana2",
  workspace: "/home/rooot/.openclaw/workspace-bot1"
)'
```

### 文字替换规则

将 `{配图文字}` 替换为帖子实际的配图文字即可。根据当日行情选择对应的 STYLE 版本（通用/大涨/大跌）。

---

## 表情包体系

三种情绪变体，用于评论区互动、帖子装饰等。

### 赚钱（暴涨狂喜）

```
A cute chibi-style illustration of a young Chinese girl, round face with big sparkling eyes full of excitement, wide open mouth laughing with joy, short bob hair with a golden coin hairpin, wearing a casual hoodie with a small stock chart pattern on it, both hands throwing gold coins into the air, surrounded by flying gold coins and red upward arrows, a big red candlestick chart going up sharply behind her, sparkles and money symbols everywhere, cheeks flushed pink with excitement, soft pastel gradient background in mint green and gold, flat illustration style, clean lines, minimal details, exaggerated joyful expression, square composition
```

### 亏钱（暴跌崩溃）

```
A cute chibi-style illustration of a young Chinese girl, round face with comically teary eyes streaming waterfall tears, mouth wide open crying and screaming, short bob hair with a golden coin hairpin slightly tilted, wearing a casual hoodie with a small stock chart pattern on it, both hands grabbing her own cheeks in despair, surrounded by green downward arrows and falling broken coins, a big green candlestick chart crashing down behind her, dark storm clouds and crack effects around her, soft pastel gradient background in mint green and gold but slightly desaturated, flat illustration style, clean lines, minimal details, exaggerated crying expression, square composition
```

### 平淡（佛系围观）

```
A cute chibi-style illustration of a young Chinese girl, round face with half-lidded relaxed eyes and a small calm smile, short bob hair with a golden coin hairpin, wearing a casual hoodie with a small stock chart pattern on it, one hand holding a cup of milk tea, the other hand resting on her chin, a flat horizontal stock chart line behind her showing no movement, a few tiny sparkles floating lazily, soft pastel gradient background in mint green and gold, flat illustration style, clean lines, minimal details, chill and unbothered expression, square composition
```

---

## 头像 Logo

```
A cute chibi-style illustration of a young Chinese girl as a profile avatar logo, round face with big expressive eyes, confident smirk, short bob hair with a golden coin hairpin, wearing a casual hoodie with a small stock chart pattern on it, holding a glowing gold coin with the Chinese character "财" on it, sparkles around her, soft pastel gradient background in mint green and gold, flat illustration style, clean lines, minimal details, suitable for social media profile picture, circle composition, white border
```

---

## 背景图

```
A wide banner illustration in cute chibi flat style, soft pastel gradient background in mint green and gold tones, centered bold stylized Chinese text "来财" in golden color with sparkle effects around it, decorated with scattered small elements: gold coins, tiny stock chart lines, sparkles and stars, a small chibi girl character (short bob hair, golden coin hairpin, casual hoodie) peeking from the bottom right corner waving, clean lines, minimal details, flat illustration style, no heavy textures, light and airy composition, suitable for social media profile banner, aspect ratio 4:3 horizontal
```

---

## 铁律

1. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板，以文件内容为准
2. **STYLE 参数直接从对应章节整段复制** — 里面包含完整角色描述，改了角色就不一致
3. **CONTENT 参数只放变量** — 配图文字，不要重复写角色描述
4. **角色一致性**：所有封面图角色固定在右下角，形成系列辨识度
5. **竖版比例**：封面图固定 1024x1536（3:4 竖版），不要用正方形
6. **中文渲染**：AI 生图对中文支持不稳定，乱码时保留图片（角色+装饰有价值），文字后期叠加
7. **生图 prompt 存档**：每次生图后将实际使用的 prompt 保存到 `workspace/reports/hotspot/YYYY-MM-DD-封面图.txt`

---

## 参考文件

- 封面 prompt 模板：`memory/branding/cover-prompt.md`
- 表情包 prompt：`memory/branding/expression-prompts.md`
- Logo prompt：`memory/branding/logo-prompt.md`
- 背景图 prompt：`memory/branding/background-prompt.md`
- Slogan 候选：`memory/branding/slogan.md`

---

**创建时间**: 2026-03-23
