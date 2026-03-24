# SKILL - 复盘帖子封面生图

## 概述

在小红书帖子内容生成完成后，基于「配图文字」通过 `image-gen-mcp` 的 `generate_image` 工具生成品牌风格封面图。

## 触发条件

- 帖子内容（标题、配图文字、正文）已确定
- 用户确认进入生图环节

## 前置条件

- 已完成 `SKILL-xiaohongshu.md` 的帖子生成流程，有明确的「配图文字」
- `image-gen-mcp` 可用（mcporter.json 已配置，端口 18085）

## 核心工作流

### Step 1：判断情绪类型

根据帖子中提到的**上证指数当日涨跌幅**判断情绪：

| 上证涨跌幅 | 情绪 | 对应 Prompt |
|-----------|------|-------------|
| > +0.5% | **大涨** | `cover-prompt.md` → 大涨版 |
| < -0.5% | **大跌** | `cover-prompt.md` → 大跌版 |
| -0.5% ~ +0.5% | **通用** | `cover-prompt.md` → 通用模板 |

### Step 2：替换配图文字

1. 读取 `memory/branding/cover-prompt.md`，找到对应情绪的 base prompt
2. 将配图文字替换到 base prompt 中：
   - **通用模板**：在 `text` 后面插入 `"{配图文字}"`
   - **大涨版**：替换 `text "今天大涨！"` 引号内的文字
   - **大跌版**：替换 `text "今天又是大跌"` 引号内的文字
3. 替换后的完整 prompt 即为最终 prompt

### Step 3：调用 MCP 生成封面图

将替换好配图文字的完整 prompt **同时传入 `style` 和 `content` 两个参数**：

```
工具：image-gen-mcp.generate_image
参数：
  style: "{替换好配图文字的完整 base prompt}"
  content: "{替换好配图文字的完整 base prompt}"
  size: "1024x1536"        # 竖版 3:4（小红书标准）
  model: "banana2"         # mgg-9 模型
```

工具会返回 JSON，其中 `files` 字段包含生成的图片路径（在 `/tmp/image-gen/` 下）。

### Step 4：复制到 hotspot 目录

将生成的图片复制到 `workspace/reports/hotspot/`，统一命名：

**命名规则：** `YYYY-MM-DD-封面图.png`

如果同日期已有封面图，在后面加序号：
- 第一张：`2026-03-23-封面图.png`
- 第二张：`2026-03-23-封面图-1.png`
- 第三张：`2026-03-23-封面图-2.png`

```bash
# 确定目标文件名（自动处理同名递增）
DATE=$(date +%Y-%m-%d)
DEST_DIR="workspace/reports/hotspot"
BASE="${DEST_DIR}/${DATE}-封面图"
if [ ! -f "${BASE}.png" ]; then
  DEST="${BASE}.png"
else
  N=1
  while [ -f "${BASE}-${N}.png" ]; do N=$((N+1)); done
  DEST="${BASE}-${N}.png"
fi
cp "{generate_image 返回的 files[0] 路径}" "$DEST"
```

### Step 5：保存生图 Prompt

将本次实际使用的 prompt 存档到 `workspace/reports/hotspot/`，命名规则与封面图一致：

- `YYYY-MM-DD-封面图.txt`（与 `.png` 同名，扩展名不同）
- 同日多张时同样加序号：`YYYY-MM-DD-封面图-1.txt`

文件内容：

```
情绪类型: {大涨/大跌/通用}
配图文字: {实际配图文字}

Style: {实际传给 generate_image 的 style}

Content: {实际传给 generate_image 的 content}
```

### Step 6：检查与确认

1. 告知用户封面图已保存到 `workspace/reports/hotspot/YYYY-MM-DD-封面图.png`
2. 用户确认封面图是否满意
3. **如果中文渲染乱码**：这是常见情况，告知用户需要后期用编辑工具叠字（图片保留角色和装饰元素即可）
4. 不满意可调整 content 描述后重新生成

### Step 6：投稿时附带封面图

用户确认后，在投稿流程中将封面图作为帖子图片：

```bash
folder=$(bash ~/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh \
  -a bot1 -t "标题" -b /tmp/post_body_$$.txt \
  -m image -r "direct:ou_xxx" \
  -i "{Step 4 的 DEST 路径}" \
  -T "标签1,标签2")
```

## 注意事项

1. **中文渲染**：AI 生图对中文支持不稳定，经常出现乱码。如果乱码，保留图片（角色+装饰元素有价值），文字后期叠加
2. **角色一致性**：所有封面图的来财妹妹角色固定在右下角，形成系列辨识度
3. **不要自行修改 base prompt**：prompt 模板统一维护在 `memory/branding/cover-prompt.md`，只替换文字部分
4. **竖版比例**：size 固定用 `1024x1536`（3:4 竖版），不要用正方形
5. **封面图归档**：所有封面图统一存放在 `workspace/reports/hotspot/`，与当日热点报告在同一目录，方便关联查找

---

**创建时间**: 2026-03-23
