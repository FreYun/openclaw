---
name: default-cover-style
description: ">"
---

# 默认封面风格 — 天天出版社 Pixel Edition

> 没有专属封面技能的 bot 用这个。像素画 + 出版社排版 = 辨识度。

---

## 核心美学

**天天出版社风**：像一本正经出版的财经读物，但插画全是像素画。反差感 = 记忆点。

| 要素 | 规范 |
|------|------|
| **画风** | 16-bit 像素画（pixel art），复古游戏机质感 |
| **排版** | 出版社书封排版：大标题居中、副标题在下、角色在固定位置 |
| **字体感** | 粗体无衬线，像书名一样有分量（AI 生图时描述为 bold blocky title text） |
| **出版社标记** | 右下角小字"天天出版社"或像素印章 |
| **整体感觉** | 像素游戏的封面 × 正经出版物 = 有趣但不幼稚 |

---

## 品牌色板

| 用途 | 色彩 | 说明 |
|------|------|------|
| 主背景 | 米色/羊皮纸 parchment | 出版物质感 |
| 标题文字 | 深墨色 charcoal #2D2D2D | 书名的分量感 |
| 通用强调 | 藏蓝 navy #1a2744 | 天天出版社品牌色 |
| 涨/利好 | 暖红 warm red #C43E3E | 像素心心、红色箭头 |
| 跌/利空 | 薄荷绿 mint #4A9E8E | 像素雨滴、绿色箭头 |
| 角色描边 | 纯黑 #000000 | 像素角色轮廓 |

---

## 角色生成规则

**每个 bot 的像素角色从 SOUL.md 中提取特征。** 生图前必须读自己的 SOUL.md，然后按以下规则构建角色描述：

1. **从 SOUL.md 提取**：性别、发型、标志性配饰、性格关键词
2. **转译为像素画描述**：
   - 人物：16x16 pixel character, chibi proportions, 2-head-tall
   - 配饰：像素化的标志物（如金币→pixel gold coin, 眼镜→pixel square glasses）
   - 表情：根据内容情绪选择（见下方情绪表）

### 像素角色模板

```
{性别} pixel art character in 16-bit retro game style, chibi 2-head-tall proportions, {发型描述}, {标志配饰}, {服装}, pixel art style with visible individual pixels, black pixel outline, {表情}
```

### 情绪 × 角色状态

| 内容情绪 | 配色 · 角色状态 · 道具 |
|---------|----------------------|
| 利好/上涨 | 暖红 · 星星眼举手欢呼 · pixel red arrow up, pixel gold coins |
| 利空/下跌 | 薄荷绿 · 瀑布泪蹲下 · pixel green arrow down, pixel rain |
| 中性/科普 | 藏蓝 · 微笑手持书本 · pixel book, pixel magnifying glass |
| 争议/观点 | 橙色 · 叉腰感叹号 · pixel exclamation mark |

---

## 封面模板

> **核心关键词**：`parchment` · `16-bit pixel art` · `bold blocky title` · `navy border` · `chibi character`

### 竖版封面（小红书帖子）3:4 = 1024x1536

```
STYLE:
A vertical 3:4 social media post cover designed like a retro pixel art book cover, warm parchment paper textured background with subtle aged grain, large bold blocky dark charcoal text centered as the main title like a book name, clean pixel art decorative border frame around the edges in navy blue pixel lines, bottom-right area has a small {角色像素描述} standing on a pixel platform, top-left corner has a tiny pixel publisher logo mark, a few scattered pixel sparkle decorations, overall aesthetic combines serious editorial book cover typography with playful 16-bit pixel art illustrations, the contrast between formal layout and pixel art creates visual interest, warm muted color palette dominated by parchment cream navy and {情绪配色}

CONTENT:
Chinese text on cover: 「{封面文字}」
```

### 横版封面（公众号/长文）3:2 = 1536x1024

```
STYLE:
A horizontal 3:2 cover image designed like a retro pixel art book jacket, warm parchment paper textured background, large bold blocky dark charcoal title text on the left two-thirds, right side has a {角色像素描述} in a characteristic pose, thin pixel art border frame in navy blue, small pixel publisher stamp in bottom-right corner, pixel art decorative elements scattered subtly, combines editorial book cover design with 16-bit pixel art aesthetic, warm muted parchment cream and navy palette with {情绪配色} accents

CONTENT:
Chinese text: 「{封面文字}」
```

---

## 生图调用

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{从上方模板整段复制，替换 {角色像素描述} 和 {情绪配色}}",
  content: "Chinese text on cover: 「{封面文字}」",
  size: "1024x1536",
  model: "banana2",
  workspace: "/home/rooot/.openclaw/workspace-{botN}"
)'
```

---

## 工作流程

1. **读 SOUL.md** → 提取角色特征 → 构建像素角色描述
2. **判断情绪** → 选择情绪配色和角色状态
3. **写封面文字** → 从帖子标题/核心观点提炼，≤15 字
4. **组装 prompt** → 复制 STYLE 模板，填入角色描述 + 情绪配色 + 封面文字
5. **确认方案** → 发送封面方案给研究部确认；紧急情况可直接生图
6. **生图** → 调用 image-gen-mcp
7. **展示** → 把图片复制到 workspace 并发送给研究部看

---

## 铁律

1. **每次生图前必须 Read 本文件** — 不要凭记忆写 prompt
2. **每次生图前必须 Read SOUL.md** — 角色特征从 SOUL 来，不要编
3. **STYLE 模板整段复制再替换变量** — 不要自由发挥改模板
4. **竖版 1024x1536，横版 1536x1024** — 不要用正方形
5. **model 必须用 banana2** — 中文渲染需要
6. **中文可能乱码** — 乱码时保留图（像素角色有价值），文字后期叠加

---

_天天出版社默认封面。没有专属风格的 bot 共用此模板，通过 SOUL.md 差异化角色。_
