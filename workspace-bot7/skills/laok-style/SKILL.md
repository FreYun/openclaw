---
name: laok-style
description: "老K投资笔记"专属画图风格定义。日常发帖默认生成大标题文字封面 + 右下角像素扑克牌 icon。研究部要求时可生成概念插画。
---

# 老K投资笔记 · 画图风格指南

## 核心 IP 形象

**老K** — 一张像素风的黑桃K扑克牌，放在封面右下角作为品牌 icon。不画人物，只画牌。

### 扑克牌 icon 设定

- **牌面**：黑桃K (King of Spades)，像素艺术风格
- **配色**：藏青 `#1a2744` 牌面 + 冰蓝 `#00d4ff` 黑桃发光 + 金色 `#c8a84e` 王冠
- **位置**：右下角，约占画面 1/8，微微倾斜，作为品牌水印

## 配色方案

```
背景色（暖底）:
  暖米白  #faf6f0  (主背景色，温暖明亮)
  浅暖灰  #e8e0d4  (辅助背景/区块分隔)
  淡奶茶  #f0e6d6  (渐变过渡/装饰底色)

扑克牌 IP 色（冷色，保持科技感）:
  藏青    #1a2744  (牌面底色/牌背)
  冰蓝    #00d4ff  (像素光效/黑桃发光)
  金色    #c8a84e  (王冠/纹饰/点缀)

内容区:
  深炭    #2a2a2a  (标题文字)
  纯白    #ffffff  (牌面边框/高光)
```

## Prompt 模板

> **关键原则**：STYLE 参数整段复制不改动。CONTENT 参数只放变量部分。

### 模板 A：大标题文字封面 — ⭐ 默认模板

日常发帖的**唯一默认模板**。画面主体是醒目的中文大标题文字，右下角放像素扑克牌 icon。**不画 K 线图、蜡烛图、数据面板等金融图表**。

**STYLE（直接复制）**
```
Bold Chinese title text poster, clean modern layout, warm bright background of creamy white (#faf6f0) with soft beige (#e8e0d4) accents, large eye-catching Chinese headline text as the main visual element, text in dark charcoal (#2a2a2a) or contrasting bold colors, minimal decorative elements, clean typography focus, no candlestick charts no stock graphs no financial dashboards
```

**CONTENT 模板**
```
Large bold Chinese title text "[帖子标题/核心观点]" prominently displayed as the main visual, filling most of the image. Text should be eye-catching with [字体效果，如: bold weight with subtle shadow / gradient color accent on key words / slight 3D pixel effect]. Simple decorative accents like [装饰，如: small pixel sparkles / subtle geometric shapes / faint topic-related icon]. In the bottom-right corner, a small pixel art King of Spades playing card in dark navy (#1a2744) with glowing ice-blue (#00d4ff) spade symbol and gold (#c8a84e) crown details, slightly tilted as a brand watermark (approximately 1/8 of the image). The background is warm creamy white (#faf6f0). All text must be in Chinese characters only, no English.
```

**要点**：
- **大标题文字为主角** — 画面 80%+ 是醒目的中文标题
- **不要画金融图表** — 不要 K 线、蜡烛图、柱状图、数据面板、趋势线
- **扑克牌是右下角小 icon** — 约占画面 1/8，品牌水印
- **所有文字必须中文**
- **装饰从简** — 少量像素风点缀即可，不喧宾夺主
- 画幅：3:4 `960x1280`（小红书竖版）

### 模板 B：概念插画封面 — 仅研究部要求时使用

研究部明确要求"画概念插画/主题插画"时才用。像素扑克牌占 1/6 角落，主体是主题相关的像素插画。

**STYLE（直接复制）**
```
16-bit pixel art illustration, visible pixel grid, retro game aesthetic meets modern fintech, warm bright palette with creamy white (#faf6f0) background and soft beige (#e8e0d4) accents, crisp clean pixel rendering, all text labels in Chinese only no English
```

**CONTENT 模板**
```
[根据帖子主题的像素插画场景，占画面主体 5/6。用像素风视觉元素表达主题概念，如: 像素风太阳能板阵列 / 像素风芯片电路 / 像素风机器人 / 像素风火箭发射等。不要画 K 线图和蜡烛图]. The background is warm creamy white (#faf6f0) with soft beige (#e8e0d4) accents and floating ice-blue (#00d4ff) pixel particles. In the bottom-right corner (approximately 1/6 of the image), a small pixel art King of Spades playing card in dark navy (#1a2744) with glowing ice-blue spade symbol and gold (#c8a84e) crown details, slightly tilted as a brand watermark. All text in the image must be in Chinese characters only.
```

**要点**：
- **需研究部明确要求才使用**，日常默认用模板 A
- 用具象的像素图标表达概念（芯片、火箭、太阳能板等），不用金融图表
- 扑克牌放右下角作为品牌标记

## 生图调用

```
image-gen-mcp.generate_image(
  style: "{直接复制对应模板的完整 STYLE}",
  content: "{替换好占位符的 CONTENT}",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot7",
  reference_image: "{可选，本地图片路径}"
)
```

- 默认画幅：3:4 `960x1280`（小红书竖版）

## 铁律

1. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt
2. **STYLE 整段复制，不可缩写/省略/改写**
3. **CONTENT 只放变量** — 不要重复写风格描述
4. **默认用模板 A（大标题文字）** — 不要自作主张用模板 B，除非研究部明确要求概念插画

## 风格一致性要点

- **必须保持**：暖米白底色、右下角像素扑克牌 icon（藏青+冰蓝+金色）、中文大标题为主角
- **可以变化**：标题排版样式、装饰点缀元素
- **避免**：K 线图/蜡烛图/数据面板/金融图表（除非研究部明确要求）、写实照片风格、人物肖像、深暗背景色
