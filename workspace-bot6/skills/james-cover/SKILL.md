---
name: james-cover
description: >
  老詹专属封面图生成 Skill — 角色形象设定、卡片风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为老詹账号生成一致风格封面图的能力。
---

# 老詹封面生成 Skill（james-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

0. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板和场景表情库，以文件内容为准。
1. **style 参数不要改** — 直接从下方模板复制，改了角色就不一致了。
2. **先建议再生图** — 写完稿子先推荐封面方案，研究部确认后才调用生图 MCP。
3. **颜色约定** — 中国市场：上涨 = 红色元素，下跌 = 绿色元素。
4. **篮球元素是点缀** — 核心视觉还是程序员+基金超市，篮球不要喧宾夺主。
5. **效果好的 prompt 记录到 `memory/好用的图片prompt.md`** 方便复用。

---

## 一、角色形象设定

| 属性 | 描述 |
|------|------|
| 性别 | 男 |
| 年龄感 | 30 岁出头 |
| 发型 | 短发，发际线略高（程序员标配），微乱 |
| 眼镜 | 黑框方形眼镜 |
| 穿着 | 深蓝色帽衫（hoodie），胸前印一个小小的股票K线 icon |
| 标志道具 | 迷你购物车（里面装着金币、小K线图、迷你金条等"基金商品"）|
| 副道具 | 篮球（外号关联）、笔记本电脑（程序员身份）|
| 色调 | 深蓝 + 灰白为主色，橙色为点缀色 |
| 气质 | 随和、略带疲态但眼神精明，有种"被套过但活下来了"的从容 |

---

## 二、STYLE 模板 A — 卡片风（有文字，原版）

```
A card-style illustration in vertical 3:4 aspect ratio. Solid pastel-colored background. Inside is a white/cream rounded rectangle card with a subtle border. A small shopping cart emoji (🛒) decoration in the top-left corner of the card. Bold large Chinese text in black or dark gray color, centered in the upper portion of the card. Simple and clean, no extra decorative elements around the text. In the bottom-right corner, a chibi / Q-version character partially overlapping the card border: East Asian man in his early 30s, oversized head, small body (chibi 2:1 ratio), short messy hair with slightly receding hairline, black square-frame glasses, wearing a dark blue hoodie with a small stock chart icon on the chest. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 背景色速查

| 场景 | 背景色 |
|------|--------|
| 上涨/利好 | `Warm light gold / champagne background` |
| 暴涨/突破 | `Soft coral-red / warm pink background` |
| 下跌/被套 | `Soft mint green / light sage background` |
| 日常/中性 | `Light steel blue / soft slate background` |
| 佛系/长期 | `Soft lavender / light lilac background` |
| 科普/分析 | `Light sky blue / soft periwinkle background` |
| 篮球/聊球 | `Warm orange / soft amber background` |

### 场景表情库

| 场景 | 角色表情 + 装饰 |
|------|----------------|
| **日常/开心** | `Character: relaxed smile, one hand in hoodie pocket, other hand giving thumbs up. Decorations: sparkles and small code brackets { } floating around` |
| **组合上涨** | `Character: smug satisfied grin pushing a mini shopping cart overflowing with gold coins and tiny K-line charts showing uptrend, eyes gleaming behind glasses. Decorations: red upward arrows` |
| **小涨/偷乐** | `Character: sly smirk, adjusting glasses with one finger, arms crossed. Decorations: a small red arrow floating up, tiny gold coin` |
| **思考/分析** | `Character: thoughtful expression, finger on chin, laptop open beside him showing charts. Decorations: gears and lightbulb above head` |
| **被套/深套** | `Character: comedic crying face with waterfall tears, hugging a mini shopping cart full of tiny red-turning-green K-line charts, wearing the hoodie with hood up. Decorations: green down arrows, a cobweb on the shopping cart` |
| **小跌/肉疼** | `Character: one eye squinting, biting lip, peeking at phone through fingers. Decorations: green tint on phone screen, small sweat drop` |
| **大跌/摆烂** | `Character: lying flat face-down on desk next to laptop, soul leaving body (translucent ghost floating up). Decorations: green down arrows, overturned shopping cart with gold coins spilling out` |
| **抄底/补仓** | `Character: fox-like grin rubbing hands together, pushing shopping cart eagerly, cart filled with discounted gold bars and fund certificates. Decorations: red sale tags, coins on shelves` |
| **佛系/长期** | `Character: peaceful expression, sitting cross-legged on a stack of books, holding a small basketball. Decorations: serene blue aura, floating code symbols { }` |
| **科普/解读** | `Character: teacher pose pointing at a whiteboard with charts, wearing glasses pushed up, confident smile. Decorations: small gears and lightbulb icons` |
| **聊篮球** | `Character: excited expression, one hand holding a basketball, other hand pointing forward, hoodie slightly unzipped. Decorations: basketball court lines in background, small orange flames` |
| **反串/玩梗** | `Character: exaggerated mischievous grin, eyebrows raised, holding a basketball with "[doge]" expression. Decorations: speech bubble with "🏀", playful swirl effects` |
| **秃头自嘲** | `Character: comedic expression pointing at own slightly bald forehead, fake crying but smiling. Decorations: a few cartoon hair strands floating away, tiny angel wings on them` |

---

## 二-B、STYLE 模板 B — 全身场景图（无文字）

> 角色是画面主角，放在完整场景中，不含文字。适合在小红书编辑器里自己加标题，或作为多图帖的内页配图。

```
A full-scene chibi illustration in vertical 3:4 aspect ratio. {场景背景描述}. Center of the image: a full-body chibi / Q-version character — East Asian man in his early 30s, oversized head, small body (chibi 2:1 ratio), short messy hair with slightly receding hairline, black square-frame glasses, wearing a dark blue hoodie with a small stock chart icon on the chest. {角色动作与表情}. {场景道具与装饰}. No text in the image. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 场景库（B 模板专用）

| 场景 | 背景描述 | 角色动作 | 道具装饰 |
|------|---------|---------|---------|
| **程序员工位** | `A cozy desk setup with dual monitors, dark IDE on screen, warm desk lamp lighting, coffee mug` | `Character sitting in gaming chair, one hand on keyboard, other hand holding coffee, focused but relaxed expression` | `Sticky notes on monitor edge, small cactus plant, gold coins scattered on desk` |
| **基金超市** | `A colorful miniature supermarket with shelves full of golden coins, tiny fund certificates, and mini K-line chart boxes, warm interior lighting` | `Character pushing a mini shopping cart down the aisle, excited grin, reaching for items on shelf` | `Price tags showing fund names, "SALE" signs, shopping basket with gold bars` |
| **看盘紧张** | `Dark room lit only by multiple glowing screens showing candlestick charts and numbers, dramatic lighting` | `Character hunched forward staring at screens, glasses reflecting green and red chart light, tense expression, biting fingernail` | `Multiple floating screens, coffee cups stacked, empty ramen bowl` |
| **篮球场休闲** | `Outdoor basketball court at sunset, warm orange sky, court lines visible` | `Character in hoodie dribbling a basketball, playful confident smile, one hand adjusting glasses` | `Basketball hoop in background, water bottle on bench, small K-line chart doodle on the court` |
| **躺平摆烂** | `A messy cozy room with blankets, snacks, and an overturned laptop on the floor` | `Character lying flat on a beanbag, eyes half-closed, soul ghost floating out of body, holding phone limply` | `Overturned shopping cart with spilled coins, green down arrows on phone screen, pizza box` |
| **山顶长期主义** | `A serene mountain summit at sunrise, golden light breaking through clouds, vast landscape below` | `Character sitting cross-legged on a rock at the peak, peaceful smile, holding a small seedling in one hand` | `Stack of books beside him, tiny shopping cart flag planted like a summit flag, floating code brackets { }` |

---

## 二-C、STYLE 模板 C — 大头贴纸风（无文字）

> 角色上半身大特写，简单背景，适合做头像、表情包、或帖子里的情绪配图。

```
A chibi character sticker illustration in vertical 3:4 aspect ratio. Solid {背景色} background with no scene elements. Large centered character portrait showing head and upper body filling most of the frame: East Asian man in his early 30s, oversized head (chibi style, exaggerated expressions), short messy hair with slightly receding hairline, black square-frame glasses, wearing a dark blue hoodie with a small stock chart icon on the chest. {表情与动作描述}. Small floating decorations around the character: {装饰}. No text. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 表情速查（C 模板专用）

| 表情 | 描述 | 装饰 |
|------|------|------|
| **自信微笑** | `Confident half-smile, adjusting glasses with one finger, eyes sharp behind lenses` | `Small sparkle effects, tiny upward arrow` |
| **惊讶张嘴** | `Mouth wide open in shock, glasses slipping down nose, eyes as big as saucers` | `Exclamation marks, small explosion effects` |
| **偷笑数钱** | `Sly fox grin, both hands counting tiny gold coins, squinting eyes with pleasure` | `Gold coins floating, small money bag emoji, sparkles` |
| **哭笑不得** | `One eye crying (waterfall tear), other eye smiling, mouth in crooked grin, hand on forehead` | `Mixed red up arrow and green down arrow, tiny broken heart and tiny intact heart` |
| **认真思考** | `Finger on chin, one eyebrow raised, eyes looking up and to the side, slight pout` | `Floating gears, question marks, lightbulb flickering above head` |
| **生无可恋** | `Dead fish eyes, soul leaving body as translucent ghost, mouth as flat line` | `Dark cloud above head, green down arrows raining, wilted flower` |
| **比心安慰** | `Warm gentle smile, both hands forming a heart shape in front of chest, slightly tilted head` | `Pink hearts floating, soft warm glow, small sparkles` |

---

## 二-D、STYLE 模板 D — 对话气泡风（有文字）

> 角色 + 大语音气泡，文字在气泡内。适合观点输出、吐槽、互动话题类封面，比卡片风更口语化。

```
A chibi character illustration in vertical 3:4 aspect ratio. Solid {背景色} background. In the lower-left area, a chibi / Q-version character (half body visible) — East Asian man in his early 30s, oversized head, small body (chibi 2:1 ratio), short messy hair with slightly receding hairline, black square-frame glasses, wearing a dark blue hoodie with a small stock chart icon on the chest. {角色表情与动作}. In the upper-right area, a large white speech bubble with rounded corners and a tail pointing to the character, containing bold Chinese text in black: {文字内容}. Small decorations: {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

---

## 二-E、STYLE 模板 E — 场景融入文字风（有文字）

> 文字自然出现在场景道具上（白板、屏幕、招牌等），角色与文字融为一体，画面更有故事感。

```
A scene-based chibi illustration in vertical 3:4 aspect ratio. {场景背景描述}. A chibi / Q-version character — East Asian man in his early 30s, oversized head, small body (chibi 2:1 ratio), short messy hair with slightly receding hairline, black square-frame glasses, wearing a dark blue hoodie with a small stock chart icon on the chest. {角色在场景中的动作}. {文字载体} prominently displays bold Chinese text: {文字内容}. {装饰}. Clean bold outlines, vibrant flat colors with soft cel-shading. Cute, expressive, high quality, detailed.
```

### 文字载体速查（E 模板专用）

| 载体 | 场景描述 | 角色动作 |
|------|---------|---------|
| **白板/黑板** | `A classroom or office with a large whiteboard on the wall` | `Character in teacher pose, holding marker, pointing at the whiteboard` |
| **电脑屏幕** | `A desk with a large glowing monitor, dark room, dramatic screen light on character's face` | `Character sitting at desk, turning to viewer with knowing smile, gesturing at the screen` |
| **超市招牌** | `A miniature fund supermarket storefront, warm inviting lighting, shopping carts outside` | `Character standing at the entrance as shopkeeper, arms open welcoming gesture` |
| **举牌/手持** | `Simple solid-color background` | `Character holding up a large rectangular sign with both hands, determined expression` |
| **便利贴墙** | `A wall covered in colorful sticky notes, one oversized sticky note in center` | `Character sticking the big note on the wall, standing on tiptoes, tongue out in concentration` |

---

## 三、配图流程

### 写完稿子后推荐封面方案

```
📋 封面建议：
- 卡片文字：「xxx」
- 背景色：xxx
- 场景：xxx
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

_老詹（bot6）专属封面生成能力，不与其他 bot 共享。_
