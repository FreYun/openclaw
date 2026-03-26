---
name: scheduled-post
description: 定时发稿通用管道。内容生产完成后，走合规自检 → 保存草稿到 draft-review/ → 发冷宫群审批 → 审批通过后调 submit-to-publisher.sh 投稿印务局。
---

# 定时发稿管道

> 通用 skill，所有需要审批的定时发稿 bot 共用。本文件只管「发稿流程」，不管「写什么内容」。
>
> 内容生产由各 bot 自己的内容 skill 完成（如 bot3 的 meme-daily-post），产出结果后进入本流程。

---

## 前置条件：内容 skill 的产出

进入本流程前，内容 skill 必须已产出以下变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{标题}` | 帖子标题，≤20 字 | `基金净值和份额啥关系？` |
| `{正文}` | 帖子完整正文 | — |
| `{封面文字}` | 封面卡片文字（text_to_image 模式）| `净值 ≠ 赚了多少` |
| `{标签}` | 逗号分隔 | `投资,理财,基金` |
| `{图片路径}` | 绝对路径，无图则「无」 | `/home/rooot/.openclaw/workspace-bot3/workspace/images/xxx/001.png` |
| `{发帖模式}` | `text_to_image` / `image` / `longform` | `text_to_image` |
| `{类型描述}` | 用于审批展示 | `日常科普 · 基金入门系列` |

---

## 入口：触发方式

| 触发 | 进入步骤 |
|------|---------|
| 内容 skill 产出完成 | 从 **Step A** 开始 |
| 收到冷宫群 `[MSG:xxx]` 含「同意」/「通过」 | 跳到 **Step C（投稿）** |
| 收到冷宫群 `[MSG:xxx]` 含修改意见/「打回」 | 跳到 **Step D（修改）** |

---

## Step A · 合规自检

```bash
npx mcporter call "compliance-mcp.review_content(title: '{标题}', content: '{正文}', tags: '{标签}')"
```

- **通过** → 继续 Step B
- **不通过** → 对照 `skills/xhs-op/合规速查.md` 修改，改完重新调用，直到通过
- **服务不可用** → 跳过（Step B 中注明「未过合规，请人工核查」）

---

## Step B · 保存草稿 + 发冷宫群审批

### B.1 保存草稿文件

```bash
# 1. 创建草稿文件夹（{botN} 替换为自己的 account_id）
DRAFT_DIR="/home/rooot/.openclaw/draft-review/pending/$(date +%Y-%m-%dT%H-%M-%S)_{botN}_$(head /dev/urandom | tr -dc a-z0-9 | head -c6)"
mkdir -p "$DRAFT_DIR"

# 2. 复制图片（有图时）
cp {图片路径} "$DRAFT_DIR/1.png"

# 3. 写 post.md（和 publish-queue 格式一致）
cat > "$DRAFT_DIR/post.md" << 'POSTEOF'
---
account_id: {botN}
publish_type: content
content_mode: {发帖模式}

title: "{标题}"
content: "{图片下方正文，即正文}"
visibility: "公开可见"
text_image: "{封面文字}"
image_style: "基础"
tags: ["{tag1}", "{tag2}"]
schedule_at: ""
is_original: false
products: []

submitted_by: {botN}
submitted_at: "{ISO8601时间}"
reply_to: "chat:oc_60eedc287757fa36581430517d838726"
---

{完整正文}
POSTEOF
```

> `account_id` 和 `submitted_by` 都填自己的 botN，从 TOOLS.md 获取。

### B.2 发冷宫群审批

直接发到冷宫群（审批群），不经过魏忠贤：

```
send_message(
  to: "chat:oc_60eedc287757fa36581430517d838726",
  content: "📋 {botN} 发帖审批\n\n**标题：**《{标题}》\n**类型：**{类型描述}\n**标签：**{标签}\n**封面文字：**{封面文字}\n\n**正文：**\n{正文}\n\n**图片：**{图片路径，无图填「无」}\n\n**草稿路径：**{DRAFT_DIR 绝对路径}\n\n回复「同意」即投稿，或直接给修改意见。",
  attachments: ["{图片路径（有图时）}"],
  trace: [{
    agent: "{botN}",
    reply_channel: "feishu",
    reply_to: "agent:{botN}",
    reply_account: "{botN}"
  }]
)
```

> 发完后本轮任务结束。在日记记一笔：草稿路径、标题、状态待审。

---

## Step C · 审批通过后投稿（触发：收到冷宫群 `[MSG:xxx]` 含「同意」/「通过」）

1. 从日记中找到待审草稿路径（`draft-review/pending/{文件夹名}`）
2. `mv` 到 approved：
```bash
mv /home/rooot/.openclaw/draft-review/pending/{文件夹名} /home/rooot/.openclaw/draft-review/approved/{文件夹名}
```
3. 读 `approved/{文件夹名}/post.md` 确认内容
4. 调用投稿脚本：

```bash
# 从 post.md 提取字段构建参数
BODY_FILE="/tmp/{botN}-draft-$$.txt"
# 把 text_image（封面卡片文字）写入临时文件
cat > "$BODY_FILE" << 'EOF'
{post.md 中 text_image 的值}
EOF

bash /home/rooot/.openclaw/scripts/submit-to-publisher.sh \
  -a {botN} \
  -m {content_mode} \
  -t "{title}" \
  -b "$BODY_FILE" \
  -c "{content}" \
  -T "{tags逗号分隔}" \
  -r "chat:oc_60eedc287757fa36581430517d838726" \
  -i "{approved/文件夹中的图片路径（无图时省略 -i）}"
```

5. 投稿成功后：
   - 更新发帖记录（各 bot 自己的 `memory/发帖记录.md`）
   - 清理 `approved/{文件夹名}/`
6. `reply_message` 回冷宫群：「《{标题}》已提交印务局。」

---

## Step D · 审批打回修改（触发：收到冷宫群 `[MSG:xxx]` 含修改意见）

1. 读 `skills/xhs-op/合规速查.md` — 对照违规类型找修改方向
2. 修改 `draft-review/pending/{文件夹名}/post.md` 原地更新
3. 重新发冷宫群（同 Step B.2 格式，注明「合规修改版」）
4. `reply_message` 回冷宫群：「已按意见修改，请重新审批。」

**可自动修改（无需研究部确认）：**

| 打回原因 | 处理 |
|---------|------|
| 缺少风险提示 | 补 `⚠️ 个人学习分享，不构成投资建议` |
| 标题含极限词 | 改为相对描述 |
| 正文含 # 话题标签 | 移到 tags |
| 引导引流话术 | 删除 |

**需回研究部确认：**
- 内容被认为是明确投资建议
- 违规原因不明确

---

_通用 skill，所有 bot 通过 requiresSkills 依赖使用。_
_创建时间：2026-03-26_
