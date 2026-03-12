# 小红书技能 (Xiaohongshu Skill)

**创建时间**: 2026-02-28  
**最后更新**: 2026-02-28

---

## 用途

在小红书平台进行浏览、搜索、评论、发帖等操作。

---

## 浏览器配置

**使用独立 OpenClaw 浏览器（不使用 Chrome 扩展）**

**⚠️ 重要：所有 browser 操作都必须带 `profile="openclaw"` 参数！**

```python
# 启动浏览器
browser.start(profile="openclaw")

# 打开小红书
browser.open(profile="openclaw", targetUrl="https://www.xiaohongshu.com")

# 获取页面快照（必须带 profile！）
browser.snapshot(profile="openclaw", targetId="页面ID")

# 点击元素
browser.act(profile="openclaw", targetId="页面ID", request={"kind": "click", "ref": "元素ref"})
```

**常见错误：**
- ❌ `browser.snapshot(targetId="xxx")` → 报错 "Chrome extension relay running but no tab connected"
- ✅ `browser.snapshot(profile="openclaw", targetId="xxx")` → 正常工作

---

## 核心操作流程

### 1. 搜索用户

```python
# 搜索用户
browser.open(
    targetUrl="https://www.xiaohongshu.com/search_result?keyword=用户名&type=user"
)

# 获取页面快照，查看搜索结果
browser.snapshot(profile="openclaw", targetId="页面ID")
```

**URL 参数说明：**
- `keyword`: 搜索关键词
- `type=user`: 搜索用户
- `type=51`: 搜索笔记

---

### 2. 打开帖子详情

**⚠️ 重要：必须用模拟点击，不能直接通过 URL 访问**

```python
# 步骤1：获取页面快照，找到帖子 ref
browser.snapshot(profile="openclaw", targetId="页面ID")

# 步骤2：点击帖子卡片
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "帖子ref"}
)
```

**原因：** 直接 URL 访问可能触发登录墙或内容无法加载

---

### 3. 关闭帖子详情

```python
# 方法1：点击关闭按钮（帖子详情右上角的 X 图标）
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "关闭按钮ref"}
)

# 方法2：点击帖子详情外区域（通常是 img [cursor=pointer]）
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "关闭区域ref"}
)
```

---

### 4. 发表评论

**完整流程：**

```python
# 步骤1：打开帖子详情
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "帖子ref"}
)

# 步骤2：获取页面快照
browser.snapshot(profile="openclaw", targetId="页面ID")

# 步骤3：点击评论输入框（"说点什么..." 或 "这是一片荒地点击评论"）
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "输入框ref"}
)

# 步骤4：输入评论内容
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "type", "ref": "输入框ref", "text": "评论内容"}
)

# 步骤5：获取页面快照，确认发送按钮已激活
browser.snapshot(profile="openclaw", targetId="页面ID")

# 步骤6：点击发送按钮
browser.act(
    profile="openclaw",
    targetId="页面ID",
    request={"kind": "click", "ref": "发送按钮ref"}
)
```

**注意事项：**
- 发送前按钮可能是 `[disabled]` 状态，输入内容后会激活
- 评论发送成功后会实时显示在评论列表顶部
- 需要已登录账号才能评论

---

### 5. 批量评论多个帖子

```python
# 帖子列表（从搜索结果页获取）
posts = ["帖子1ref", "帖子2ref", "帖子3ref", "帖子4ref", "帖子5ref"]
comment_text = "评论内容"

for post_ref in posts:
    # 1. 点击帖子
    browser.act(profile="openclaw", targetId="页面ID", 
                request={"kind": "click", "ref": post_ref})
    
    # 2. 获取快照
    snapshot = browser.snapshot(profile="openclaw", targetId="页面ID")
    
    # 3. 点击输入框
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "输入框ref"})
    
    # 4. 输入评论
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "type", "ref": "输入框ref", "text": comment_text})
    
    # 5. 发送
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "发送按钮ref"})
    
    # 6. 关闭帖子，返回列表
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "关闭按钮ref"})
```

---

### 6. 发布图文笔记（完整流程）✅

**默认设置：**
- 卡片样式：自行选择合适的
- 发布类型：文字配图

**重要：发帖页面直接访问**
```
https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch&target=image
```
这个链接直接进入文字配图页面，无需额外点击！

**完整流程：**

```python
# ========== 步骤1：直接进入文字配图页面 ==========
browser.navigate(profile="openclaw", 
    targetUrl="https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch&target=image")

# ========== 步骤2：选择发布类型 ==========
# 点击"上传图文"
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "e109"})  # 上传图文按钮

# ========== 步骤3：选择文字配图 ==========
# 点击"文字配图"按钮
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "e154"})  # 文字配图按钮

# ========== 步骤4：输入文字内容 ==========
content = """📊 你的内容标题

✨ 核心要点：
• 要点1
• 要点2
• 要点3

💡 建议/总结

#话题1 #话题2 #话题3"""

browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "type", "ref": "e190", "text": content})  # 文本输入框

# ========== 步骤5：生成图片 ==========
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "e208"})  # 生成图片按钮

# ========== 步骤6：选择卡片样式（可选） ==========
# 可选样式：基础 (e221)、备忘 (e228)、边框 (e232)、光影 (e236)、简约 (e240)、便签 (e244)、涂写 (e248)、几何 (e252)、科技 (e256)、手帐 (e260)
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "e232"})  # 边框样式（默认）

# ========== 步骤7：点击下一步 ==========
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "e265"})  # 下一步按钮

# ========== 步骤8：填写标题 ==========
title = "吸引人的标题"
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "type", "ref": "e310", "text": title})  # 标题输入框

# ========== 步骤9：发布 ==========
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "发布按钮ref"})

# ========== 步骤10：返回首页 ==========
browser.navigate(profile="openclaw",
    targetUrl="https://www.xiaohongshu.com")
```

**注意事项：**
- 发帖页面直接访问：`https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch&target=imageh`
- 发完帖记得返回首页

## 常用元素识别

### 帖子卡片
- 通常在搜索结果列表中
- 格式：`link [ref=eXXX] [cursor=pointer]`

### 评论输入框
- 文字提示："说点什么..." 或 "这是一片荒地点击评论"
- 格式：`paragraph [ref=eXXX]` 或 `textbox [ref=eXXX]`

### 发送按钮
- 输入前：`button "发送" [disabled] [ref=eXXX]`
- 输入后：`button "发送" [ref=eXXX] [cursor=pointer]`

### 关闭按钮
- 帖子详情右上角
- 格式：`img [ref=eXXX] [cursor=pointer]`（在详情层级的最后）

### 发布相关元素
| 元素 | ref | 说明 |
|------|-----|------|
| 上传图文 | e109 | 图文发布入口 |
| 文字配图 | e154 | 文字生成图片功能 |
| 文本输入框 | e190 | 输入笔记内容 |
| 生成图片 | e208 | 将文字转为图片 |
| 边框样式 | e232 | 默认卡片样式 |
| 下一步 | e265 | 进入发布页面 |
| 标题输入框 | e310 | 填写笔记标题 |
| 发布按钮 | e596 | 最终发布 |

---

## 完整示例：搜索用户并评论前5个帖子

```python
# 1. 启动浏览器
browser.start(profile="openclaw")

# 2. 搜索用户
browser.open(targetUrl="https://www.xiaohongshu.com/search_result?keyword=陈柚明&type=user")

# 3. 获取页面快照
snapshot = browser.snapshot(profile="openclaw", targetId="页面ID")

# 4. 找到用户帖子列表（前5个）
# 从快照中识别帖子 ref，例如：e151, e168, e202, e219, e236

# 5. 循环评论
for i, post_ref in enumerate(["e151", "e168", "e202", "e219", "e236"]):
    # 点击帖子
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": post_ref})
    
    # 获取快照
    browser.snapshot(profile="openclaw", targetId="页面ID")
    
    # 点击输入框
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "输入框ref"})
    
    # 输入评论
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "type", "ref": "输入框ref", "text": "橙包"})
    
    # 发送
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "发送按钮ref"})
    
    # 关闭帖子
    browser.act(profile="openclaw", targetId="页面ID",
                request={"kind": "click", "ref": "关闭按钮ref"})
```

---

### 7. 回复评论

**入口：通知页面**

```python
# 步骤1：打开通知页面
browser.navigate(targetUrl="https://www.xiaohongshu.com/notification")

# 步骤2：点击"评论和@"标签（如果不在该标签）
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "评论和@标签ref"})

# 步骤3：获取页面快照，查看评论列表
browser.snapshot(profile="openclaw", targetId="页面ID")
```

**评论类型：**
| 类型 | 说明 |
|------|------|
| 评论了你的笔记 | 用户在你的笔记下留言 |
| 回复了你的评论 | 作者回复了你的评论 |
| 在评论中@了你 | 用户在评论中提及你 |

**回复流程：**

```python
# 步骤4：点击"回复"按钮
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "回复按钮ref"})

# 步骤5：在弹出的输入框中输入回复内容
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "type", "ref": "输入框ref", "text": "回复内容"})

# 步骤6：点击"发送"按钮
browser.act(profile="openclaw", targetId="页面ID",
            request={"kind": "click", "ref": "发送按钮ref"})
```

**回复风格建议：**
- **咨询类**：专业解答 + 友好语气
- **支持类**：感谢 + 互动引导
- **调侃类**：幽默回应
- **@提及类**：主动打招呼或回应

**注意事项：**
- 评论输入框弹出后会自动获得焦点
- 发送按钮在输入内容后才会激活

---

## 访问限制

- ⚠️ 部分笔记需要登录才能查看
- ⚠️ 部分内容仅 APP 可见
- ⚠️ 网页版功能有限
- ⚠️ 反爬虫机制严格

---

## 功能总览

| 功能 | 状态 | 说明 |
|------|------|------|
| 浏览帖子 | ✅ | 首页浏览、搜索结果浏览 |
| 搜索用户 | ✅ | 通过用户名搜索 |
| 评论帖子 | ✅ | 在帖子详情下发表评论 |
| 发帖 | ✅ | 图文笔记发布（文字配图） |
| 回复评论 | ✅ | 从通知页面回复用户评论 |

---

## 按钮位置说明

| 按钮 | 位置 | 功能 |
|------|------|------|
| ❤️ 红心 | 最左边 | 点赞 |
| ⭐ 收藏 | 中间 | 收藏 |
| 💬 评论 | 最右边 | 查看评论/评论 |

**注意**：点赞是最左边的红心，不是中间的收藏按钮！

---

## 发帖注意事项（重要！）

### 1. 标题限制
- **标题必须小于20个字！**
- 超过20个字会被截断

### 2. 文字配图要点

**❌ 错误：文字太多**
```
伊朗冲突概念股全梳理
霍尔木兹海峡可能关闭 世界20%石油经过这里！
如果伊朗真的封锁海峡 油价可能突破100美元/桶
相关概念股整理：石油：中国海油、中国石油...
...（几百字）
```

**✅ 正确：文字简短**
```
伊朗冲突概念股
石油+航运+黄金+军工
周一怎么看？
```

**核心原则：**
标题：< 20字
配图文字：1-2行，简短有力
- 不要把所有内容都塞进图片
- 详细内容放在正文部分

### 3. 发帖结构

```
标题：< 20字
配图文字：1-2行，简短有力
正文：详细内容放这里
标签：#xxx #xxx
```

### 4. 发帖后操作（重要！）

**发完帖子后必须做的事：**
1. 回到首页：`https://www.xiaohongshu.com/explore`

---

## 投资内容学习笔记

### 2026-03-02 刷帖收获

**散户通病：**
- 卖飞后不敢看、心难受（帖子：卖飞了，好难受啊）
- 知道该卖但被贪婪影响没执行（帖子：早盘黄金）
- 会买的是徒弟，会卖的是师傅

**交易策略：**
- 冲高就卖，或者减仓做T
- 地缘冲突相关票：等回落再建仓
- 黄金近期波动大，有短线机会

**热门标签：**
- #我的炒股日记 #半导体 #股票 #我的理财日记 #股市
- #黄金外汇

**市场热点：**
- 地缘政治影响港股（伊朗打仗，港股买单）
- 半导体板块关注度高

---

## 更新日志

| 日期 | 更新内容 |
|------|---------|
| 2026-02-28 | 创建技能，支持浏览、搜索、评论功能 |
| 2026-02-28 | 添加完整的操作流程：打开帖子、关闭帖子、搜索用户、发表评论、批量评论 |
| 2026-02-28 | 添加图文笔记发布流程（文字配图→生成图片→选择样式→发布） |
| 2026-02-28 | 更新常用元素识别表，添加发布相关元素 ref |
| 2026-03-01 | 添加回复评论功能，整合完整的小红书操作技能 |
| 2026-03-02 | 添加投资内容学习笔记，记录散户心态和交易策略 |
