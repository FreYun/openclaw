---
name: mp-cover-art
description: >
  公众号投资文章封面配图 Skill — 图解信息图风格，适配日复盘/深度分析/周复盘/轻松深度四种文章类型。
  与 mp-content-writer 配合，写完文章后自动推荐封面方案。
---

# 公众号配图生成 Skill（mp-cover-art）

> 装备即生效，写完公众号文章后按本文件推荐配图方案。

## 铁律

0. **每次生图必须先 Read 本文件** — 禁止凭记忆写 prompt，必须从本文件中复制 STYLE 模板，以文件内容为准。
1. **style 基底不要改** — 只追加布局描述词，保证系列一致感。
2. **先建议再生图** — 写完文章先推荐封面方案，研究部确认后才调用生图 MCP。
3. **横版 1536x1024** — 公众号封面比例，不要用竖版。
4. **banana2 模型** — 必须用 banana2，中文渲染准确（banana 会乱码）。
5. **合规** — 配图不得出现个股名称、代码、目标价、荐股表述。用"行业龙头""第一梯队"等泛化表述。
6. **生成后必须展示** — 图片生成后必须发给研究部查看，不能生成完就跳过，等研究部确认满意后才保存。
7. **效果好的 prompt 记录到 `memory/好用的图片prompt.md`** 方便复用。

---

## 一、STYLE 基底（固定，直接复制）

```
hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout
```

### 色彩体系

根据文章主题和产业方向选用不同的**强调色**，追加到 style 末尾：

| 主题方向 | 强调色追加词 | 适用场景 |
|---------|------------|---------|
| **通用/市场** | `, golden yellow accent highlights, earth tone palette (cream, gold, olive green, warm brown, steel blue)` | 日复盘、周复盘（无特定产业主题） |
| **锂电/新能源** | `, fresh green accent highlights, energy palette (cream, lime green, forest green, warm brown, electric yellow)` | 锂电池、新能源车、光伏相关 |
| **存储/芯片** | `, cool blue accent highlights, tech palette (cream, ice blue, steel blue, slate gray, electric cyan)` | 存储芯片、半导体、AI 算力 |
| **航天/军工** | `, deep indigo accent highlights, aerospace palette (cream, navy blue, silver gray, warm brown, star white)` | 航天、军工、卫星 |
| **能化/化工** | `, warm amber accent highlights, chemistry palette (cream, amber, olive green, warm brown, burnt orange)` | 能源化工、原材料、大宗商品 |
| **上涨/利好** | `, warm red-gold accent highlights, bullish palette (cream, champagne gold, warm red, amber)` | 大涨行情、利好解读 |
| **下跌/风险** | `, muted green-gray accent highlights, cautious palette (cream, sage green, cool gray, warm brown)` | 下跌行情、风险提示 |

---

## 二、文章类型模板

### A. 日复盘封面

> 每日固定格式，强调**今日核心信号 + 市场情绪**，让读者一眼抓住重点。

**style（复制基底 + 追加）：**
```
hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, {色彩体系}, daily market review cover, left-right split layout
```

**content 写法：**
```
左侧区域占60%: 顶部大标题黑色粗体中文"{文章标题}", 标题下方小字标签"{日期} 复盘", 中部1-2个手绘插画描述当日核心主题({主题插画描述}), 右侧区域占40%: 三个竖排数据卡片, 第一个卡片"{指数名}{涨跌幅}", 第二个卡片"成交额 {金额}", 第三个卡片"{情绪关键词}", 卡片之间用虚线连接, 底部细线分隔, 小字"投资有风险 入市需谨慎"
```

**主题插画速查：**

| 当日主题 | 插画描述 |
|---------|---------|
| 科技/AI | `芯片电路板与数据流线条, 小型服务器机架剪影` |
| 消费/内需 | `购物车与向上箭头, 商业街剪影` |
| 新能源 | `电池与闪电符号, 风力发电机剪影` |
| 大宗商品 | `油桶与价格曲线, 工厂烟囱剪影` |
| 政策驱动 | `文件卷轴与印章, 向上阶梯` |
| 资金博弈 | `天平两端的多空力量, 资金流向箭头` |
| 情绪修复 | `破碎后重新拼合的心形, 向上的嫩芽` |
| 滞胀/衰退 | `被锁链缠绕的齿轮, 沙漏与下行曲线` |
| 缩量震荡 | `水面微波纹, 横向来回的钟摆` |
| 突破/放量 | `打破玻璃天花板的拳头, 火箭升空轨迹` |

---

### B. 深度分析封面

> 突出**研究深度感**，中央大主题插画 + 标题，视觉冲击力强。

**style（复制基底 + 追加）：**
```
hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, {色彩体系}, deep analysis cover, centered hero illustration layout
```

**content 写法：**
```
中央大幅手绘插画({产业/主题核心视觉}), 占画面60%, 插画上方居中大标题黑色粗体中文"{文章标题}", 标题下方小字副标题"{副标题/一句话核心观点}", 插画左右两侧各1-2个浮动标签卡片({关键数据或关键词}), 底部装饰线与小字来源标注
```

**产业核心视觉速查：**

| 产业 | 中央插画描述 |
|------|------------|
| 锂电池 | `巨大的电池单体剖面图, 内部可见正负极材料层, 电解液流动, 电子轨迹线条` |
| 存储芯片 | `放大的晶圆芯片俯视图, 内部电路微缩城市景观, 数据流光带` |
| 航天 | `火箭发射场全景, 控制台与轨道线, 卫星环绕地球` |
| 能源化工 | `化工厂装置剖面, 分子结构模型, 管道流程图` |
| 光伏 | `太阳能板阵列透视, 光线折射路径, 电网连接` |
| 新能源车 | `电动车透视底盘, 三电系统标注, 充电桩网络` |
| 半导体设备 | `光刻机侧面剖视, 晶圆传送带, 洁净室场景` |
| 宏观经济 | `经济仪表盘, 多个表盘显示CPI/PPI/PMI, 中央大指针` |
| 行业对比 | `天平或擂台, 两侧代表不同公司/路线的符号对峙` |

---

### C. 周复盘封面

> 固定栏目感，**仪表盘风格**，数据密度高但清晰有序。

**style（复制基底 + 追加）：**
```
hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, golden yellow accent highlights, earth tone palette (cream, gold, olive green, warm brown, steel blue), weekly review dashboard cover, grid data card layout
```

**content 写法（格式固定）：**
```
顶部横幅: 大标题黑色粗体中文"周复盘 | 第{N}期", 副标题"{本周关键词}", 中部2x2网格四个数据卡片: 左上卡片"沪指 {涨跌幅}" 配迷你折线图, 右上卡片"创业板 {涨跌幅}" 配迷你折线图, 左下卡片"成交额 {周均}" 配迷你柱状图, 右下卡片"市场温度 {温度值}" 配温度计图标, 底部一行三个小标签: "{领涨板块}" "{领跌板块}" "{下周关注}", 装饰: 细线网格背景纹理, 仪表盘风格圆角边框
```

---

### D. 轻松深度封面

> **故事感 + 隐喻**，用一个核心比喻画面吸引点击，最有创意空间的类型。

**style（复制基底 + 追加）：**
```
hand-drawn editorial infographic, horizontal 3:2 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, WeChat article cover layout, {色彩体系}, editorial story cover, metaphor illustration centered layout
```

**content 写法：**
```
中央大幅比喻插画({从文章核心比喻提取的视觉场景}), 占画面70%, 插画上方或下方大标题黑色粗体中文"{文章标题}", 画面边缘散落2-3个小图标暗示文章涉及的投资概念({相关小图标}), 整体氛围{情绪氛围词}
```

**常见比喻→插画速查：**

| 文章比喻 | 插画描述 | 氛围 |
|---------|---------|------|
| 潮水退去 | `海滩退潮露出各种搁浅的小船, 远处有一艘大船仍在航行` | `calm contemplative` |
| 赌桌博弈 | `圆形牌桌, 筹码堆叠, 扑克牌显示经济指标, 多双手出牌` | `tense dramatic` |
| 过山车 | `过山车轨道勾勒出K线走势, 乘客表情各异(兴奋/恐惧/淡定)` | `dynamic playful` |
| 厨房做菜 | `厨师在大锅中翻炒各种"食材"(标注为不同资产), 调料瓶标注"政策""利率"` | `warm humorous` |
| 天气预报 | `气象站大屏显示市场"天气", 不同区域晴雨不同, 预报员指着地图` | `informative lighthearted` |
| 健身房 | `各种器械标注不同板块, 有的在举重(强势), 有的躺平(弱势)` | `energetic witty` |
| 医院体检 | `体检报告单, 各项指标红绿灯, 医生拿着听诊器听"市场心跳"` | `analytical humorous` |
| 航海探险 | `大航海地图, 标注各个"岛屿"(板块), 罗盘指向某方向` | `adventurous curious` |

---

## 三、文中配图模板（可选）

深度分析和轻松深度类文章可能需要文中插图，用于拆解复杂逻辑。

### E. 产业链/传导链图

**style：**
```
hand-drawn editorial infographic, vertical 3:4 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, {色彩体系}, supply chain flow diagram, vertical three-tier layout
```

**content 写法：**
```
顶部标题黑色粗体中文"{产业链/传导链标题}", 三层结构从上到下: 上游区域({上游色调}色边框圆角卡片): {上游环节描述}, 中游区域({中游色调}色边框圆角卡片): {中游环节描述}, 下游区域({下游色调}色边框圆角卡片): {下游环节描述}, 各层之间用粗箭头连接, 箭头旁标注传导逻辑"{传导关系}", 竖版1024x1536
```

### F. 数据对比卡片

**style：**
```
hand-drawn editorial infographic, vertical 3:4 ratio, warm cream beige paper background with subtle texture, bold black ink illustration style, clean line art with flat muted color fills, professional financial education aesthetic, {色彩体系}, data comparison card, versus split layout
```

**content 写法：**
```
顶部标题黑色粗体中文"{对比主题}", 画面一分为二: 左侧({左侧色调}色背景): "{对象A名称}" 大字, 下方3-4个数据行({具体数据}), 底部小图标, 右侧({右侧色调}色背景): "{对象B名称}" 大字, 下方3-4个数据行({具体数据}), 底部小图标, 中间VS标志, 底部总结栏一句话点评, 竖版1024x1536
```

---

## 四、配图流程

### 写完文章后推荐封面

```
🖼️ 封面配图建议：
- 文章类型：{日复盘/深度分析/周复盘/轻松深度}
- 封面模板：{A/B/C/D}
- 标题文字：「{标题}」
- 色彩方向：{从色彩体系选}
- 核心视觉：{一句话描述中央插画}
- 是否需要文中配图：{是/否，如是列出建议}
```

### 研究部确认后调用生图

**封面图（横版）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制对应模板的 style}",
  content: "{按模板 content 写法填写}",
  size: "1536x1024",
  model: "banana2"
)'
```

**文中配图（竖版）：**
```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "{复制 E/F 模板的 style}",
  content: "{按模板 content 写法填写}",
  size: "1024x1536",
  model: "banana2"
)'
```

---

## 五、与 mp-content-writer 的衔接

mp-content-writer 的 Step 7（交付与发布）结束后，自动进入配图流程：

1. **分析文章** — 识别文章类型、核心主题、产业方向、情绪基调
2. **选择模板** — 根据文章类型选 A/B/C/D
3. **推荐方案** — 输出封面建议（见上方格式）
4. **等待确认** — 研究部确认或修改
5. **生成配图** — 调用 image-gen-mcp
6. **展示给研究部** — 生成后**必须**将图片发给研究部查看，等待反馈（满意/重做/微调）
7. **保存** — 研究部满意后，保存到工作空间并发图：
   ```bash
   DEST="workspace/images/cover/YYYY-MM-DD"
   mkdir -p "$DEST"
   cp /tmp/image-gen/xxx.png "$DEST/公众号封面_{主题关键词}.png"
   ```
   - 将图片通过当前会话发给研究部（飞书直接发图片文件）
   - **不要只回复"已生成"或告知路径 — 必须把图片发过去**

---

_bot11 公众号配图能力，图解信息图风格，与 mp-content-writer 配合使用。_
