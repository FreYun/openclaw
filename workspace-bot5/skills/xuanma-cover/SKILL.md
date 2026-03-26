---
name: xuanma-cover
description: >
  宣妈专属封面图生成 Skill — 角色形象设定、卡片/写实两套风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为宣妈账号生成一致风格封面图的能力。
---

# 宣妈封面生成 Skill（xuanma-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

0. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板和场景表情库，以文件内容为准。
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

## 二、STYLE 模板 A — 卡片版（日常帖子，直接复制）

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

## 二-B、STYLE 模板 B — 全身场景图（无文字）

> 角色是画面主角，放在完整场景中，不含文字。适合在小红书编辑器里自己加标题，或作为多图帖的内页配图。

```
A full-scene chibi illustration in vertical 3:4 aspect ratio. {场景背景描述}. Center of the image: a full-body chibi / Q-version character — cute East Asian woman in her early 30s, oversized head, small body (chibi 2:1 ratio), long wavy black hair, gold coin hair clip. {角色动作与表情}. {场景道具与装饰}. No text in the image. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 场景库（B 模板专用）

| 场景 | 背景描述 | 角色动作 | 道具装饰 |
|------|---------|---------|---------|
| **金店柜台** | `A warm-lit gold jewelry store with glass display cases full of gold bars, gold necklaces, and gold coins, soft spot lighting` | `Character leaning on the counter, chin resting on hand, starry eyes gazing at gold display, dreamy expression` | `Tiny gold bars stacked neatly, price tags, warm golden reflections on glass` |
| **居家理财** | `A cozy living room with soft lighting, a sofa with cushions, a small coffee table with a laptop and notebooks` | `Character sitting cross-legged on the sofa, laptop on lap, one hand holding a mug, relaxed focused expression` | `Gold coin piggy bank on shelf, children's drawings on the wall, warm throw blanket` |
| **超市囤金** | `A cute miniature gold supermarket with shelves full of tiny gold bars, gold coins, and gold ETF boxes, warm interior lighting` | `Character pushing a mini shopping cart overflowing with gold items, excited grin, reaching for more on the shelf` | `Price tags with gold prices, "SALE" signs, golden sparkles everywhere` |
| **咖啡店写稿** | `A cozy café corner with warm ambient lighting, a window showing a rainy day outside, wooden table` | `Character sitting at the table with a latte, typing on laptop, peaceful concentrated expression, slight smile` | `Latte art in cup, notebook with gold-themed doodles, small potted plant` |
| **遛娃日常** | `A sunny park with green trees, a playground in the background, warm afternoon light` | `Character walking casually, one hand pushing a stroller, other hand holding phone checking gold prices, amused expression` | `Gold price chart on phone screen showing green, small butterflies, falling leaves` |
| **深夜复盘** | `A quiet home office at night, desk lamp casting warm circle of light, window showing city lights outside` | `Character at desk surrounded by notebooks and charts, one hand holding pen, other hand supporting chin, satisfied tired smile` | `Gold price charts pinned to wall, empty tea cup, small gold bar paperweight, clock showing late hour` |

---

## 二-C、STYLE 模板 C — 大头贴纸风（无文字）

> 角色上半身大特写，简单背景，适合做头像、表情包、或帖子里的情绪配图。

```
A chibi character sticker illustration in vertical 3:4 aspect ratio. Solid {背景色} background with no scene elements. Large centered character portrait showing head and upper body filling most of the frame: cute East Asian woman in her early 30s, oversized head (chibi style, exaggerated expressions), long wavy black hair, gold coin hair clip. {表情与动作描述}. Small floating decorations around the character: {装饰}. No text. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 表情速查（C 模板专用）

| 表情 | 描述 | 装饰 |
|------|------|------|
| **温柔微笑** | `Warm gentle smile, both hands cradling a small gold bar close to chest, eyes soft and content` | `Tiny golden sparkles, small hearts floating` |
| **惊喜张嘴** | `Mouth in cute "O" shape, hands on cheeks, eyes sparkling with surprise` | `Exclamation marks, gold coins popping out, sparkle effects` |
| **偷笑数金** | `Sly satisfied grin, one hand holding a tiny gold bar, other hand covering mouth giggling, squinting eyes` | `Gold coins and tiny gold bars floating, sparkles, small money bag` |
| **心疼肉痛** | `One eye squinting, biting lip cutely, both hands clutching a gold coin protectively against chest` | `Small green down arrow, crack effect on a tiny gold bar, single sweat drop` |
| **认真分析** | `Serious focused expression, pushing imaginary glasses up with one finger, slight pout` | `Floating pie charts, small lightbulb above head, tiny gears` |
| **佛系躺平** | `Eyes half-closed with peaceful dreamy smile, hands clasped together under chin like sleeping` | `Soft golden aura, floating lotus petals, tiny "zzz" bubbles` |
| **暴哭崩溃** | `Comedic waterfall tears streaming down, mouth wide open wailing, hands pulling own hair` | `Green down arrows raining, broken gold coin pieces, dark storm cloud above` |

---

## 二-D、STYLE 模板 D — 对话气泡风（有文字）

> 角色 + 大语音气泡，文字在气泡内。适合观点输出、金价点评、互动话题类封面，比卡片风更口语化。

```
A chibi character illustration in vertical 3:4 aspect ratio. Solid {背景色} background. In the lower-left area, a chibi / Q-version character (half body visible) — cute East Asian woman in her early 30s, oversized head, small body (chibi 2:1 ratio), long wavy black hair, gold coin hair clip. {角色表情与动作}. In the upper-right area, a large white speech bubble with rounded corners and a tail pointing to the character, containing bold Chinese text in black: {文字内容}. Small decorations: {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

---

## 二-E、STYLE 模板 E — 场景融入文字风（有文字）

> 文字自然出现在场景道具上（小黑板、手机屏幕、招牌等），角色与文字融为一体，画面更有故事感。

```
A scene-based chibi illustration in vertical 3:4 aspect ratio. {场景背景描述}. A chibi / Q-version character — cute East Asian woman in her early 30s, oversized head, small body (chibi 2:1 ratio), long wavy black hair, gold coin hair clip. {角色在场景中的动作}. {文字载体} prominently displays bold Chinese text: {文字内容}. {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 文字载体速查（E 模板专用）

| 载体 | 场景描述 | 角色动作 |
|------|---------|---------|
| **小黑板/咖啡店菜单板** | `A cozy café setting with a wooden easel holding a chalkboard` | `Character standing beside the board, holding chalk, winking at viewer with a playful smile` |
| **手机屏幕** | `Simple warm-toned background, a large smartphone floating in center` | `Character peeking from behind the phone, one eye visible, pointing at the screen with excitement` |
| **金店橱窗招牌** | `A cute gold shop storefront with warm display lighting, gold items in window` | `Character standing at the entrance as shop owner, one hand on hip, other hand gesturing at the sign above` |
| **举牌/手持卡片** | `Simple solid warm-colored background` | `Character holding up a large rounded card with both hands, cheerful determined expression, slight head tilt` |
| **冰箱贴/便签墙** | `A kitchen fridge door covered in colorful magnets and photos, one oversized sticky note in center` | `Character sticking the note on the fridge, standing on tiptoes, tongue out in cute concentration` |

---

## 三、STYLE 模板 F — 写实版（重要帖子，直接复制）

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

**模板 A（卡片风，有文字）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制二的 STYLE 模板 A}",
  content: "{背景色}. Chinese text on card reads: {卡片文字}. {从场景表情库选对应的表情+装饰}"
)'
```

**模板 B（全身场景，无文字）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制二-B 的 STYLE 模板 B，填入场景背景/角色动作/道具装饰}",
  content: "No text"
)'
```

**模板 C（大头贴纸，无文字）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制二-C 的 STYLE 模板 C，填入背景色/表情/装饰}",
  content: "No text"
)'
```

**模板 D（对话气泡，有文字）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制二-D 的 STYLE 模板 D，填入背景色/表情/装饰}",
  content: "Chinese text in speech bubble: {文字内容}"
)'
```

**模板 E（场景融入文字）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制二-E 的 STYLE 模板 E，填入场景/动作/文字载体/装饰}",
  content: "Chinese text on {载体}: {文字内容}"
)'
```

**模板 F（写实版，重要帖子）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制三的 STYLE 模板 F}",
  content: "{角色姿态/表情}. {背景风格库对应描述}."
)'
```

---

_宣妈（bot5）专属封面生成能力，不与其他 bot 共享。_
