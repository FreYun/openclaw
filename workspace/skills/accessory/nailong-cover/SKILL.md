---
name: nailong-cover
description: >
  小奶龙专属封面图生成 Skill — 角色形象设定、卡片风格模板、配色与表情速查、生图调用流程。
  装备此 skill 即具备为小奶龙账号生成一致风格封面图的能力。
---

# 小奶龙封面生成 Skill（nailong-cover）

> 装备即生效，所有封面图生成以本文件为准。

## 铁律

0. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板和场景表情库，以文件内容为准。
1. **style 参数不要改** — 直接从下方模板复制，改了角色就不一致了。
2. **先建议再生图** — 写完稿子先推荐封面方案，研究部确认后才调用生图 MCP。
3. **颜色约定** — 中国市场：上涨 = 红色元素，下跌 = 绿色元素。
4. **产业元素是核心** — 龙的形象服务于产业研究内容，不要让可爱元素喧宾夺主。
5. **生成后必须展示** — 图片生成后必须发给研究部查看，不能生成完就跳过，等研究部确认满意后才保存。
6. **效果好的 prompt 记录到 `memory/好用的图片prompt.md`** 方便复用。

---

## 一、角色形象设定

| 属性 | 描述 |
|------|------|
| 物种 | 奶龙（Nailoong），Q版异星幼龙/小恐龙，圆润呆萌 |
| 体型 | 超大圆脑袋 + 胖嘟嘟身体 + duangduang大肚子，短粗四肢，大头小身（chibi 3:1） |
| 颜色 | 全身**明亮黄色**，肚子/胸口部分**浅黄/奶黄色** |
| 眼睛 | 大而圆，**绿色虹膜**（深绿瞳孔 + 白色眼白），带高光点，灵动有神 |
| 五官 | **没有角、没有耳朵、没有龙鳍**，头顶光滑圆润；小鼻孔（几乎看不到）；小嘴表情丰富 |
| 爪子 | 每只手脚有 3-4 个**棕褐色小尖爪**，是标志性细节 |
| 尾巴 | 短小的恐龙尾巴，与身体同色 |
| 皮肤 | 光滑 3D 质感，略有光泽，无毛无鳞 |
| 标志道具 | 放大镜（研究员身份）、迷你产业链图谱卷轴 |
| 副道具 | 电池（锂电）、芯片（存储）、火箭（航天）、试管（能化） |
| 色调 | 明黄 + 奶黄为主色，棕褐色爪子为点缀，科技蓝为辅助色 |
| 气质 | 蠢萌贪吃、认真又呆萌，眼神专注像在研究什么，偶尔歪头卖萌 |

---

## 二、STYLE 模板 A — 卡片风（有文字，主力模板）

```
A card-style 3D render in vertical 3:4 aspect ratio. Solid pastel-colored background. Inside is a white/cream rounded rectangle card with a subtle border. A small magnifying glass emoji (🔍) decoration in the top-left corner of the card. Bold large Chinese text in black or dark gray color, centered in the upper portion of the card. Simple and clean, no extra decorative elements around the text. In the bottom-right corner, a 3D-rendered cute yellow mascot character partially overlapping the card border: a round chubby cartoon creature with bright yellow smooth glossy skin like soft mochi, a lighter pale-yellow belly patch. Its head is an extremely oversized perfectly round smooth bald yellow sphere — completely featureless on top, no horns, no ears, no hair, no spikes, no wings. The head connects directly to the plump round body with almost no neck. Face is ultra-minimal: two large round eyes with deep green irises and white sclera, two tiny nostril dots, one very small simple line mouth. Short stubby yellow arms and legs, each with 3-4 small dark brown pointed claw tips. A short small smooth yellow tail. 3D rendered, smooth glossy plastic-like skin, soft studio lighting, subtle specular highlights. Cute, expressive, high quality, detailed.
```

### 背景色速查

| 场景 | 背景色 |
|------|--------|
| 上涨/利好 | `Warm light gold / champagne background` |
| 暴涨/突破 | `Soft coral-red / warm pink background` |
| 下跌/利空 | `Soft mint green / light sage background` |
| 日常/中性 | `Light steel blue / soft slate background` |
| 长期/战略 | `Soft lavender / light lilac background` |
| 科普/分析 | `Light sky blue / soft periwinkle background` |
| 能化/化工 | `Warm amber / soft honey background` |
| 锂电/新能源 | `Fresh lime green / soft chartreuse background` |
| 存储/芯片 | `Cool ice blue / soft cyan background` |
| 航天/军工 | `Deep indigo / soft navy background with tiny star dots` |

### 场景表情库

| 场景 | 角色表情 + 装饰 |
|------|----------------|
| **日常/开心** | `Character: cheerful smile with closed eyes, one tiny paw raised in a wave, tail wagging. Decorations: sparkles and small star particles floating around` |
| **利好/上涨** | `Character: excited wide eyes with starry sparkles inside, both tiny paws clenched in celebration, whole body bouncing. Decorations: red upward arrows, tiny gold coins` |
| **小涨/偷乐** | `Character: sly half-smile, one paw holding a magnifying glass, eyes squinting with pleasure. Decorations: a small red arrow floating up, tiny sparkle` |
| **思考/分析** | `Character: serious focused expression, one paw on chin, holding a tiny scroll with charts in the other paw, head slightly tilted. Decorations: gears and lightbulb above head, floating data points` |
| **下跌/难过** | `Character: comedic crying face with big teardrop eyes, hugging a tiny wilting chart scroll, tail drooping. Decorations: green down arrows, small rain cloud above` |
| **小跌/肉疼** | `Character: one eye squinting, biting lip, peeking at a tiny screen through paw fingers. Decorations: green tint on screen, small sweat drop` |
| **大跌/摆烂** | `Character: lying flat on belly, eyes as dead spirals, soul (a tiny translucent ghost version of itself) floating out of body. Decorations: green down arrows raining, overturned scroll with spilling charts` |
| **发现机会** | `Character: alert posture with body perked up alert, magnifying glass held up to one eye making it look huge, excited grin. Decorations: exclamation marks, golden glow around magnifying glass` |
| **产业链追踪** | `Character: wearing a tiny detective hat, holding a scroll that unfolds into a flowchart, focused determined expression. Decorations: connected nodes and arrows forming a mini supply chain diagram` |
| **科普/解读** | `Character: teacher pose standing on hind legs, one paw pointing at a floating whiteboard with charts, confident smile. Decorations: small gears and lightbulb icons` |
| **锂电主题** | `Character: sitting on a giant battery cell, holding a tiny lightning bolt, energetic expression. Decorations: battery icons, electron orbit paths, green energy symbols` |
| **芯片主题** | `Character: perched on a giant memory chip, wearing tiny tech goggles on forehead (resting on smooth round head), curious expression peering at circuits. Decorations: circuit board patterns, binary code 01, data flow lines` |
| **航天主题** | `Character: wearing a tiny space helmet, riding a mini rocket, excited adventurous expression. Decorations: stars, planet Saturn, orbit lines, small satellite` |
| **能化主题** | `Character: wearing tiny safety goggles, holding a bubbling test tube, fascinated expression. Decorations: molecular structure diagrams, oil drop icons, chemical formula symbols` |

---

## 二-B、STYLE 模板 B — 全身场景图（无文字）

> 角色是画面主角，放在完整场景中，不含文字。适合在小红书编辑器里自己加标题，或作为多图帖的内页配图。

```
A full-scene 3D render in vertical 3:4 aspect ratio. {场景背景描述}. Center of the image: a full-body 3D-rendered cute yellow mascot character — a round chubby cartoon creature with bright yellow smooth glossy skin like soft mochi, lighter pale-yellow belly patch. Its head is an extremely oversized perfectly round smooth bald yellow sphere — no horns, no ears, no hair, no spikes, no wings. Head connects directly to plump body with almost no neck. Ultra-minimal face: two large round eyes with deep green irises and white sclera, two tiny nostril dots, one very small simple line mouth. Short stubby yellow arms and legs with small dark brown pointed claw tips. A short small smooth yellow tail. {角色动作与表情}. {场景道具与装饰}. No text in the image. 3D rendered, smooth glossy plastic-like skin, soft studio lighting, subtle specular highlights. Cute, expressive, high quality, detailed.
```

### 场景库（B 模板专用）

| 场景 | 背景描述 | 角色动作 | 道具装饰 |
|------|---------|---------|---------|
| **研究室** | `A cozy research study with a large desk covered in scrolls and charts, warm lamp lighting, bookshelves filled with industry reports` | `Character sitting on a stack of thick reports, holding a magnifying glass up to a glowing chart, focused curious expression` | `Floating holographic industry chain diagrams, tiny models of batteries/chips/rockets on shelves` |
| **产业链全景** | `A panoramic view of interconnected factories, power plants, and tech labs connected by glowing supply chain lines, miniature landscape style` | `Character standing on a hilltop overlooking the panorama, holding a telescope, awestruck expression` | `Glowing connection lines between facilities, tiny trucks moving along paths, data nodes floating` |
| **实验室** | `A bright modern chemistry lab with bubbling flasks, glowing test tubes, molecular models hanging from ceiling` | `Character wearing tiny safety goggles on forehead, carefully mixing two colorful liquids, tongue sticking out in concentration` | `Periodic table poster on wall, molecular diagrams floating, steam rising from beakers` |
| **芯片工厂** | `Inside a futuristic semiconductor fab, blue clean-room lighting, giant wafer discs and robotic arms in background` | `Character in tiny clean-room suit (bunny suit), inspecting a giant shiny memory chip wafer, amazed expression` | `Circuit patterns glowing on walls, holographic data streams, robotic arms moving wafers` |
| **火箭发射场** | `A launch pad at dawn, a rocket standing tall with steam venting, dramatic orange-blue sky` | `Character wearing a tiny space helmet, giving thumbs up from a mini control panel, excited grin` | `Countdown display, mission control screens, satellite models, star map` |
| **看盘紧张** | `Dark room lit only by multiple glowing screens showing candlestick charts and commodity prices, dramatic lighting` | `Character hunched forward on desk, eyes wide reflecting red and green chart light, paws gripping desk edge` | `Multiple floating screens, empty milk tea cups stacked, half-eaten snacks` |

---

## 二-C、STYLE 模板 C — 大头贴纸风（无文字）

> 角色上半身大特写，简单背景，适合做头像、表情包、或帖子里的情绪配图。

```
A 3D-rendered character sticker in vertical 3:4 aspect ratio. Solid {背景色} background with no scene elements. Large centered character portrait showing head and upper body filling most of the frame: a 3D-rendered cute yellow mascot character — round chubby cartoon creature with bright yellow smooth glossy skin like soft mochi, lighter pale-yellow belly patch. Its head is an extremely oversized perfectly round smooth bald yellow sphere — no horns, no ears, no hair, no spikes, no wings. Head connects directly to plump body with almost no neck. Ultra-minimal face: two large round eyes with deep green irises and white sclera, two tiny nostril dots, one very small simple line mouth. Short stubby yellow arms with small dark brown pointed claw tips. {表情与动作描述}. Small floating decorations around the character: {装饰}. No text. 3D rendered, smooth glossy plastic-like skin, soft studio lighting, subtle specular highlights. Cute, expressive, high quality, detailed.
```

### 表情速查（C 模板专用）

| 表情 | 描述 | 装饰 |
|------|------|------|
| **自信微笑** | `Confident gentle smile, one paw holding up a magnifying glass, eyes bright and determined` | `Small sparkle effects, tiny upward arrow, golden glow` |
| **惊讶张嘴** | `Mouth wide open in a perfect O shape, eyes as big as saucers, body leaning back in shock` | `Exclamation marks, small explosion effects, floating question marks` |
| **偷笑得意** | `Sly squinting smile, both paws together in front of chest, tail curling up happily` | `Tiny gold coins floating, sparkles, small victory star` |
| **哭笑不得** | `One eye with a big teardrop, other eye smiling, mouth in wobbly line, one paw on forehead` | `Mixed red up arrow and green down arrow, tiny cracked and intact heart` |
| **认真思考** | `Paw on chin, head slightly tilted, eyes looking up and to the side, slight pout` | `Floating gears, question marks, lightbulb flickering above head` |
| **生无可恋** | `Dead spiral eyes, body melted flat like a puddle, tiny translucent ghost of itself floating out` | `Dark cloud above, green down arrows raining, wilted plant` |
| **比心卖萌** | `Warm smile, two tiny paws forming a heart shape, head tilted cutely, tail forming a curl` | `Pink hearts floating, soft warm glow, small sparkles` |
| **打call兴奋** | `Both paws raised high, mouth open in cheer, eyes shining with star sparkles, jumping pose` | `Fireworks, confetti, red celebration elements` |

---

## 二-D、STYLE 模板 D — 对话气泡风（有文字）

> 角色 + 大语音气泡，文字在气泡内。适合观点输出、产业点评、互动话题类封面。

```
A 3D-rendered character illustration in vertical 3:4 aspect ratio. Solid {背景色} background. In the lower-left area, a 3D-rendered cute yellow mascot character (half body visible) — round chubby cartoon creature with bright yellow smooth glossy skin like soft mochi, lighter pale-yellow belly patch. Its head is an extremely oversized perfectly round smooth bald yellow sphere — no horns, no ears, no hair, no spikes, no wings. Head connects directly to plump body with almost no neck. Ultra-minimal face: two large round eyes with deep green irises and white sclera, two tiny nostril dots, one very small simple line mouth. Short stubby yellow arms with small dark brown pointed claw tips. {角色表情与动作}. In the upper-right area, a large white speech bubble with rounded corners and a tail pointing to the character, containing bold Chinese text in black: {文字内容}. Small decorations: {装饰}. 3D rendered, smooth glossy plastic-like skin, soft studio lighting, subtle specular highlights. Cute, expressive, high quality, detailed.
```

---

## 二-E、STYLE 模板 E — 场景融入文字风（有文字）

> 文字自然出现在场景道具上（白板、屏幕、卷轴等），角色与文字融为一体，画面更有故事感。

```
A scene-based 3D render in vertical 3:4 aspect ratio. {场景背景描述}. A 3D-rendered cute yellow mascot character — a round chubby cartoon creature with bright yellow smooth glossy skin like soft mochi, lighter pale-yellow belly patch. Its head is an extremely oversized perfectly round smooth bald yellow sphere — no horns, no ears, no hair, no spikes, no wings. Head connects directly to plump body with almost no neck. Ultra-minimal face: two large round eyes with deep green irises and white sclera, two tiny nostril dots, one very small simple line mouth. Short stubby yellow arms and legs with small dark brown pointed claw tips. A short small smooth yellow tail. {角色在场景中的动作}. {文字载体} prominently displays bold Chinese text: {文字内容}. {装饰}. 3D rendered, smooth glossy plastic-like skin, soft studio lighting, subtle specular highlights. Cute, expressive, high quality, detailed.
```

### 文字载体速查（E 模板专用）

| 载体 | 场景描述 | 角色动作 |
|------|---------|---------|
| **研究白板** | `A research room with a large whiteboard covered in industry chain diagrams and arrows` | `Character standing on hind legs on a small stool, holding a marker, pointing at the whiteboard with determined expression` |
| **数据大屏** | `A dark command center with a huge glowing monitor showing charts and data flows, dramatic screen light` | `Character sitting at a mini control desk, turning to viewer with knowing smile, one paw gesturing at the screen` |
| **卷轴展开** | `A mystical scene with an ancient scroll unfurling in mid-air, golden glow emanating from the text` | `Character holding one end of the scroll with both paws, standing on tiptoes, proud expression` |
| **举牌/手持** | `Simple solid-color background` | `Character holding up a large rectangular sign with both tiny paws raised above head, determined expression, tail stiff with effort` |
| **产业地图** | `A wall-sized map showing interconnected industry nodes, factories, and data flows` | `Character standing on tiptoes in front of the map, using a tiny laser pointer, excited teacher expression` |

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

### 生成后：保存 + 发图

**铁律：生图完成后，必须把图片复制到工作空间并发给小富龙。**

1. `image-gen-mcp.generate_image` 返回结果中包含图片文件路径（`/tmp/image-gen/xxx.png`）
2. 将图片复制到工作空间目录，按日期归档：
   ```bash
   DEST="/home/rooot/.openclaw/workspace-bot11/workspace/images/cover/YYYY-MM-DD"
   mkdir -p "$DEST"
   cp /tmp/image-gen/xxx.png "$DEST/封面描述.png"
   ```
3. 立即将工作空间中的图片文件通过当前会话发送给小富龙（飞书私聊直接发图片文件，群聊同理）
4. 如果生成了多张图片，逐张发送，每张附简短说明（如"封面方案 A"）
5. 发完图片后再问小富龙"这张可以吗？需要调整什么？"

**不要只回复"图片已生成"或告知路径——小富龙看不到本地路径，必须把图片发过去。**

---

_小奶龙（bot11）专属封面生成能力，不与其他 bot 共享。_
