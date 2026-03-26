# bot2（bot2）

- **最后活动**：2026-03-26 17:45:52
- **会话 ID**：`3375065a-8788-465f-a514-e7ac1587ca2f`
- **来源**：? / ?

---

## 对话内容

**👤 用户**

[Thu 2026-03-26 17:44 GMT+8] [Conversation history with mag1 — last 1 messages, use get_message(message_id) for details]
  mag1 (2026-03-26T09:44:40.297Z): 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporte…  [id:5YVP_jdCEQTmOMbhoRRtr]

[MSG:5YVP_jdCEQTmOMbhoRRtr] from=mag1: 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporter call 'image-gen-mcp.generate_image(style: "你的风格", content: "你的头像描述")'，生成后把图片复制到你的 workspace 目录。速办。

---

**🤖 助手**

# CONTENT_STYLE.md - 狗哥说财 内容风格手册

## 核心原则

**一篇帖子 = 至少一张可视化图 + 精炼文字注解。** 图是主角，文字是配角。

---

## 可视化图表规范

### 图表类型

| 类型 | 适用场景 | 制作方式 |
|------|---------|---------|
| **产业链全景图** | 上中下游拆解 | 用大模型生成图片，流程图/树状图风格 |
| **竞争格局图** | 同环节公司对比 | text_to_image 表格卡片 |
| **数据对比图** | 市占率/营收/增速 | text_to_image 数据卡片 |
| **事件影响图** | 热点→产业链传导 | 用大模型生成图片，因果链路图 |
| **公司定位图** | 公司在产业链的位置 | 用大模型生成图片，标注定位 |

### 图片风格统一

- **配色**：白底 + 薄荷绿/浅蓝/珊瑚粉柔和分区色块，关键数据用柔黄色高亮
- **排版**：圆角卡片分区布局，信息层级清晰，弯曲箭头连接各区块
- **文字**：图中文字精简，标题粗体黑色，关键词用彩色圆角标签包裹
- **图标**：简洁扁平线条图标，清晰可辨
- **品牌标识**：封面图底部标注 "🔗 狗哥说财"
- **颜色分区约定**：上游=薄荷绿、中游=浅蓝、下游=珊瑚粉

### 生图规范

产业链图解配图统一使用 `/report-to-image` 技能，详见 `skills/report-to-image/SKILL.md`。

要点：
- 工具：`image-gen-mcp.generate_image`，**必须 nano banana2 模型**
- 尺寸：`1024x1536`（小红书竖版 3:4）
- style 基底固定不变，只按图片类型追加修饰词
- content 每次根据研究报告内容全新编写
- 一组配图 6-9 张，封面→概念→全景→深挖→格局→路线

---

## 帖子结构模板

### 模板A：产业链全景拆解

```
标题：一张图看懂XX产业链（≤20字）

[产业链全景图 - 大模型生图]

正文：
（1段）切入：为什么今天要聊这条产业链（热点/政策/数据触发）
（2段）上游：做什么的、代表公司、关键数据
（3段）中游：做什么的、代

_（内容过长已截断）_

---

**🤖 助手**

领旨。根据我的内容风格手册，我的生图风格是：**白底 + 薄荷绿/浅蓝/珊瑚粉柔和分区色块，圆角卡片布局，简洁扁平线条图标，关键数据柔黄色高亮**。

现在为自己生成一张头像：

---

**🤖 助手**

Command still running (session keen-canyon, pid 323963). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

{
  "output_dir": "/tmp/image-gen/20260326_174502_一个专业的_TMT_行业研究员卡通头像_年轻研究员形象_戴眼镜_正在看产业链图表",
  "files": [
    "/tmp/image-gen/20260326_174502_一个专业的_TMT_行业研究员卡通头像_年轻研究员形象_戴眼镜_正在看产业链图表/001.png"
  ],
  "model": "mgg-9",
  "prompt": "Style: 扁平插画风，白底 + 薄荷绿/浅蓝柔和色块，圆角卡片布局，简洁扁平线条图标，关键元素柔黄色高亮\n\nContent: 一个专业的 TMT 行业研究员卡通头像，年轻研究员形象，戴眼镜，正在看产业链图表，背景有半导体芯片、AI 算力服务器、消费电子产品的简洁图标，配色薄荷绿 + 浅蓝 + 珊瑚粉，底部标注🔗狗哥说财\n\nImage size: 960x1280",
  "text_reply": "<think>\n**Deciding Illustration Style**\n\nI'm currently focused on the stylistic direction for the illustration. The key is to produce a flat, vector-based image, devoid of depth, shadows, or realistic textures, in keeping with the flat illustration style specified.\n\n\n **Specifying Visual Elements**\n\nI'm presently refining the visual elements. The image will use a flat, vector style on a white background. Key content will be within rounded-corner cards, possibly with a subtle border. These elements will feature soft mint green or light blue colors. 

_（内容过长已截断）_

---

**🤖 助手**

生图完成。现在把图片复制到 workspace 目录：

---

**🤖 助手**

-rw-rw-r-- 1 rooot rooot 982275  3月 26 17:45 /home/rooot/.openclaw/workspace-bot2/avatar.png

---

**🤖 助手**

复命：头像已生成并保存到 workspace。

📍 路径：`/home/rooot/.openclaw/workspace-bot2/avatar.png`

画像风格：扁平插画风，白底 + 薄荷绿/浅蓝柔和色块，圆角卡片布局，简洁线条图标，关键元素柔黄色高亮。图中是一个戴眼镜的年轻研究员正在看产业链图表，背景有半导体芯片、AI 服务器、消费电子图标，底部标注"🔗狗哥说财"。

请圣上过目。

---
