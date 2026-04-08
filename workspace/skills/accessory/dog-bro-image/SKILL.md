---
name: dog-bro-image
description: 狗哥说财可视化图表规范——图表类型、统一视觉风格、配色规则、生图工作流。生图时必须遵循此规范。用法：生图前读此文件，或 /dog-bro-image 查看规范。
---

# 狗哥说财 生图规范 /dog-bro-image

**触发词**：`/dog-bro-image`、"生图规范"、"图片风格"、"配图怎么做"

> **重要：每次必须根据当前研究报告内容重新写 prompt。下方示例仅供参考格式和风格，严禁照搬示例中的具体内容。**

---

## 图表类型

| 类型 | 适用场景 | 制作方式 |
|------|---------|---------|
| **产业链全景图** | 上中下游拆解 | 用大模型生成图片，流程图/树状图风格 |
| **竞争格局图** | 同环节公司对比 | text_to_image 表格卡片 |
| **数据对比图** | 市占率/营收/增速 | text_to_image 数据卡片 |
| **事件影响图** | 热点→产业链传导 | 用大模型生成图片，因果链路图 |
| **公司定位图** | 公司在产业链的位置 | 用大模型生成图片，标注定位 |

---

## 风格定义

### style（固定基底，每张图必须完整使用，不可删减）

> **铁律：下方 style 是所有图片的统一视觉基底。生图时 style 参数必须完整复制此文本，仅在末尾追加类型修饰词。不可缩写、不可省略、不可改写。**

```
hand-drawn style educational infographic, vertical 3:4 ratio, off-white textured paper background, all text in Chinese, information organized in organic rounded blob-shaped card sections with soft pastel colored wavy borders (not sharp rectangles), each card section has irregular curved outlines like hand-drawn bubbles, mint green (#B2E0D6) and coral pink (#F5A8A0) and light blue (#A8D8EA) and soft yellow (#FDEAA8) section border colors, white fill inside cards, hand-drawn style flat icons with colored outlines (chips circuits servers cables gears brains rockets satellites), bold black Chinese title text at top of page, sub-section headers in colored rounded label badges, key terms highlighted in small colored rounded tag boxes, curved colored arrows with round ends connecting sections (green blue pink arrows), dotted flow lines between elements, small explanatory Chinese text annotations next to icons, high information density layout, Xiaohongshu knowledge card aesthetic, professional yet warm and approachable, clean readable typography, no photographic elements only illustrated icons and diagrams
```

### 按图片类型追加修饰词（追加在 style 末尾）

| 图片类型 | 在 style 末尾追加 |
|---------|----------|
| 封面 | `, cover page layout, centered realistic product illustration or 3D render of the subject, series title banner at top in quotation marks, large bold product name below illustration, author credit at bottom` |
| 概念解析 | `, bridge or translation metaphor illustration, labeled diagram showing input-process-output, question-answer format sections, what-is-it explainer layout` |
| 产业链全景 | `, three-tier vertical flow chart, upstream section in mint green midstream in light blue downstream in coral pink, each tier contains multiple sub-items with small icons, curved arrows connecting tiers top to bottom` |
| 环节深挖 | `, categorized breakdown with 2-3 major blob cards each containing sub-categories, heart or brain metaphor icons for core components, tree-branch layout showing hierarchy, percentage and cost data labels` |
| 竞争格局 | `, versus comparison layout, tier ranking cards, progress bar or column chart visualization for market share, national flag icons for global comparison` |
| 技术路线 | `, horizontal timeline progression with product images, generation labels (current next-gen future), technology evolution arrows, specification data cards` |
| 数据/投资视角 | `, data summary cards with key numbers, bar chart or percentage column visualization, risk-reward balance layout, warning section in warm colors conclusion section in cool colors` |

### 配色规则（固定，不可改）

| 用途 | 颜色 | 色值 |
|------|------|------|
| 上游环节 / 第一分区 | 薄荷绿 | `#B2E0D6` |
| 中游环节 / 第二分区 | 浅蓝色 | `#A8D8EA` |
| 下游环节 / 第三分区 | 珊瑚粉 | `#F5A8A0` |
| 强调/高亮/数据 | 柔黄色 | `#FDEAA8` |
| 标题/正文 | 深灰黑色 | `#2D2D2D` |
| 卡片内部填充 | 白色 | `#FFFFFF` |
| 连接箭头 | 与所在分区同色（绿/蓝/粉） | — |

### 品牌标识

- 封面图底部标注 "🔗 狗哥说财"
- 颜色分区约定：上游=薄荷绿、中游=浅蓝、下游=珊瑚粉

---

## 图片分解模板

### 标准产业链拆解（6-9 张）

| 图序 | 定位 | 说明 |
|------|------|------|
| 图1 | **封面** | 系列标题"一天吃透一条产业链" + 产业链名称 + 产品/概念中心插图 |
| 图2 | **概念解析** | 这是什么？用比喻/类比一句话讲清核心概念，配解释性示意图 |
| 图3 | **产业链全景图** | 上游→中游→下游完整地图，每层列出关键环节和行业特征（不点名个股） |
| 图4 | **上游深挖** | 关键材料/零部件/芯片分类拆解，标注壁垒和国产化率 |
| 图5 | **中游深挖** | 制造/封装/集成环节，核心工艺和行业格局 |
| 图6 | **下游深挖** | 终端应用场景分类，需求驱动力 |
| 图7 | **竞争格局** | 全球vs国内、梯队特征、国产替代进度，不点名个股（可选） |
| 图8 | **技术路线** | 技术演进方向、关键节点（可选） |
| 图9 | **投资视角** | 核心数据汇总、风险提示（可选） |

**灵活规则**：
- 最少 6 张（图1-6），最多 9 张
- 产业链简单的主题可合并上/中/下游为 1-2 张
- 对比类主题（A vs B）可替换图4-6 为对比卡片
- 不凑数，内容不够就减少

### 对比类主题（A vs B）

| 图序 | 定位 | 说明 |
|------|------|------|
| 图1 | 封面 | 系列标题 + 对比主题 + 概念/产品类型对比插图（不出现公司名） |
| 图2 | 产业链定位 | 两类玩家在产业链中的位置标注 |
| 图3 | 业务结构对比 | 商业模式、收入构成类型对比 |
| 图4 | 行业数据对比 | 行业级核心指标卡片（市场规模/增速/渗透率） |
| 图5 | 竞争优势对比 | 不同路线/模式的护城河分析 |
| 图6 | 总结 | 一句话结论 + 风险提示 |

---

## 生图工作流

### Step 1：阅读报告，拆分图片

读完研究报告后，确定用哪个模板（标准产业链 or 对比类），列出每张图的主题和核心内容要点。

### Step 2：编写 content prompt

**content 编写规则**：
- 全部用中文描述画面元素
- 标题和标签文字用引号包裹（如 `"光模块产业链全景图"`）
- 数据必须具体化（写 "市场规模 800 亿" 不写 "很大的市场"）
- 每个卡片区域用 "区域+内容" 格式描述（如 `顶部标题区"xxx", 中部三栏卡片: 左栏...`）
- 图标/插画元素要具体描述（如 `芯片简笔图标`, `服务器机柜图标`, `5G基站图标`）
- 文字标签和图标配对出现

### Step 3：调用生图

> **每张图的 style 参数必须完整复制「风格定义」中的固定基底文本，然后在末尾追加对应图片类型的修饰词。不可缩写、不可省略任何描述词。这是保证全系列视觉一致性的关键。**

```
工具：image-gen-mcp.generate_image
  style: "{完整复制固定 style 基底全文} + {末尾追加类型修饰词}"
  content: "{当前图片的 content}"
  size: "1024x1536"
  model: "nano banana2"
```

**style 拼接示例**（以封面图为例）：
```
style: "hand-drawn style educational infographic, vertical 3:4 ratio, off-white textured paper background, all text in Chinese, information organized in organic rounded blob-shaped card sections with soft pastel colored wavy borders (not sharp rectangles), each card section has irregular curved outlines like hand-drawn bubbles, mint green (#B2E0D6) and coral pink (#F5A8A0) and light blue (#A8D8EA) and soft yellow (#FDEAA8) section border colors, white fill inside cards, hand-drawn style flat icons with colored outlines (chips circuits servers cables gears brains rockets satellites), bold black Chinese title text at top of page, sub-section headers in colored rounded label badges, key terms highlighted in small colored rounded tag boxes, curved colored arrows with round ends connecting sections (green blue pink arrows), dotted flow lines between elements, small explanatory Chinese text annotations next to icons, high information density layout, Xiaohongshu knowledge card aesthetic, professional yet warm and approachable, clean readable typography, no photographic elements only illustrated icons and diagrams, cover page layout, centered realistic product illustration or 3D render of the subject, series title banner at top in quotation marks, large bold product name below illustration, author credit at bottom"
```

### Step 4：保存文件

每次新建文件夹，路径：`image/YYYY-MM-DD-主题-配图/`

```bash
DEST="image/2026-03-25-存储芯片-配图"
mkdir -p "$DEST"
cp "{files[0]}" "$DEST/01-封面.png"
cp "{files[1]}" "$DEST/02-概念解析.png"
cp "{files[2]}" "$DEST/03-产业链全景.png"
cp "{files[3]}" "$DEST/04-上游深挖.png"
cp "{files[4]}" "$DEST/05-中游深挖.png"
cp "{files[5]}" "$DEST/06-下游深挖.png"
# 可选
cp "{files[6]}" "$DEST/07-竞争格局.png"
cp "{files[7]}" "$DEST/08-技术路线.png"
```

### Step 5：质量检查

- 逐张检查中文字符渲染是否正确
- 检查信息层级是否清晰（标题>小标题>正文>注释）
- 有误则微调该张的 content 重新生成，不必全部重来
- 确认后告知研究部图片位置

---

## 注意事项

1. **nano banana2 模型**：必须用 nano banana2，中文渲染准确
2. **竖版 1024x1536**：小红书标准 3:4 比例
3. **style 完整复制不可改**：每张图的 style 参数必须完整复制「风格定义」中的固定基底全文，仅在末尾追加类型修饰词。不可缩写、不可省略、不可用自己的话改写。这是全系列视觉统一的基石
4. **合规红线**：配图不得出现任何个股信息（包括但不限于：具体公司名称、股票代码、目标价、荐股表述、个股财务数据）。竞争格局图只描述行业梯队特征和市场格局，用"行业龙头"、"第一梯队"等泛化表述，不点名具体公司
5. **水印**：封面图底部标注 "🔗 狗哥说财"
6. **信息密度**：每张图要有实质内容，不做纯装饰图
7. **颜色分区**：上游用薄荷绿、中游用浅蓝、下游用珊瑚粉，保持全系列一致

---

## 示例（仅供参考格式，不可照搬内容）

以下是「光模块产业链」的 content 示例，展示写法：

**图1 封面**：
```
content: 顶部横幅区浅灰底深色中文"一天吃透一条产业链", 中央大号产品实物插图一个光模块造型(银色金属外壳带绿色PCB和光纤接口), 下方大号粗体中文"光模块", 底部小字作者署名"🔗 狗哥说财"
```

**图3 产业链全景图**：
```
content: 顶部大标题粗体中文"光模块产业链全景图", 三层竖向排列: 第一层薄荷绿圆角卡片标题"上游：核心元器件与材料"副标题"技术核心，高壁垒，决定性能上限"内含四个子项带图标(光芯片放大镜图标、电芯片电路板图标、光无源器件光纤图标、配套材料PCB图标), 第二层浅蓝圆角卡片标题"中游：光模块设计、封装与测试"副标题"价值实现，系统集成&规模化生产"内含核心流程(设计→封装→测试)和关键能力(高速率设计、先进工艺、管理控制), 第三层珊瑚粉圆角卡片标题"下游：应用场景与需求市场"副标题"需求源头，决定行业景气度"内含三个应用场景(数据通信服务器图标、电信通信5G基站图标、新兴场景汽车火箭图标), 各层之间用弯曲箭头连接
```

**图7 竞争格局**：
```
content: 顶部大标题"竞争格局：龙头效应显著，国产替代加速", 第一区珊瑚粉卡片"全球层面：寡头垄断 中国追赶"左侧海外巨头图标右侧中国国旗火箭图标, 第二区薄荷绿卡片"中国层面：梯队布局"内含第一梯队特征(800G量产能力、LPO技术领先、全产业链覆盖)和第二梯队特征(XPO/NPO技术突破、光引擎核心供应), 第三区柔黄色卡片"国产化进程：黄金替代期"三个柱状图标(10G及以下>90%、25G/100G约60%、>25G高速芯片&高端DSP<10%), 底部结论"核心技术国产化率仍极低，未来3-5年是黄金替代期"
```
