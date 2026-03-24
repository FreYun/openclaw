---
name: xuanma-cover
description: >
  宣妈专属封面图生成 Skill — 角色形象设定、卡片/写实两套风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为宣妈账号生成一致风格封面图的能力。
---

# 宣妈封面生成 Skill（xuanma-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

1. **style 参数不要改** — 直接从下方模板复制，改了角色和版式就不一致了。
2. **先建议再生图** — 写完稿子先推荐封面方案，研究部确认后才调用生图 MCP。
3. **颜色约定** — 中国市场：上涨 = 红色元素，下跌 = 绿色元素。
4. **日常用卡片式，重要帖子用写实版** — 月度复盘、里程碑等用写实版增强视觉效果。
5. **效果好的 prompt 记录到 `memory/好用的图片prompt.md`** 方便复用。

---

## 一、角色形象设定

| 属性 | 描述 |
|------|------|
| 性别 | 女 |
| 年龄感 | 30 岁出头 |
| 发型 | 长卷发，黑色 |
| 配饰 | 金币发夹 |
| 穿着 | 奶白色针织毛衣 + 卡其色阔腿裤 |
| 色调 | 奶白、金色、香槟色为主 |
| 气质 | 温暖亲切、从容淡定 |

附 character reference sheet（`xuanma-portrait.png` 或研究部提供的角色设定图）可提升生图一致性。

---

## 二、卡片版 STYLE 模板（日常帖子，直接复制）

```
Based on the attached character reference sheet. A card-style illustration in vertical 3:4 aspect ratio. Solid pastel-colored background. Inside is a white/cream rounded rectangle card with a subtle border. A gold double-quotation-mark (❝) decoration in the top-left corner of the card. Bold large Chinese text title centered in the upper portion of the card. In the bottom-right corner, a chibi / Q-version character partially overlapping the card border: cute East Asian woman with long wavy black hair, oversized head, small body (chibi 2:1 ratio), gold coin hair clip. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 背景色速查

| 场景 | 背景色 |
|------|--------|
| 上涨/利好 | `Warm light gold / champagne background` |
| 暴涨/突破 | `Soft coral-red / warm pink background` |
| 下跌 | `Soft mint green / light sage background` |
| 日常/中性 | `Light cream / warm beige background` |
| 佛系/长期 | `Soft lavender / light lilac background` |
| 科普/分析 | `Light sky blue / soft periwinkle background` |

### 场景表情库

| 场景 | 角色表情 + 装饰 |
|------|----------------|
| **日常/开心** | `Character: cheerful smile, one hand waving. Decorations: sparkles and small stars around her` |
| **金价上涨** | `Character: excited fist pump, starry eyes. Decorations: red upward arrows and gold sparkles floating around` |
| **小涨/偷乐** | `Character: smug satisfied grin, arms crossed. Decorations: a small red arrow floating up` |
| **思考/分析** | `Character: thoughtful expression, finger on chin. Decorations: a small lightbulb above her head` |
| **金价暴跌** | `Character: comedic crying face with waterfall tears, mouth wide open, wearing a green hoodie. Decorations: green down arrows, a broken gold coin on the ground` |
| **小跌/肉疼** | `Character: one eye squinting, biting lip cutely, peeking at phone. Decorations: green tint on phone screen, small sweat drop` |
| **大跌/摆烂** | `Character: lying flat face-down with soul leaving body (translucent ghost floating up), comedic despair. Decorations: green down arrows scattered around` |
| **抄底/偷笑** | `Character: sly grin rubbing hands together, eyes narrowed like a fox, pushing tiny shopping cart. Decorations: red sale tags floating around` |
| **佛系/长期主义** | `Character: peaceful zen expression, sitting cross-legged, holding a gold bar. Decorations: serene golden aura, lotus petals` |
| **科普/解读** | `Character: teacher pose pointing up, wearing tiny glasses. Decorations: small gears and lightbulb icons` |

---

## 三、写实版 STYLE 模板（重要帖子，直接复制）

```
Based on the attached character reference sheet. A young East Asian woman in her early 30s with long wavy black hair, wearing a cream-colored knit sweater and khaki wide-leg pants. Illustration style, soft and clean linework, warm color palette dominated by cream, gold, and champagne tones. No text, no watermark. High quality, detailed. Vertical 3:4 aspect ratio.
```

### 背景风格库

| 代号 | 风格 | 适用 |
|------|------|------|
| A | dreamy bokeh, floating golden particles, champagne gradient | 重要帖子 |
| B | golden metallic hexagons/circles floating, minimalist | 数据/分析 |
| C | golden hour sunlight, cozy indoor, lifestyle feel | 日常温暖 |
| D | upward-flowing sparkles, rising energy, lens flare | 上涨/突破 |
| E | stacked gold bars soft-focus, warm vault lighting | 囤金/长期 |
| F | ink wash + golden watercolor, traditional meets modern | 节日/特殊 |

---

## 四、配图流程

### 写完稿子后推荐封面方案

**卡片式（日常帖子）：**

```
📋 封面建议：
- 卡片文字：「xxx」
- 背景色：xxx
- 场景：xxx
```

**写实版（重要帖子）：**

```
📋 封面建议（写实版）：
- 背景风格：x（从背景风格库选）
- 角色姿态/表情：xxx
- 场景描述：xxx
```

### 研究部确认后调用生图

**卡片式：**

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制第二节的卡片版 STYLE 模板}",
  content: "{背景色}. Chinese text on card reads: {卡片文字}. {从场景表情库选对应的表情+装饰}"
)'
```

**写实版：**

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制第三节的写实版 STYLE 模板}",
  content: "{角色姿态/表情}. {背景风格库对应描述}."
)'
```

---

_宣妈（bot5）专属封面生成能力，不与其他 bot 共享。_
