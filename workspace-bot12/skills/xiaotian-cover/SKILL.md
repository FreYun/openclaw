---
name: xiaotian-cover
description: >
  小天爱黄金专属封面图生成 Skill — 猫咪角色形象设定、卡片/场景两套风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为小天账号生成一致风格封面图的能力。
---

# 小天封面生成 Skill（xiaotian-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

0. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板和场景表情库，以文件内容为准。
1. **style 参数不要改** — 直接从下方模板复制，改了角色和版式就不一致了。
2. **先建议再生图** — 写完稿子先推荐封面方案，研究部确认后才调用生图 MCP。
3. **颜色约定** — 中国市场：上涨 = 红色元素，下跌 = 绿色元素。
4. **日常用卡片式，重要帖子用场景版** — 月度复盘、里程碑等用场景版增强视觉效果。
5. **效果好的 prompt 记录到 `memory/好用的图片prompt.md`** 方便复用。

---

## 一、角色形象设定

| 属性 | 描述 |
|------|------|
| 形象 | 白色小猫咪，卡通风 |
| 特征 | 圆脸、大眼睛、橙色腮红条纹 |
| 标志动作 | 嘴里叼着/抱着一根金条 |
| 背景主色 | 粉色系为主 |
| 色调 | 粉色、金色、白色、暖色系 |
| 气质 | 可爱软萌、元气活泼 |

---

## 二、STYLE 模板 A — 卡片版（日常帖子，直接复制）

```
A card-style illustration in vertical 3:4 aspect ratio. Solid pastel-colored background. Inside is a white/cream rounded rectangle card with a subtle border. A gold bar icon decoration in the top-left corner of the card. Bold large Chinese text title centered in the upper portion of the card. In the bottom-right corner, a cute cartoon white cat partially overlapping the card border: round face, big sparkling eyes, orange blush stripes on cheeks, holding or biting a small gold bar. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, kawaii style, high quality, detailed.
```

### 背景色速查

| 场景 | 背景色 |
|------|--------|
| 上涨/利好 | `Warm light gold / champagne pink background` |
| 暴涨/突破 | `Soft coral-red / warm pink background` |
| 下跌 | `Soft mint green / light sage background` |
| 日常/中性 | `Light pink / soft rose background` |
| 佛系/长期 | `Soft lavender / light lilac background` |
| 科普/分析 | `Light sky blue / soft periwinkle background` |

### 场景表情库

| 场景 | 角色表情 + 装饰 |
|------|----------------|
| **日常/开心** | `Cat character: cheerful smile, one paw waving, gold bar tucked under other arm. Decorations: sparkles and small stars around` |
| **金价上涨** | `Cat character: excited starry eyes, both paws raised in celebration, gold bar floating above head with glow. Decorations: red upward arrows and gold sparkles` |
| **小涨/偷乐** | `Cat character: smug satisfied grin, hugging gold bar tightly, squinting eyes smugly. Decorations: small red arrow floating up, sparkle effects` |
| **思考/分析** | `Cat character: thoughtful expression, one paw on chin, wearing tiny round glasses, gold bar beside it. Decorations: small lightbulb above head, tiny gears` |
| **金价暴跌** | `Cat character: comedic crying face with waterfall tears, mouth wide open, dropping the gold bar. Decorations: green down arrows, cracked gold coin on ground` |
| **小跌/肉疼** | `Cat character: one eye squinting, biting lip cutely, clutching gold bar protectively. Decorations: green tint, small sweat drop` |
| **大跌/摆烂** | `Cat character: lying flat face-down, soul leaving body (translucent ghost cat floating up), gold bar on the ground beside it. Decorations: green down arrows scattered` |
| **抄底/偷笑** | `Cat character: sly fox-like grin, pushing tiny shopping cart full of gold bars. Decorations: red sale tags floating, gold sparkles` |
| **佛系/长期主义** | `Cat character: peaceful zen expression, sitting cross-legged on a gold bar like a meditation cushion. Decorations: serene golden aura, lotus petals` |
| **科普/解读** | `Cat character: teacher pose pointing up with paw, wearing tiny professor hat and round glasses. Decorations: small gears and lightbulb icons` |

---

## 二-B、STYLE 模板 B — 全身场景图（无文字）

> 猫咪角色是画面主角，放在完整场景中，不含文字。适合在小红书编辑器里自己加标题，或作为多图帖的内页配图。

```
A full-scene kawaii illustration in vertical 3:4 aspect ratio. {场景背景描述}. Center of the image: a cute cartoon white cat — round face, big sparkling eyes, orange blush stripes on cheeks, small body. {角色动作与表情}. {场景道具与装饰}. No text in the image. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, kawaii style, high quality, detailed.
```

### 场景库（B 模板专用）

| 场景 | 背景描述 | 角色动作 | 道具装饰 |
|------|---------|---------|---------|
| **金店柜台** | `A warm-lit gold jewelry store with glass display cases full of gold bars and gold coins, soft spot lighting, pink walls` | `Cat leaning on the counter, chin resting on paw, starry eyes gazing at gold display, dreamy expression, gold bar in other paw` | `Tiny gold bars stacked neatly, price tags, warm golden reflections on glass` |
| **办公室看盘** | `A modern office cubicle with a computer showing gold price charts, desk lamp, warm lighting` | `Cat sitting in office chair, staring intently at screen, one paw on mouse, surprised/focused expression` | `Coffee mug with gold coin logo, sticky notes on monitor, small gold bar paperweight` |
| **超市囤金** | `A cute miniature gold supermarket with shelves full of tiny gold bars, gold coins, and gold ETF boxes, warm interior lighting, pink ceiling` | `Cat pushing a mini shopping cart overflowing with gold items, excited grin, reaching for more on shelf` | `Price tags with gold prices, "SALE" signs, golden sparkles everywhere` |
| **咖啡店写稿** | `A cozy café corner with warm ambient lighting, a window showing Shanghai skyline outside, wooden table` | `Cat sitting at table with a latte, typing on laptop with paws, peaceful concentrated expression` | `Latte art with gold bar shape, notebook with gold-themed doodles, small potted plant` |
| **地铁通勤** | `A Shanghai metro train interior, morning sunlight through windows, modern clean design` | `Cat standing holding handrail, other paw scrolling phone checking gold prices, slightly anxious but amused expression` | `Gold price notification on phone screen, other commuter animals in background` |
| **深夜复盘** | `A quiet home desk at night, desk lamp casting warm circle of light, window showing Shanghai city lights` | `Cat at desk surrounded by charts and notebooks, one paw holding pen, other supporting chin, tired but satisfied smile` | `Gold price charts pinned to wall, empty milk tea cup, small gold bar paperweight, clock showing late hour` |

---

## 二-C、STYLE 模板 C — 大头贴纸风（无文字）

> 猫咪上半身大特写，简单背景，适合做头像、表情包、或帖子里的情绪配图。

```
A cute cat character sticker illustration in vertical 3:4 aspect ratio. Solid {背景色} background with no scene elements. Large centered character portrait filling most of the frame: a white cartoon cat with round face, big sparkling eyes, orange blush stripes on cheeks. {表情与动作描述}. Small floating decorations around the character: {装饰}. No text. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, kawaii style, high quality, detailed.
```

### 表情速查（C 模板专用）

| 表情 | 描述 | 装饰 |
|------|------|------|
| **温柔微笑** | `Warm gentle smile, both paws cradling a small gold bar close to chest, eyes soft and content` | `Tiny golden sparkles, small hearts floating` |
| **惊喜张嘴** | `Mouth in cute "O" shape, paws on cheeks, eyes sparkling with surprise` | `Exclamation marks, gold coins popping out, sparkle effects` |
| **偷笑数金** | `Sly satisfied grin, one paw holding a tiny gold bar, other paw covering mouth giggling, squinting eyes` | `Gold coins and tiny gold bars floating, sparkles, small money bag` |
| **心疼肉痛** | `One eye squinting, biting lip cutely, both paws clutching a gold coin protectively against chest` | `Small green down arrow, crack on a tiny gold bar, single sweat drop` |
| **认真分析** | `Serious focused expression, wearing tiny round glasses, one paw pushing glasses up` | `Floating pie charts, small lightbulb above head, tiny gears` |
| **佛系躺平** | `Eyes half-closed with peaceful dreamy smile, lying on a gold bar like a pillow` | `Soft golden aura, floating lotus petals, tiny "zzz" bubbles` |
| **暴哭崩溃** | `Comedic waterfall tears, mouth wide open wailing, paws pulling own ears` | `Green down arrows raining, broken gold coin pieces, dark storm cloud above` |

---

## 二-D、STYLE 模板 D — 对话气泡风（有文字）

> 猫咪 + 大语音气泡，文字在气泡内。适合观点输出、金价点评、互动话题类封面。

```
A cute cat character illustration in vertical 3:4 aspect ratio. Solid {背景色} background. In the lower-left area, a white cartoon cat (half body visible) — round face, big sparkling eyes, orange blush stripes on cheeks. {角色表情与动作}. In the upper-right area, a large white speech bubble with rounded corners and a tail pointing to the cat, containing bold Chinese text in black: {文字内容}. Small decorations: {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, kawaii style, high quality, detailed.
```

---

## 二-E、STYLE 模板 E — 场景融入文字风（有文字）

> 文字自然出现在场景道具上（小黑板、手机屏幕、招牌等），猫咪与文字融为一体。

```
A scene-based kawaii illustration in vertical 3:4 aspect ratio. {场景背景描述}. A cute white cartoon cat — round face, big sparkling eyes, orange blush stripes on cheeks. {角色在场景中的动作}. {文字载体} prominently displays bold Chinese text: {文字内容}. {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, kawaii style, high quality, detailed.
```

### 文字载体速查（E 模板专用）

| 载体 | 场景描述 | 角色动作 |
|------|---------|---------|
| **小黑板** | `A cozy pink-toned room with a wooden easel holding a chalkboard` | `Cat standing beside board, holding chalk in paw, winking at viewer` |
| **手机屏幕** | `Simple warm pink background, a large smartphone floating in center` | `Cat peeking from behind phone, one eye visible, pointing at screen excitedly` |
| **金价看板** | `A cute gold tracking station with warm pink and gold decor` | `Cat standing next to a digital display board, one paw on hip, other pointing at the board` |
| **举牌/手持卡片** | `Simple solid pink background` | `Cat holding up a large rounded card with both paws, cheerful determined expression` |
| **便签墙** | `A pink cork board covered in colorful notes and gold stickers, one oversized sticky note in center` | `Cat sticking the note with both paws, tongue out in cute concentration` |

---

## 三、配图流程

### 写完稿子后推荐封面方案

**卡片式（日常帖子）：**

```
📋 封面建议：
- 卡片文字：「xxx」
- 背景色：xxx
- 场景：xxx
```

**场景版（重要帖子）：**

```
📋 封面建议（场景版）：
- 场景：xxx（从场景库选）
- 角色动作/表情：xxx
- 装饰：xxx
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

---

_小天爱黄金（bot12）专属封面生成能力，不与其他 bot 共享。_
