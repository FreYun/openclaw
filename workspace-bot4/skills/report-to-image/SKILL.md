# /report-to-image — 研报解读生成配图

**触发词**：`/report-to-image`、"生成配图"、"做成图片"、"把解读画出来"

**前置条件**：已有结构化的研报解读文档（`memory/研报解读/YYYY-MM-DD-主题.md`）

> **重要：每次必须根据当前研报内容重新写 prompt。下方示例仅供参考格式和风格，严禁照搬示例中的具体内容。**

---

## 工作流

### Step 1：拆分为 6 张图

| 图序 | 定位 | 说明 |
|------|------|------|
| 图1 | 封面总览 | 标题 + 四象限核心观点 |
| 图2 | 核心观点 A | 最有冲击力的观点（现状/矛盾） |
| 图3 | 核心观点 B | 对比/争议 |
| 图4 | 关键数据 | 市场规模/时间轴/数据可视化 |
| 图5 | 玩家动态 | 主要公司进展（卡片网格） |
| 图6 | 风险 + 启示 | 收尾总结 |

内容不够 6 张可减至 4-5 张，不凑数。

### Step 2：写 style 和 content

**style（固定基底，保证系列一致）：**

```
hand-drawn editorial infographic page, vertical 3:4 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, golden yellow accent highlights, earth tone color palette (cream, gold, olive green, warm brown, steel blue), professional financial education aesthetic, Xiaohongshu knowledge card style
```

封面图将 `page` → `cover`。按需追加：`, comparison visual layout` / `, company profiles grid layout` / `, timeline and data visualization elements` / `, warning elements and takeaway layout`

**content（每次根据研报内容全新编写）：**
- 中文描述画面元素，标题标签用引号包裹
- 数据具体化（写"5万亿美元"不写"很大的数字"）
- 每个区域插画和文字标签配对描述

### Step 3：调用生图

```
工具：image-gen-mcp.generate_image
  style: "{style}"
  content: "{content}"
  size: "1024x1536"
  model: "banana2"    ← 必须 banana2，中文渲染准确
```

### Step 4：保存

每次新建文件夹，路径：`image/YYYY-MM-DD-主题-配图/`

```bash
DEST="image/2026-03-23-人形机器人-配图"
mkdir -p "$DEST"
cp "{files[0]}" "$DEST/01-封面总览.png"
cp "{files[1]}" "$DEST/02-xxx.png"
# ...
```

### Step 5：检查

逐张检查中文渲染，有误则微调 content 重新生成该张。确认后告知研究部图片位置。

---

## 示例（仅供参考格式，不可照搬内容）

以下是「人形机器人研报」的 prompt 示例，展示 content 的写法：

**图1 封面**：
```
content: 顶部大标题黑色粗体中文"人形机器人行业全景", 中央等距视角人形机器人站在平台上, 四方向分区: 左上金币堆叠标签"订单火热 执行存疑", 右上工厂流水线标签"2026目标激进", 左下地球趋势箭头标签"长期空间5万亿美元", 右下科技公司剪影标签"核心玩家", 金黄色高亮背景, 齿轮电路图案点缀
```

**图6 风险启示**：
```
content: 顶部大标题"风险提示与投资启示", 上半红色调2x3网格: 机器手抓不住物体"技术瓶颈", 未交付箱子和时钟"交付风险", 公司挤窄门"竞争加剧", 慢速流水线"产能爬坡", 泡沫股价图"估值风险", 地球裂痕"地缘政治", 下半绿色调三条启示: ①"别被标题忽悠" ②"短期谨慎长期乐观" ③"软件能力是关键"
```

---

## 注意事项

1. **banana2 模型**：banana 中文乱码，必须用 banana2
2. **竖版 1024x1536**：小红书标准比例
3. **style 不改**：只追加布局描述词，保证系列感
4. **合规**：配图不得出现股票代码、目标价、荐股表述
