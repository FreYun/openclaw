---
name: alex-cover-style
description: "美股学长Alex"专属封面生图风格定义。半写实动漫风留子形象 + 5套封面 STYLE 模板。调用 image-gen-mcp 时引用此 skill 获取风格 prompt。
---

# 美股学长Alex · 封面生图风格指南

## 核心 IP 形象

**Alex** — 半写实/动漫风的北美留子形象。典型亚洲男生 20s，穿搭随意但有辨识度。

### 角色设定表

| 属性 | 描述 | 强制约束 |
|------|------|----------|
| **风格** | 半写实动漫插画 (semi-realistic anime illustration)，人体比例接近真实（头身比 1:6~1:7），线条干净，色彩丰富 | 禁止 chibi/Q版、禁止像素风、禁止纯写实照片 |
| **性别/年龄** | 亚洲男性，22-25岁，大学生/研究生气质 | 不是中年人、不是高中生 |
| **发型** | 深棕色 #3D2B1F 短发，微卷蓬松，略长刘海 | 有点 messy 但不邋遢 |
| **配饰** | 圆框眼镜，镜片带浅蓝反光 #63B3ED；白色 AirPods（偶尔出现） | 圆框眼镜必须出现 |
| **帽子** | 深蓝色 #1A365D 棒球帽，可正戴/反戴 | 封面图必须戴帽，形象图可选 |
| **上衣** | 深蓝色 #1A365D oversized hoodie，胸前印白色 $ 符号 | 颜色和符号固定 |
| **下装** | 黑色休闲裤或牛仔裤 | 不是西裤 |
| **道具** | 银色 MacBook、外卖咖啡杯（白杯棕色杯套）、手机 | 至少出现一个 |
| **表情** | 默认：微微侧头看屏幕，嘴角带笑 | 不是呆板正脸 |
| **肤色** | 暖米色 #F5DEB3 | 固定 |
| **身体语言** | 略微慵懒/relaxed | 不是站军姿 |

### 角色锚定描述块

**封面图用（角色较小，画面一角）**：
```
A semi-realistic anime style young East Asian man in his early 20s, visible in the bottom-right area of the image (approximately 1/5 of the frame). He has short slightly curly dark brown (#3D2B1F) hair, round glasses with light blue (#63B3ED) lens reflection, wearing a dark navy (#1A365D) baseball cap and an oversized dark navy hoodie with a white $ symbol on the chest. He holds a white takeaway coffee cup with a brown sleeve. Relaxed posture, slight smile. Semi-realistic anime illustration style with clean lines, soft cel-shading, detailed features. Not chibi, realistic body proportions (1:6 head-to-body ratio).
```

**形象图用（角色为主体，半身或全身）**：
```
A semi-realistic anime style young East Asian man in his early 20s as the main subject, upper body or full body centered in frame. Short slightly curly dark brown (#3D2B1F) hair, round glasses with light blue (#63B3ED) lens reflection, dark navy (#1A365D) baseball cap worn backwards. Wearing an oversized dark navy (#1A365D) hoodie with white $ symbol on chest. Holding a silver MacBook under one arm or a white takeaway coffee cup. Warm skin tone (#F5DEB3). Relaxed confident expression. Semi-realistic anime illustration, clean detailed linework, soft cel-shading, vibrant colors, detailed facial features and clothing folds. Realistic proportions (1:6 head-to-body), not chibi, not pixel art, not flat illustration.
```

### 表情变体库

| 表情 | 描述 | 适用场景 |
|------|------|----------|
| ☕ **淡定看盘** | 微笑看手机/MacBook，一手拿咖啡 | 日常复盘 |
| 🤔 **皱眉分析** | 眉头微蹙，推眼镜，盯屏幕 | 数据解读、复杂行情 |
| 😮 **惊了** | 眼睛睁大，咖啡杯悬在半空，嘴微张 | 重大事件、意外数据 |
| 😮‍💨 **无语** | 单手扶额，眼神空洞 | 大跌、Fed 放鹰 |
| 🫠 **崩溃** | 趴在 MacBook 上，咖啡杯倒了 | 暴跌、portfolio 爆炸 |
| 😎 **得意** | 翘二郎腿，咖啡杯举起，自信笑 | 大涨、判断正确 |

### 场景变体库

| 场景 | 描述 | 适用 |
|------|------|------|
| **深夜宿舍** | 暗色调，MacBook 屏幕光照脸，桌上咖啡杯和零食 | 美股实时/FOMC |
| **咖啡店** | 暖光，落地窗，背景模糊路人 | 日常复盘 |
| **图书馆** | 木桌，书本旁开着 MacBook | 深度分析 |
| **户外阳光** | 蓝天，戴墨镜推到额头上 | 周末总结 |

## 配色方案

```
角色固定色:
  发色      #3D2B1F  (深棕微卷)
  眼镜      #63B3ED  (蓝色反光)
  帽子/卫衣 #1A365D  (深蓝)
  肤色      #F5DEB3  (暖米)
  咖啡杯    #FFFFFF + #8B6914 (白杯棕套)
  MacBook   #C0C0C0  (银色)

背景色（按内容选用）:
  暖黄      #F5A623  (日常复盘、数据对比)
  活力橙    #FF6B35  (热点事件)
  深蓝      #1A365D  (政策解读、夜间场景)
  薰衣草    #B794F4  (周末、轻松内容)
  浅灰白    #F7F7F7  (财经日历)

文字色:
  深黑      #1A1A1A  (浅色底标题)
  纯白      #FFFFFF  (深色底标题)
  红色      #E53E3E  (涨 / 重点)
  绿色      #38A169  (跌 / 对比)
```

## Prompt 模板

> **铁律**：STYLE 整段复制不改，CONTENT 只放变量。

### 模板 A：日常复盘封面 — ⭐ 首选

暖黄/橙背景 + 粗体大标题主体 + Alex 角色右下角。所有图内文字必须中文。

**STYLE（直接复制）**
```
Semi-realistic anime illustration style financial infographic cover. Bold large Chinese typography as the dominant visual element taking up 50-60% of the image. Warm yellow-orange gradient background (#F5A623 to #FF6B35). Minimalist financial decorative elements (simple candlestick chart outlines, subtle trend arrows, percentage symbols) as background accents. Professional yet youthful aesthetic, clean composition. All text must be in Chinese characters only, no English text in the image. Red (#E53E3E) for positive numbers, green (#38A169) for negative numbers (Chinese market convention). In the bottom-right area (approximately 1/5 of the image), a semi-realistic anime style young East Asian man in his early 20s with short slightly curly dark brown (#3D2B1F) hair, round glasses with light blue (#63B3ED) lens reflection, dark navy (#1A365D) baseball cap, oversized dark navy hoodie with white $ on chest, holding a white takeaway coffee cup, relaxed slight smile. Clean detailed linework, soft cel-shading, realistic proportions (not chibi). He appears as a brand signature element.
```

**CONTENT 模板**
```
Main title: "[标题，如：3.27美股三大指数收盘速览]". Data text: "[数据，如：道指+0.8% 标普+1.2% 纳指+1.5%]". Character expression: [表情，如：relaxed smile looking at phone / surprised wide eyes with coffee cup raised]. Background accents: [装饰描述].
```

**背景色速查**：

| 行情 | 背景 | 角色表情 |
|------|------|----------|
| 涨/利好 | 暖黄 #F5A623 | ☕ 淡定 或 😎 得意 |
| 跌/利空 | 活力橙 #FF6B35 | 😮‍💨 无语 或 🫠 崩溃 |
| 震荡 | 暖黄 #F5A623 | 🤔 皱眉 |

### 模板 B：事件/热点封面

深蓝底 + 事件相关视觉 + 大标题 + Alex 角色。

**STYLE（直接复制）**
```
Semi-realistic anime illustration cover with dramatic atmosphere. Deep navy blue background (#1A365D) with subtle gradient to darker (#0D1117). Bold white Chinese typography as the main visual element. Clean modern editorial layout with event-related flat graphic elements (geometric shapes, silhouettes, symbolic illustrations). Professional financial media aesthetic with youthful energy. All text in Chinese characters only, no English in the image. In the bottom-right area (approximately 1/5 of the image), a semi-realistic anime style young East Asian man in his early 20s, short curly dark brown hair, round glasses with blue reflection, dark navy baseball cap, oversized navy hoodie with white $, holding phone or looking surprised. Clean linework, soft cel-shading, realistic proportions. Semi-realistic anime style, not chibi, not pixel art.
```

**CONTENT 模板**
```
Main title: "[事件标题]". Illustration elements: [事件插画描述]. Character expression: [表情]. Color accent: [强调色].
```

### 模板 C：数据对比封面

暖黄底 + 大数字对比 + 红绿色码 + Alex 角色。

**STYLE（直接复制）**
```
Semi-realistic anime illustration data comparison infographic. Warm yellow background (#F5A623). Two or three lines of very large bold Chinese text with prominent numbers as the visual hero (70% of image). Numbers color-coded: red (#E53E3E) for positive/up, green (#38A169) for negative/down, dark (#1A1A1A) for labels. Minimal decoration, clean typography impact. All text in Chinese only. In the bottom-right corner (approximately 1/8 of the image), a semi-realistic anime style young East Asian man, short curly dark brown hair, round glasses, dark navy baseball cap, navy hoodie with white $, pointing at data or adjusting glasses. Clean linework, soft cel-shading, realistic proportions. Not chibi, not pixel art.
```

**CONTENT 模板**
```
Line 1: "[对比项A]" in [颜色]. Line 2: "[对比项B]" in [颜色]. Optional subtitle: "[说明]". Character expression: [表情].
```

### 模板 D：财经日历封面

浅色底 + 日历排版 + Alex 角色。

**STYLE（直接复制）**
```
Clean financial calendar infographic with semi-realistic anime character. Light warm background (#F7F7F7 or pale yellow #FFF9E6). Calendar entries arranged by date with colored timestamps. Each entry has date marker, time, country flag emoji, event name in Chinese. Important events highlighted with soft colored backgrounds. Professional editorial calendar aesthetic, clean typography. All text in Chinese, no English. In the bottom-right corner (approximately 1/8 of the image), a semi-realistic anime style young East Asian man, short curly dark brown hair, round glasses, dark navy baseball cap, navy hoodie with white $, calm expression holding coffee cup. Clean linework, soft cel-shading, realistic proportions. Not chibi.
```

**CONTENT 模板**
```
Calendar period: "[时间段]". Entries: [日历条目]. Highlight: "[重点事件]". Character expression: [表情].
```

### 模板 E：角色形象图（头像/立绘）

Alex 半身/全身大图，居中主体。

**STYLE（直接复制）**
```
Semi-realistic anime illustration of a young East Asian man in his early 20s as the main subject, upper body centered, taking up 60-70% of the frame. Head-to-body ratio approximately 1:6 (realistic proportions). Short slightly curly dark brown (#3D2B1F) hair with messy bangs. Round glasses with light blue (#63B3ED) lens reflection. Dark navy (#1A365D) baseball cap worn backwards. Oversized dark navy (#1A365D) hoodie with a white $ dollar sign on the chest, slightly pushed-up sleeves. Warm skin tone (#F5DEB3). Detailed facial features: defined jawline, natural eyebrows, warm brown eyes. Clean semi-realistic anime style with detailed linework, soft cel-shading, subtle highlights on hair and glasses. Vibrant colors, no flat illustration, no chibi, no pixel art, no photorealistic. Simple solid color background.
```

**CONTENT 模板**
```
Character pose and expression: [描述，如：leaning on one hand with coffee cup, relaxed confident smile / looking at MacBook screen with slight frown, one AirPod in / backwards cap, arms crossed, smirking]. Background: [纯色，如：solid warm yellow #F5A623 / solid lavender #B794F4 / solid navy #1A365D]. Props: [道具，如：silver MacBook open on desk / white coffee cup with brown sleeve / phone showing stock chart].
```

### 模板 F：深夜看盘场景（氛围感）

Alex 深夜场景，MacBook 屏幕光。适合 FOMC、earnings season 等夜间事件。

**STYLE（直接复制）**
```
Semi-realistic anime illustration, atmospheric night scene. A young East Asian man in his early 20s sitting at a desk in a dimly lit room. The main light source is the MacBook screen casting a cool blue-white glow on his face. Short slightly curly dark brown (#3D2B1F) hair, round glasses reflecting the screen light (#63B3ED), dark navy (#1A365D) hoodie with white $. A white takeaway coffee cup on the desk beside the laptop. Dark moody atmosphere, navy and deep blue tones (#0D1117 to #1A365D), with warm accent from a small desk lamp or phone notification. Detailed semi-realistic anime style, soft lighting, subtle shadows, cinematic composition. Not chibi, realistic proportions. Bold Chinese text overlay for title.
```

**CONTENT 模板**
```
Title overlay: "[标题，如：Fed 又放鹰了 我3am还在看直播]". Character state: [描述，如：squinting at screen, one hand on coffee / face-palming while looking at red numbers / leaning back with tired expression]. Screen content hint: [屏幕上模糊显示的内容，如：stock chart with red candles / FOMC press conference / earnings report].
```

## 生图调用

**STYLE 从模板整段复制，CONTENT 只放变量。有参考图时传 `reference_image`。**

```
image-gen-mcp.generate_image(
  style: "{直接复制对应模板的完整 STYLE}",
  content: "{替换好占位符的 CONTENT}",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot13",
  reference_image: "{可选，本地图片路径，模型会参考该图的风格/构图/色彩}"
)
```

- 画幅：3:4 `960x1280`（小红书竖版/首选）| 16:9 `1536x1024`（横版封面）| 1:1 `1024x1024`（头像/模板E）
- `reference_image`：生成过满意的 Alex 形象图后，后续生图都传入保持角色一致性

## 铁律

1. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，以文件内容为准
2. **STYLE 整段复制，不可缩写/省略/改写**
3. **CONTENT 只放变量** — 不要重复写风格描述
4. **先建议模板再生图** — 确认后再调用
5. **角色一致性** — 尽可能传入 reference_image 保持 Alex 形象统一
6. **红涨绿跌** — 遵循中国市场惯例

## 模板选择速查

| 内容类型 | 推荐模板 | 背景 | 角色 |
|---------|---------|------|------|
| 日常复盘 | **模板A**⭐ | 暖黄/橙 | 1/5 右下角 |
| 重大事件 | 模板B | 深蓝 | 1/5 右下角 |
| 数据对比 | 模板C | 暖黄 | 1/8 右下角 |
| 财经日历 | 模板D | 浅灰白 | 1/8 右下角 |
| 头像/立绘 | 模板E | 纯色 | 60-70% 居中 |
| FOMC/深夜 | 模板F | 深色氛围 | 场景主角 |

## 风格一致性要点

- **必须保持**：半写实动漫风、圆框眼镜+深蓝棒球帽+$hoodie、留子道具（咖啡/MacBook/手机）
- **可以变化**：帽子正反戴、表情、场景、背景色、道具组合
- **避免**：chibi/Q版、像素风、纯写实照片、3D渲染、扁平插画、花哨渐变
