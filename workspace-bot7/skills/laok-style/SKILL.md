---
name: laok-style
description: "老K投资笔记"专属画图风格定义。为 bot7/bot8 生成配图时提供统一的视觉风格 prompt 模板。使用场景：(1) 生成老K IP扑克牌配图, (2) 生成投资/财经主题像素插画, (3) 任何需要老K品牌视觉一致性的图片生成任务。调用 image-generator 时引用此 skill 获取风格 prompt。
---

# 老K投资笔记 · 画图风格指南

## 核心 IP 形象

**老K** — 一张像素风的黑桃K扑克牌，是品牌的唯一视觉锚点。不画人物，只画牌。

### 扑克牌设定

- **牌面**：黑桃K (King of Spades) 标准扑克牌比例（约 2.5:3.5）
- **风格**：8-bit / 16-bit 像素艺术 (pixel art)，清晰可辨的像素网格感
- **牌面国王**：像素风格绘制的国王侧脸，深藏青色服装，金色王冠，手持权杖（可替换为 K 线图/数据棒）
- **花色标记**：黑桃 ♠ 用冰蓝色发光像素渲染，带微弱光晕
- **牌背**：深藏青底色 + 金色像素几何纹样

### 标志元素

| 元素 | 说明 |
|------|------|
| **黑桃K扑克牌** | 像素风，整体视觉主角，牌面内容可根据主题变化 |
| **像素光粒子** | 牌周围散落的冰蓝色像素方块粒子，表达数据/科技感 |
| **像素化数据** | K线、柱状图、趋势箭头等金融元素均用像素风格绘制 |

## 配色方案

```
主色:
  藏青    #1a2744  (牌面/背景主色)
  冰蓝    #00d4ff  (像素光效/数据高光)
  金色    #c8a84e  (王冠/纹饰/点缀)

辅助色:
  深黑    #0d1117  (背景/暗部)
  纯白    #ffffff  (牌面边框/高光/文字)
  像素红  #ff4444  (涨/阳线)
  像素绿  #44bb44  (跌/阴线)
```

## Prompt 模板

### 模板 A：老K 扑克牌 IP（通用）

```
A single King of Spades playing card rendered in detailed 16-bit pixel art style. The card stands upright, slightly tilted. The pixel king wears a dark navy (#1a2744) royal garment with a gold (#c8a84e) crown, holding a scepter. The spade symbol glows in ice blue (#00d4ff) with a subtle pixel glow effect. Scattered around the card are tiny ice-blue pixel particles floating like data fragments. Dark gradient background (#0d1117 to #1a2744). Crisp pixel art, visible pixel grid, retro game aesthetic meets fintech.
```

### 模板 B：老K 扑克牌 + 投资主题

```
A King of Spades playing card in 16-bit pixel art style, standing upright against a dark navy background. The card face shows a pixel king in navy robes with gold crown. Surrounding the card: [场景描述: pixel art candlestick charts / pixel stock tickers / 8-bit style financial dashboard with rising bars]. The spade symbol glows ice blue (#00d4ff). Pixel particles and data blocks float around. Retro pixel art aesthetic, visible pixel grid, dark moody palette of navy (#1a2744), ice blue (#00d4ff), and gold (#c8a84e). All text labels in Chinese characters only.
```

### 模板 C：老K 头像版（正方形）

```
Close-up of a King of Spades playing card in 16-bit pixel art, centered composition. The pixel king face fills most of the frame: navy garment, gold crown, confident pixel expression. Glowing ice-blue spade symbol. Dark background with floating pixel particles. Square 1:1 composition suitable for avatar/profile picture. Crisp pixel art style, retro 16-bit game aesthetic.
```

### 模板 D：纯扑克牌元素（文章配图）

```
A glowing King of Spades playing card in pixel art style, floating in dark space (#0d1117). The card is surrounded by [主题: pixel art candlestick patterns / 8-bit financial data visualizations / retro-style stock market indicators]. Ice blue (#00d4ff) pixel glow effects and gold (#c8a84e) accents. Scattered pixel blocks and data fragments. 16-bit retro game aesthetic, visible pixel grid, clean composition. No human figures.
```

### 模板 E：日常发帖配图（扑克牌角标 + 内容主体）

这是日常发帖的**首选模板**。像素扑克牌仅占画面约 1/6（角落），其余 5/6 留给主题内容。所有图内文字必须是中文。

```
Style: 16-bit pixel art illustration, visible pixel grid, retro game aesthetic meets modern fintech, dark moody palette, crisp clean pixel rendering, all text labels in Chinese only no English

Content: [根据帖子主题自由发挥的场景描述，占画面主体 5/6。用中文标签和像素风视觉元素填充，风格和内容应与帖子主题匹配。如果涉及中国股市涨跌，遵循红涨绿跌惯例。所有图表、数据面板、趋势线均用像素风格绘制]. The background is dark navy (#1a2744) with floating ice-blue (#00d4ff) pixel particles. In the [bottom-left/bottom-right] corner (approximately 1/6 of the image), a small pixel art King of Spades playing card with glowing ice-blue spade symbol and gold (#c8a84e) crown details, slightly tilted as a brand watermark. All text in the image must be in Chinese characters only, no English letters or words.
```

**要点**：
- **扑克牌 vs 内容 = 1:5** — 像素扑克牌放角落作为品牌标记，主体留给内容
- **所有文字必须中文** — 包括图表标签、标题、百分比说明等，一律中文，禁止出现英文字母
- **红涨绿跌** — 遵循中国市场惯例（RED = 上涨, GREEN = 下跌）
- **统一像素风** — 所有元素（图表、文字、装饰）都应保持像素艺术风格的一致性
- 适合画幅：16:9（横版封面）或 3:4（小红书竖版）

## 使用指南

### 调用 image-generator 时

1. 从上方模板中选择最合适的模板
2. 替换 `[方括号]` 中的占位符为具体内容
3. 可追加风格修饰词：`--style 16-bit pixel art`
4. 建议画幅：正方形(1:1)用于头像，16:9 用于文章封面，3:4 用于小红书竖版

### 风格一致性要点

- **必须保持**：像素艺术风格、藏青+冰蓝+金三色体系、黑桃K扑克牌作为 IP 锚点
- **可以变化**：牌面内容（国王/图表/数据）、像素密度(8-bit vs 16-bit)、周围场景元素
- **避免**：写实照片风格、人物肖像/半身像、非像素的平滑渐变、暖色调为主的配色
