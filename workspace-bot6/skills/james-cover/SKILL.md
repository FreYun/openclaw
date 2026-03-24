---
name: james-cover
description: >
  老詹专属封面图生成 Skill — 角色形象设定、卡片风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为老詹账号生成一致风格封面图的能力。
---

# 老詹封面生成 Skill（james-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

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

## 二、STYLE 模板（直接复制）

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

## 三、配图流程

### 写完稿子后推荐封面方案

```
📋 封面建议：
- 卡片文字：「xxx」
- 背景色：xxx
- 场景：xxx
```

### 研究部确认后调用生图

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制第二节的 STYLE 模板}",
  content: "{背景色}. Chinese text on card reads: {卡片文字}. {从场景表情库选对应的表情+装饰}"
)'
```

---

_老詹（bot6）专属封面生成能力，不与其他 bot 共享。_
