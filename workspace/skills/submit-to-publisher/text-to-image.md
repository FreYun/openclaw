# Text-to-Image Post

> **🚨 核心规则：`-b` 文件中的空行（`\n\n`）= 分割线，每段生成一张独立的图片卡片！**
> - 想要 **1 张图片** → `-b` 文件中**不要有空行**（所有文字连续写）
> - 想要 **2 张图片** → 用**一个空行**分成两段
> - 想要 **3 张图片** → 用**两个空行**分成三段（最多 3 张）
> - **常见错误**：把多个段落用空行隔开，结果生成了多张图片而不是预期的一张

> **🚨 `-b` 和 `-c` 都是必填项，缺一不可！**
> - **`-b` (body file)** = 卡片上的文字 (`text_content`)。用**空行**分隔不同卡片，最多 3 张。
> - **`-c` (parameter)** = 图片下方的正文 (`content`)。通常是总结、互动引导、或补充说明。
> - **漏掉 `-c` 会直接报错，无法提交。** 两者内容必须不同：卡片是核心观点，正文是补充讨论。

```bash
cat > /tmp/post_body_$$.txt << 'BODYEOF'
First card content
3-6 lines ideal, include key points + data

Second card content
Continue the narrative; blank line = new card

Third card (optional)
Summary + engagement hook
BODYEOF

folder=$(bash ~/.openclaw/scripts/submit-to-publisher.sh \
  -a bot7 -t "标题" -b /tmp/post_body_$$.txt \
  -m text_to_image -r "direct:ou_xxx" \
  -T "A股,投资" \
  -s "基础" \
  -c "Body text below images, different from card text. E.g.: 你怎么看？欢迎评论区聊聊～")
echo "FOLDER: $folder"
```

`image_style` options: `基础` (default), `光影`, `涂写`, `书摘`, `涂鸦`, `便签`, `边框`, `手写`, `几何`
