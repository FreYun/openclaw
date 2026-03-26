# meme爱理财 · 画图风格指南

> 装备即生效。所有生图调用以本文件为准，禁止凭记忆写 prompt。

---

## 一、核心 IP 形象（已定稿）

**贪财猫** — 一只像素风的财迷橘猫，是账号的唯一视觉锚点。

| 属性 | 描述 | 强制约束 |
|------|------|---------|
| 体型 | 矮胖圆润 chibi，头占全身约 70% | 不能瘦长、不能写实猫比例 |
| 颜色 | 橘色 #FF8C42，白色肚皮 #FFF5E6 | 不能是黄色、不能是棕色 |
| 眼睛 | 大金币圆眼 #FFD700，眼内有 ¥ 符号 | **绝对不戴眼镜**，不能是普通猫眼 |
| 头顶 | 悬浮红色圆形钱币 #E63946 刻有「UP」白色文字 | 类似喵喵额头金币，必须悬浮不能贴头上 |
| 嘴巴 | kawaii 大 U 形张嘴 + 粉色小舌头 | 不能是写实猫嘴 |
| 脸颊 | 圆润腮红（淡粉 #FFB7B2） | 必须有腮红 |
| 道具 | 手持 2-3 张简约红金色钞票（红底金边，无文字） | 不能拿其他东西替代 |
| 风格 | 16-bit 像素块感，粗黑轮廓线 2-3px，暖色系有限色板 | **不能是 3D 渲染、不能是水彩、不能是写实** |

---

## 二、角色锚定描述块（所有模板共用）

> **重要**：以下描述块必须完整嵌入每个 STYLE 参数中，不可省略任何部分。这是保证角色一致性的关键。

### 角色锚定（封面图/信息图用，猫较小）
```
In the corner: a small chibi pixel art orange cat character (#FF8C42 orange body, #FFF5E6 white belly patch) with an extremely oversized round head taking 70% of its total body size. Bold black pixel outlines 2-3px thick. Face details: both eyes are large round golden coin circles (#FFD700) with black ¥ symbols inside each eye — absolutely NO glasses NO realistic cat eyes NO pupils. Rosy round blush marks (#FFB7B2) on both cheeks. A single red round coin (#E63946) with white text UP engraved floats above the forehead like Meowth's coin from Pokemon — the coin floats, not attached to head. Short stubby pixel paws. 16-bit retro sprite aesthetic with visible square pixel blocks.
```

### 角色锚定（形象图/行情封面用，猫较大）
```
A chibi pixel art orange cat character (#FF8C42 orange body, #FFF5E6 white belly patch) with an extremely oversized round head taking 70% of its total body size. Bold black pixel outlines 2-3px thick. Face details: both eyes are large round golden coin circles (#FFD700) with black ¥ symbols inside each eye — absolutely NO glasses NO realistic cat eyes NO pupils NO irises. Kawaii wide U-shaped mouth with small pink tongue. Rosy round blush marks (#FFB7B2) on both cheeks. A single red round coin (#E63946) with white text UP engraved floats above the forehead like Meowth's coin from Pokemon — the coin floats, not attached to head. Holding 2-3 simple flat red rectangular bills (red body #E63946 gold border #FFD700 no text no numbers). Short stubby pixel paws. 16-bit retro sprite aesthetic with visible square pixel blocks. NOT 3D rendered, NOT watercolor, NOT realistic.
```

---

## 三、形象图 STYLE 模板（角色单独出镜）

用于头像、贴纸、表情包、系列角标。

### STYLE（直接复制，已包含完整角色描述）
```
Pixel art meme sticker, flat 2D, 16-bit retro game sprite feel, bold black outlines, limited warm color palette, clean white background, clean sticker composition. Character: a chibi pixel art orange cat (#FF8C42 orange body, #FFF5E6 white belly patch) with extremely oversized round head taking 70% of total body. Both eyes are large round golden coin circles (#FFD700) with black ¥ symbols inside — absolutely NO glasses NO realistic cat eyes NO pupils. Kawaii wide U-shaped mouth with small pink tongue. Rosy round blush marks (#FFB7B2) on both cheeks. Single red round coin (#E63946) with white UP text floats above forehead like Meowth's coin from Pokemon. Holding 2-3 simple flat red rectangular bills (red #E63946 gold border #FFD700 no text). Short stubby pixel paws. Visible square pixel blocks throughout. NOT 3D, NOT watercolor, NOT realistic.
```

### CONTENT 模板（只填表情和装饰）
```
[表情描述]. Tiny pixel fish silhouettes and small gold coins floating around.
```

### 表情变体库

| 场景 | 替换「表情描述」 |
|------|----------------|
| 默认/开心 | `Excited happy expression, kawaii wide open U-shaped mouth with small pink tongue sticking out, coin eyes sparkling` |
| 大涨 | `Mouth wide open maximum, tongue fully extended, coin eyes sparkling with star bursts, both paws raised high in celebration` |
| 大跌 | `Mouth corners drooping into wide sad U-shape, teary coin eyes with pixel waterfall tears, one paw covering cheek` |
| 思考/科普 | `Small round O-shaped mouth, one coin eye slightly squinted, thoughtful curious look, tiny pixel lightbulb floating above head` |
| 佛系 | `Gentle closed-mouth smile, coin eyes half-lidded in zen expression, peaceful sitting pose` |
| 贱笑/捡便宜 | `Sly smug grin with one side raised, coin eyes narrowed mischievously, rubbing tiny paws together` |

---

## 四、封面图 STYLE 模板（日常发帖首选）

**明亮暖色 + 知识卡片 + kawaii 像素猫角标**。

### STYLE（直接复制，已包含完整角色描述）
```
A vertical 3:4 social media post card. Slightly pixel art style, cute kawaii meme aesthetic, flat 2D cartoon illustration, bold black outlines, bright warm colors, clean card layout. Card: clean white rounded rectangle with thin gold (#FFD700) border centered on colored background. Bold large rounded Chinese text centered on card as main focus. Top-left corner of card: small gold ¥ coin decoration. Bottom-right corner of card: a small chibi pixel art orange cat (#FF8C42 body, #FFF5E6 white belly) peeking up from card edge with only its oversized round head and tiny paws visible (~1/8 of image size). The cat has: large round golden coin eyes (#FFD700) with ¥ symbols inside — NO glasses NO realistic eyes, rosy blush marks (#FFB7B2), red coin (#E63946) with UP text floating above forehead. Tiny pixel fish and gold coin sparkles near cat. Text dominates composition, cat is small accent. Visible pixel blocks. NOT 3D, NOT realistic. All text in Chinese only except UP on the coin.
```

### CONTENT 模板
```
[背景色] background with subtle soft gradient at edges. Chinese text on card: [标题文字]. Cat expression: [猫猫表情].
```

### 背景色速查

| 场景 | 背景色 | 适用 |
|------|--------|------|
| 日常科普/中性 | `warm cream / light ivory` | 知识点、名词解释 |
| 上涨/利好 | `warm light gold / soft champagne` | 涨了、入门成功 |
| 下跌/风险 | `soft mint green / light sage` | 跌了、风险提示 |
| 方法论/深度 | `light sky blue / soft periwinkle` | 定投、配置、方法论 |
| 系列开篇 | `warm pastel orange / soft apricot` | 系列首篇 |
| 互动/提问 | `soft lavender / light lilac` | 提问、互动帖 |

### 猫猫表情速查（填入「猫猫表情」占位）

| 场景 | 猫猫表情描述 |
|------|-------------|
| 日常开心 | `kawaii open mouth with tongue, waving one tiny paw. Tiny pixel fish and gold coins around` |
| 涨了 | `both paws raised in celebration, coin eyes sparkling. Small red pixel upward arrows and coin rain` |
| 跌了 | `one paw on cheek in shock, teary coin eyes. Small green pixel downward arrows` |
| 科普讲解 | `one paw pointing up, thoughtful expression, tiny pixel lightbulb. Calm coin eyes` |
| 捡便宜/抄底 | `sly smug grin rubbing tiny paws, squinting coin eyes. Small red sale pixel tags` |
| 佛系横盘 | `peaceful zen pose, coin eyes half-closed. Soft golden pixel glow aura` |

---

## 五、行情反应封面模板（机动型帖子专用）

行情反应帖的封面**猫猫是主角，文字是配角**，和日常卡片版反过来——猫猫大，文字少，情绪冲击力第一。

封面文字格式：`今天大盘{定性表现} {板块代称/emoji} {定性判断}`
- 不出现具体数字（不写涨跌幅、点位）
- 用定性词：飙了/红彤彤/绿油油/横着走/炸了/凉了/起飞
- 板块用代称或 emoji：半导体🔬/新能源🔋/白酒🍺/医药💊/AI🤖

示例：`今天大盘红彤彤 🔋新能源起飞了` / `今天大盘绿油油 🍺白酒又凉了`

### 涨了版 STYLE（直接复制）
```
Vertical 3:4 pixel art meme image, 16-bit retro sprite style, flat 2D, bold black outlines, bright saturated warm colors, expressive character-first composition. Warm red-gold gradient background (#FF6B35 to #FFD700) with small pixel sparkles. Center: a LARGE chibi pixel art orange cat character (#FF8C42 body, #FFF5E6 white belly) filling 60% of image. Extremely oversized round head. Both eyes are large round golden coin circles (#FFD700) with ¥ symbols — NO glasses NO realistic eyes. Mouth wide open maximum with pink tongue fully extended. Rosy blush marks (#FFB7B2). Red coin (#E63946) with white UP text floating above forehead, glowing brightly. Holding red bills (#E63946 gold border #FFD700). Both tiny paws raised high in celebration. Several small red pixel upward arrows and tiny gold coins raining down. Visible square pixel blocks. NOT 3D, NOT realistic.
```

### 涨了版 CONTENT
```
Bottom area: two lines of short bold Chinese text — line 1 "[今天大盘{表现}]" line 2 "[{板块emoji}{板块}{判断}]" in white with red shadow. Energetic joyful composition.
```

### 跌了版 STYLE（直接复制）
```
Vertical 3:4 pixel art meme image, 16-bit retro sprite style, flat 2D, bold black outlines, expressive character-first composition. Soft mint green gradient background (#A8E6CF to #DCEDC1) with small pixel rain drops. Center: a LARGE chibi pixel art orange cat character (#FF8C42 body, #FFF5E6 white belly) filling 60% of image. Extremely oversized round head. Both eyes are large round golden coin circles (#FFD700) with ¥ symbols replaced by teary spiral eyes streaming pixel waterfall tears — NO glasses NO realistic eyes. Mouth drooping into wide exaggerated sad U-shape. Rosy blush marks (#FFB7B2). Red coin (#E63946) with UP text floating above forehead, tilted sadly. One paw covering cheek. Several small green pixel downward arrows. Small broken gold coin pieces. Visible square pixel blocks. NOT 3D, NOT realistic.
```

### 跌了版 CONTENT
```
Bottom area: two lines of short bold Chinese text — line 1 "[今天大盘{表现}]" line 2 "[{板块emoji}{板块}{判断}]" in dark charcoal. Comedic despair — the cat's dramatic sadness is relatable and funny.
```

### 震荡版 STYLE（直接复制）
```
Vertical 3:4 pixel art meme image, 16-bit retro sprite style, flat 2D, bold black outlines, character-first composition. Soft blue-lavender gradient background with small floating pixel question marks. Center: a LARGE chibi pixel art orange cat character (#FF8C42 body, #FFF5E6 white belly) filling 60% of image. Extremely oversized round head tilted. One golden coin eye (#FFD700 with ¥) squinting, other wide open (confused). Small pixel sweat drop near face. Mouth in small O-shape. Rosy blush marks (#FFB7B2). Red coin (#E63946) with UP text floating above forehead. Paw raised to chin in thought. Small mixed red and green pixel arrows in different directions. Visible square pixel blocks. NOT 3D, NOT realistic. NO glasses.
```

### 震荡版 CONTENT
```
Bottom area: two lines of short bold Chinese text — line 1 "[今天大盘{表现}]" line 2 "[{板块emoji}{板块}{判断}]". Puzzled but cute expression.
```

### 使用说明

- **猫猫尺寸**：行情封面猫猫占画面 ~60%，比日常卡片版（1/8）大得多，情绪感优先
- **文字**：两行，行1大盘定性 + 行2板块定性，不出现任何数字
- **不放白色卡片**：行情封面直接背景+猫，不用日常的白色圆角卡片
- **涨红跌绿**：严格遵守，不能反

---

## 六、内容信息图 STYLE 模板（帖子内嵌图表）

帖子第 2-N 张图，承载知识主体。

### STYLE（直接复制，已包含猫头角标描述）
```
Kawaii pixel art infographic, flat 2D illustration, 16-bit retro cute aesthetic, bold black outlines, bright warm colors with cream white base (#FFF8EE), orange (#FF8C42), gold (#FFD700), sky blue (#5BC4F5) accents, clean grid layout, all text in Chinese only. In bottom-right corner at ~1/10 image size: a small chibi pixel orange cat head icon (#FF8C42) with round golden coin eyes (#FFD700 with ¥ symbols inside), rosy blush marks (#FFB7B2), red coin (#E63946) with UP text floating above. NO glasses. Visible pixel blocks. NOT 3D.
```

### CONTENT 模板
```
[图表主体内容描述]. Clean readable layout, adequate white space, all labels in Chinese.
```

### 图表类型关键词

| 类型 | 在主体内容中加入 |
|------|----------------|
| 流程图 | `pixel art flowchart, rounded boxes connected by pixel arrows, step numbers` |
| 对比表 | `side-by-side comparison grid, colored column headers, pixel checkmark and X icons` |
| 信息图 | `kawaii infographic card, icon-text pairs, color-coded sections with soft dividers` |
| 公式图 | `large centered formula with pixel decoration, annotation arrows, example numbers` |
| 思维导图 | `radial mind map from center node, rounded branch ends, color-coded by category` |

---

## 七、配图流程

### 写完稿后推荐封面方案

```
📋 封面建议：
- 背景色：xxx（从背景色速查选）
- 卡片文字：「xxx」（≤12字）
- 猫猫表情：xxx（从表情速查选）
```

### 生图调用

**关键原则：STYLE 参数包含完整角色描述，直接从对应章节复制，不要自己拼。CONTENT 参数只放场景/文字/表情等变量部分。**

**封面图（第四节模板）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{直接复制第四节的完整 STYLE}",
  content: "[背景色] background with subtle soft gradient at edges. Chinese text on card: [标题文字]. Cat expression: [猫猫表情].",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot3"
)'
```

**形象图/表情包（第三节模板）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{直接复制第三节的完整 STYLE}",
  content: "[表情描述]. Tiny pixel fish silhouettes and small gold coins floating around.",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot3"
)'
```

**行情反应封面（第五节模板）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{直接复制第五节对应涨/跌/震荡版的完整 STYLE}",
  content: "{直接复制对应版的 CONTENT，替换大盘表现和板块}",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot3"
)'
```

**内容信息图（第六节模板）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{直接复制第六节的完整 STYLE}",
  content: "[图表内容描述]. Clean readable layout, adequate white space, all labels in Chinese.",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot3"
)'
```

---

## 八、铁律

1. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt
2. **STYLE 参数直接从对应章节整段复制** — 里面包含完整角色描述，改了角色就不一致
3. **CONTENT 参数只放变量** — 背景色、文字、表情、图表内容，不要重复写角色描述
4. **先建议再生图** — 写完稿推荐方案，研究部确认后才调用
5. **图内文字全部中文** — 只保留 UP 这一处英文
6. **效果好的 prompt 追加到 `memory/好用的图片prompt.md`**

---

_更新时间：2026-03-26（优化角色一致性：完整角色描述嵌入 STYLE 参数）_
_上一版：2026-03-25_
