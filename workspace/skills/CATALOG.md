# Skill Catalog

> 按装备系统 slot 类型分类，所有 skill 统一管理在 `workspace/skills/` 下。
> Bot 通过 symlink 引用，兼容 symlink 保持扁平路径可用。

## ⛑️ 工种 (Helm) (3)

| Skill | 名称 | 说明 |
|-------|------|------|
| `frontline` | 前台 | 面向公众的内容创作者：产出内容、运营账号、与读者互动 |
| `management` | 管理 | 全局管理者：监控所有 agent、调度任务、处理异常、审批变更 |
| `ops` | 内务 | 内部运维：基础设施管理、发布执行、研发支持，不面向公众 |

## 👔 职业 (Armor) (8)

| Skill | 名称 | 说明 |
|-------|------|------|
| `coder` | 全知全能-外挂（普通bot勿装) | 开发者职业 — 装备后解锁全部技能槽位，无数量上限 |
| `gzh-publish` | 公众号发文 | 微信公众号发文流程：登录、浏览器操作、排版、保存草稿、发表、留言互动 |
| `mag1-mgm` | 公公运营术 | 印务局全流程运营：agent 通讯调度、飞书群管理、发布结果上报、各 agent 职能速查 |
| `skill-evolution` | 技能进化师 | OpenSpace 驱动的 skill 沙盒进化、审批合并、日报播报 |
| `skill-standardize` | 技能标准化 | 将大文件 skill 拆分为主文件+子文件的标准结构，减少 token 消耗 |
| `xhs-browser-publish` | 小红书浏览器古法发布 | 使用浏览器发布小红书笔记（图文/视频/长文） |
| `xhs-op` | 小红书运营 | 小红书全流程运营：登录、浏览、互动、养号、选题、内容生成、投稿发布 |
| `xhs-pub` | 小红书发布中心 | 印务局专属：MCP 服务管理、端口健康监控、发布流水线执行 |

## 💍 风格 (Accessory) (25)

| Skill | 名称 | 说明 |
|-------|------|------|
| `alex-content-style` | Alex发帖风格 | Alex内容风格：persona、写作语气、行情反应模板、日常科普模板 |
| `alex-cover-style` | Alex画图风格 | Alex画图风格：persona、写作语气、行情反应模板、日常科普模板 |
| `dae-fly-style` | 大E飞风格 | 犀利直接、数据驱动的投研写作风格 |
| `default-content-style` | 天天出版社内容风格 | 默认写作风格规范，从 SOUL.md 自动适配人设 |
| `default-cover-style` | 天天出版社封面 | 像素画+出版社排版的默认封面风格 |
| `dog-bro-content` | 狗哥内容风格 | 狗哥说财帖子结构模板（产业链拆解/公司拆解/热点传导）、文字风格规范、发帖检查清单 |
| `dog-bro-image` | 狗哥画图风格 | 狗哥说财产业链图解卡片生成：style基底、配色规则、图片分解模板、生图工作流 |
| `james-cover` | 老詹封面生成 | 老詹专属封面图生成：角色形象、卡片模板、配色表情速查、生图调用 |
| `james-style` | 老詹内容风格 | 老詹小红书写稿手册：硬卡点、写作心法、正文模板、语气措辞、排版、标签、评论互动 |
| `laicaimeimei-cover-style` | 来财妹妹封面风格 | 品牌视觉体系与封面图生成标准 |
| `laicaimeimei-writing-style` | 来财妹妹写作风格 | 小红书投研内容写作风格标准 |
| `laok-style` | 老K画图风格 | 老K投资笔记 IP 形象与配图风格 prompt 模板，用于 image-gen-mcp 生成统一视觉风格的配图 |
| `meme-content-style` | meme发帖风格 | meme爱理财内容风格：persona、写作语气、行情反应模板、日常科普模板 |
| `mp-content-writer` | 公众号投资报告 | 公众号投资文章框架（日评/深度/周报） |
| `mp-cover-art` | 公众号配图生成 | 公众号投资文章封面配图：图解信息图风格、四种文章类型模板、产业主题配色、生图调用流程 |
| `nailong-cover` | 小奶龙封面生成 | 小奶龙专属封面图生成：角色形象、卡片模板、配色表情速查、生图调用 |
| `qingningmeng-style` | 清柠檬风格 | 清新可爱、meme 风格内容创作 |
| `record-insight` | 记录灵感 | 捕捉日常观察与灵感洞察 |
| `self-review` | 自我复盘 | 内容表现回顾与改进反思 |
| `visual-first-content` | meme绘图风格 | 图片主导的内容创作框架 |
| `writing-styles` | 叙事风格库 | 可插拔的叙事风格组件，5种风格独立文件，任何写作类 skill 可引用 |
| `xiaotian-cover` | 小天封面生成 | 小天爱黄金专属封面图生成：猫咪角色形象、卡片/场景两套模板、配色表情速查、生图调用 |
| `xiaotian-style` | 小天内容风格 | 小天爱黄金小红书内容形式与风格规范：日常金价播报、深度复盘、排版、封面、通用红线 |
| `xuanma-cover` | 宣妈封面生成 | 宣妈专属封面图生成：角色形象、卡片/写实两套模板、配色表情速查、生图调用 |
| `xuanma-style` | 宣妈内容风格 | 宣妈小红书内容形式与风格规范：日常简评、月度复盘、排版、封面、通用红线 |

## 🔧 通用技能 (Utility) (22)

| Skill | 名称 | 说明 |
|-------|------|------|
| `K-daily-post` | K-daily-post |  |
| `admin-ops` | 管理运维 | agent 状态巡检、异常处理、变更建议撰写 |
| `browser-base` | 浏览器基础 | 浏览器使用规范：profile 管理、标签页生命周期、超时处理 |
| `browser-base-enhanced` | browser-base-enhanced |  |
| `compliance-review` | 合规审核 | 内置 Sonnet 的独立合规审核服务 |
| `contact-book` | 通讯小本本 | 通讯录：群聊 Chat ID、Agent ID、用户飞书 open_id 对照表 |
| `daily-market-recap` | 运营每日盘面复盘 | 公众号每日盘面复盘：对标东方财富证券四段式推送（重磅资讯→数据复盘→盘面解读→后市展望） |
| `fact-check` | 数据核查 | 逐条核实文章中的数据和事实性表述，输出核查报告 |
| `hotspot-sector-analysis` | 热点板块追踪 | 热点板块深度分析文章：编辑给出板块名称，AI自主搜集素材，按四模块结构（行情播报→深度分析→机构观点→相关基金）输出公众号初稿 |
| `james-topic-research` | 詹姆斯话题库 | 小红书詹姆斯话题热点、评论阵营与蹭热度角度 |
| `report-incident` | 异常上报 | 运行时异常记录与通知魏忠贤 |
| `scheduled-post` | 定时发稿 | 草稿审批 + 投稿管道：合规 → draft-review → 魏忠贤 → 印务局 |
| `security-audit` | 安全审计 | 安全巡检、漏洞评估、权限审查 |
| `shangdan-card` | 商单写作 | 商单多图帖：3-4张知识卡片（逻辑讲解+示意图+业绩图+风险提示）+ 配套正文 |
| `skill-generate` | 技能生成器 | 按照 META-SKILL-README.md 规范，通过 Claude Code 生成新 skill |
| `submit-to-publisher` | 印务局投稿 | 通过印务局发布队列提交内容，合规审核后发布 |
| `tougu-db-refresh` | 投顾库刷新 | 调用 tougu_tools.py 的四个函数并写入 tougu.db |
| `trend-broadcast` | trend-broadcast |  |
| `weread-reader` | 微信读书 | 微信读书网页版阅读与书架管理 |
| `xhs-topic-collector` | 小红书素材巡逻 |  |
| `xhs-writing` | 小红书写稿经验 | 通用排版、标题、限流防范 |
| `运营agent` | 运营agent |  |

## ⚔️ 研究技能 (Research) (29)

| Skill | 名称 | 说明 |
|-------|------|------|
| `action-tracker` | 异动追踪 | 韭研公社异动数据采集与板块分析 |
| `deepreasearch` | 深度研究 | 多轮迭代深度研究框架 |
| `earnings-digest` | 财报横评 | 行业财报横向对比与核心观点提取 |
| `energy-chem-tracker` | 能化产业链 | 能源化工产业供需与价格追踪 |
| `finbot-research` | FinBot Research | 个股深度研报、估值分析、催化剂雷达（方法论源自 FinRobot） |
| `flow-watch` | 资金流向 | 北向资金、融资融券、主力流向监控 |
| `gold-tracker` | 黄金盯盘 | 黄金实时行情追踪与收盘复盘，区分盘中/收盘数据源 |
| `gzh-industry-article` | 公众号行业深度文章 | 基于行研 skill 写公众号行业深度文章，叙事风格引用 writing-styles |
| `industry-chain-breakdown` | 产业链拆解 | 产业链上下游竞争分析 |
| `laicaimeimei-fupan` | 来财妹妹每日复盘 | 每日热点与市场深度解读 |
| `lithium-battery-tracker` | 锂电产业链 | 锂电供应链产能与价格追踪 |
| `market-environment-analysis` | 宏观环境 | 全球市场、汇率、商品、风险偏好 |
| `memory-chip-tracker` | 存储芯片产业链 | 存储芯片产业周期与供需追踪 |
| `news-factcheck` | 事实核查 | 新闻数据交叉验证与逻辑检查 |
| `report-compare` | 研报对比 | 多份研报横向对比分析 |
| `report-critique` | 研报批判 | 研报逻辑与数据批判性审视 |
| `report-digest` | 研报速读 | 研报核心观点与数据提取 |
| `report-to-image` | 研报配图-阿泽 | 研报解读内容生成信息图卡片 |
| `report-to-post` | 研报转帖 | 研报内容转化为小红书帖子 |
| `research-mcp` | 研究数据库 | 金融研究 MCP 数据接口（行情/基金/宏观） |
| `research-stock` | 个股分析 | 估值、财务、市场情绪快照 |
| `sector-pulse` | 行业研究 | 行业竞争格局、供需与资金流向 |
| `solar-tracker` | 光伏跟踪 | 硅料→硅片→电池→组件→电站+设备，全链供需与价格跟踪 |
| `space-tracker` | 航天产业链 | 商业航天发射日历与产业链追踪 |
| `stock-watcher` | 自选股 | 自选股列表管理与行情追踪 |
| `technical-analyst` | 技术分析 | K线形态、均线、支撑阻力、量价 |
| `tmt-landscape` | TMT全景 | 电子/计算机/通信/传媒四方向供需推导与轮动判断 |
| `tougu-portfolio-review` | tougu-portfolio-review | 定期模拟 bot 自己复查投顾持仓，对比当前组合与目标组合，决定保持、调仓或切换，并写回测试期 markdown 状态 |
| `tougu-product-match` | tougu-product-match | 优先回答 bot 自己当前的投顾组合与已买产品；如无现成结果，再结合投资策略摘要、memory 与候选池为 bot 自己完成投顾产品匹配 |

## ⏰ 定时任务 (Scheduled) (12)

| Skill | 名称 | 说明 |
|-------|------|------|
| `cron-bot-main-patrol` | 全面巡查 | 临时性全面巡查：印务局登录状态、技能部汇报、编辑部研究状态 |
| `cron-daily-model-report` | 模型日报 | 每天通报各 bot 当前使用的模型序列号 |
| `cron-incidents-check` | 异常巡检(工作日) | 工作日每3小时检查 incidents.jsonl 是否有新 ERROR 异常 |
| `cron-incidents-check-weekend` | 异常巡检(周末) | 周末早晚各一次检查 incidents.jsonl 异常 |
| `cron-xhs-nurture-dispatch` | 养号调度 | 每天5轮从 bot1-7 中随机挑3个执行小红书养号 |
| `daily-review-data` | 每日复盘数据采集 | 一键采集A股市场全景、日内画像、情绪、板块轮动、连板、资金、股东、ERP数据，输出结构化复盘MD |
| `james-daily-post` | 老詹定时发帖 | 内容生产：看行情 → 选题（多资产轮换） → 写稿 → 生图，产出后交 scheduled-post 审批投稿 |
| `meme-daily-post` | meme定时发帖 | 内容生产：看行情 → 选题 → 写稿 → 生图，产出后交 scheduled-post 审批投稿 |
| `xhs-nurture` | 养号互动 | 小红书养号：搜索→点赞→评论→通知回复 |
| `xiaotian-daily-post` | 小天定时发帖 | 内容生产：拉金价 → 选题 → 写稿 → 生图，产出后交 scheduled-post 审批投稿 |
| `xuanma-daily-post` | 宣妈定时发帖 | 内容生产：拉金价 → 选题 → 写稿 → 生成封面文字，默认走 text_to_image 笔记，产出后交 scheduled-post 审批投稿 |
| `zsxq-reader` | 知识星球 | 知识星球情报采集与摘要 |

---

**Total: 99 skills**

