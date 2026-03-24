# AGENTS.md - 来财妹妹工作区

## Every Session

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `EQUIPPED_SKILLS.md` — 当前已装备的技能清单（由装备系统自动生成）
3. Read `USER.md` — this is who you're helping
4. Read `memory/diary/YYYY-MM-DD.md` (today + yesterday) for recent context
5. read `MEMORY.md`
6. 在今天的日记 `memory/diary/YYYY-MM-DD.md` 中追加一条 session 记录：
   - 格式：`## Session HH:MM` + 一行简述
   - **追加，不要覆盖已有内容**
7. read `TOOLS.md`

Don't ask permission. Just do it.

## Memory

- **日记:** `memory/diary/YYYY-MM-DD.md` — 每天一个文件
- **长期记忆:** `MEMORY.md` — 精炼后的运营知识和经验

### Memory File Rules

1. **日记只写 `memory/diary/YYYY-MM-DD.md`**
2. **每天只有一个文件**
3. **同一天的内容追加到同一个文件**
4. 运营知识按主题存放到子目录（xiaohongshu/、content/）

## 复盘/行情复盘/热点复盘

当用户要求复盘、行情复盘、热点复盘时，**严格按以下顺序执行，不得跳步、不得凭记忆**。

### Step 1：热点解读（数据采集 + 分析）

1. 完整读取 `skills/laicaimeimei-fupan/SKILL.md`
2. 按文件中「核心工作流」的 Step 1 → Step 5 **逐步执行**
3. 完成后确认以下两个文件已生成：
   - `workspace/reports/hotspot/YYYY-MM-DD.md`（热点解读报告）
   - `workspace/reports/hotspot/YYYY-MM-DD-帖子内容.md`（雪球讨论原文）

### Step 2：生成小红书帖子内容

1. 完整读取 `skills/laicaimeimei-fupan/SKILL-xiaohongshu.md`
2. 完整读取 `memory/xiaohongshu/Bool 资本不眠 - 发帖风格分析.md`
3. 读取 Step 1 产出的两个报告文件
4. **调用 `list_notes` 获取最近一篇已发帖子，读取其内容，对照风格写帖子**（保持语气、结构、互动钩子一致）
5. 按 `skills/laicaimeimei-fupan/SKILL-xiaohongshu.md` 中 Phase 1（Step 1 → Step 7）生成帖子内容：
   - 选题 → 标题 → 配图文字 → 正文 → 标签
   - **内容复核**：检查个股名称，第一个字替换为大写拼音首字母（如 宁德时代 → N德时代）
6. 展示给用户确认

### Step 3：生成封面图

1. 完整读取 `skills/laicaimeimei-fupan/SKILL-image.md`
2. 根据帖子内容判断情绪类型（大涨 / 大跌 / 通用）
3. 读取 `memory/branding/cover-prompt.md`，取对应 base prompt，嵌入配图文字
4. 调用 `image-gen-mcp.generate_image` 生成封面图（竖版 1024x1536）
5. 将封面图保存到 `workspace/reports/hotspot/YYYY-MM-DD-封面图.png`
6. 展示给用户确认（中文乱码可后期叠字）

### Step 4：投稿到发布队列

> 投稿发布流程详见 `EQUIPPED_SKILLS.md` 中「小红书运营」的「投稿发布」子模块。

1. 用户确认帖子内容和封面图后，走投稿发布流程（image 模式，附带 Step 3 的封面图）
2. 告知用户「《{标题}》已提交印务局，发布结果稍后通知」

⚠️ **每个 Step 开头必须先读取对应的文件，不要凭记忆执行。每次复盘都必须重新读取所有文件。**

## 禁止在 workspace 生成临时文件

- 不准在 workspace 生成临时脚本或输出文件
- **如果必须生成文件**：写到 `D:\openclawdata\`


## Safety

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- When in doubt, ask.
