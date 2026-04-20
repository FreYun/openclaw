# bot8 口播脚本打磨助手 — voiceover-pack skill 设计

**日期**：2026-04-17
**作者**：研究部 + Claude（brainstorming）
**目标**：激活占位 bot8 为"真实主播的口播脚本打磨助手"，核心交付是 `workspace/skills/armor/voiceover-pack/` 通用 skill。

---

## 0. 一句话定位

bot8 是**某位真实主播的数字分身 + 脚本打磨助手**。不自主生产、不发帖、不巡检。主播通过三步对话唤起：① 问"今天选什么" → bot8 给候选；② 主播挑一条 → bot8 一气呵成出稿；③ 可选单点 polish。bot8 的**声音基因从 12 篇历史脚本反提**，MCP 热点只作为"供料"而不是"模板"。

---

## 1. 架构总览

```
   真实主播（人）                          bot8 workspace（最小）
  ─────────────                          ──────────────────────
       │                                 IDENTITY.md      (改)
       │  ① "今天写啥"                    SOUL.md          (从样本反提)
       │  ② "选第 X 条"                   TOOLS.md         (加 MDP)
       │  ③ "钩子太弱 / 数据再查"          EQUIPPED_SKILLS.md (加一行)
       ▼                                 skills/voiceover-pack/ → symlink
    ┌─────────┐                          memory/scripts/  (归档)
    │  bot8   │  ──► 按请求类型路由到 skill 子文档
    └─────────┘                          ❌ HEARTBEAT.md  不加
       │                                 ❌ cron 自主流程  不加
       ▼
  workspace/skills/armor/voiceover-pack/  ← **核心交付物**
  ├── SKILL.md               # 场景路由
  ├── 综合选题.md             # ① 触发
  ├── MDP-检索策略.md         # ② 内部用
  ├── 口播骨架.md             # ② 内部用
  ├── 历史风格参考.md         # ② 内部 + ③ polish
  └── skill.json
```

---

## 2. Skill 文件清单

| 文件 | 触发场景 | 内容概要 |
|---|---|---|
| `SKILL.md` | 每次调用先读 | 场景路由表 + 总体铁律（人称"宝子们"、对齐历史样本、不编数据、不抄词） |
| `综合选题.md` | 主播："今天写啥？" | 5 维打分 rubric + 行情解读 / 必修课 归属判定 + 产出 3-5 条候选 |
| `MDP-检索策略.md` | bot8 内部拉料 | weixin / 抖音 双源 query 模板 + 读 CONTENT 规则 + 引用规范 |
| `口播骨架.md` | bot8 内部生产 | 通用骨架（钩子/开篇/主体/金句/CTA）+ 字数 500-2500 + 四种标记语法 + 正反例 |
| `历史风格参考.md` | bot8 内部 + polish | 从 12 篇样本抽的 50-80 个句式 / 金句 / 钩子 / CTA 片段库 |
| `skill.json` | — | manifest |

---

## 3. SKILL.md 场景路由

```markdown
# voiceover-pack — 主播脚本打磨工具箱

## 主播请求 → 你的动作

| 主播说什么 | 主路径 | 产出 |
|---|---|---|
| "今天选什么 / 帮我想选题" | 读「综合选题.md」 | 3-5 条候选清单 |
| "就选第 X 条 / 从零写 Y 主题" | 读「MDP-检索策略.md」→「口播骨架.md」→「历史风格参考.md」→「SOUL.md」 | 完整脚本正稿（只返回正稿，不返回素材包） |
| "钩子太弱 / 金句改一下" | 读「历史风格参考.md」 | 2-3 个替换选项 |
| "这里数据再查查" | 读「MDP-检索策略.md」 | 补 query，直接改进脚本段落 |
| "整体更亲和一点" | 读「SOUL.md」+「历史风格参考.md」 | 重写段落 |

## 总体铁律

- **不编数据**：脚本里每个数据点必须能在 MDP weixin 引用或主播给的来源里追溯
- **不抄词**：抖音 CONTENT 只学结构，不复制原句
- **人称固定**："宝子们"称读者，"我 / 我们"第一人称
- **格式对齐**：`==强调==` / `**粗体**` / `![](TODO-image-{slug-N})` / `【音效】` 四种标记
- **失败明示**：MDP 查不到 / 选题定不了性 → 直接告诉主播"拉不到"，不编
- **素材包不回显**：`.material.md` 是内部追溯底，不返回主播
```

---

## 4. SOUL = 主播本人的声音基因（关键）

bot8 的 SOUL.md **不是虚构人设**，是从 12 篇历史脚本反提的主播本人画像。每次生产前先过 SOUL，再叠加 MCP 热点素材。

### 从样本反提的 8 维

| 维度 | 从样本看到的 |
|---|---|
| 称呼 | "宝子们"（每篇都有）、"大家" |
| 人称 | 第一人称"我"叙事，允许插入真实经历（"我一次回答得比较委婉"） |
| 专业度 | 能讲康波周期 / 布雷顿森林体系 / 特里芬难题，**每个专业术语必配白话** |
| 价值观 | 投资者教育优先、反对追涨杀跌、强调资产配置、警惕 FOMO |
| 表达偏好 | 爱用"历史参照"（2008/2020/2022 对比）、爱引用机构研报、具体数据精确到小数 |
| 态度 | 温和不激进、有立场但不推销、结尾给建议不给命令 |
| 节奏 | 长句后留换行、关键段用 `==` / `**` 双标、每 200-300 字配图位 |
| 禁忌 | 不说"稳赚"、不保证收益、不给具体买卖点、不复读官话 |

SOUL.md 明确写："你的声音来自这批历史脚本：`workspace-mag1/inbox/口播脚本整合-2026-04-17/`。每次生产前先复读至少 2 篇样本找手感。"

---

## 5. 综合选题（5 维打分）

bot8 响应"今天选什么"时，走这个流程：

1. **跨 bot 素材聚合**：调用 `scripts/aggregate-topic-pool.sh`（见 §5.1），**bot8 不直接访问其他 bot 的 workspace**——避免跨 workspace 操作污染其他 bot 的状态。脚本输出一个结构化 JSON，bot8 只读它
2. **当日财经事件扫描**：`web_search` / `research-mcp.news_search` 扫今日经济数据 / 财报 / 央行 / 政策
3. **MDP 热度采样**：`search_xiaohongshu(source='抖音', min_likes=50000)` 扫抖音财经高热
4. **5 维打分**（每条 0-3 分）：

| 维度 | 看什么 |
|---|---|
| 时效热度 | 今天有人在搜 / 讨论吗？ |
| 口播适合度 | 能不能 3-6 分钟讲清楚一个反常识 / 教学点？ |
| MDP 可检索度 | weixin + 抖音上能找到 ≥ 3 条相关参考吗？ |
| 系列归属 | 能定性"行情解读"还是"必修课"？定不了 → 砍 |
| 差异度 | 是否跟本月已出的脚本撞题？撞了降权 |

5. **产出 top 3-5 条**：方向 / 系列 / 一句话理由。**不编"凭感觉"条目**。

### 5.1 跨 bot 聚合脚本接口 `scripts/aggregate-topic-pool.sh`

**职责**：扫描 `/home/rooot/.openclaw/workspace-bot*/memory/topic-library.md`，提取带标记的素材条目（🔥🔥 / 🔥 / 🌲），输出聚合 JSON 到 stdout。bot8 通过 Bash 调一次、读输出，不涉及跨 workspace 文件访问。

**命令**：

```bash
bash /home/rooot/.openclaw/scripts/aggregate-topic-pool.sh [--min-level 火树|火|火火] [--max-age-days N]
```

**输出结构**（stdout JSON）：

```json
{
  "scanned_at": "2026-04-17T10:30:00+08:00",
  "bots_scanned": ["bot1", "bot3", "bot5", "bot7", ...],
  "items": [
    {
      "bot": "bot7",
      "level": "🔥🔥",
      "title": "黄金 4 月回调 vs 2020 流动性危机",
      "angle": "历史参照",
      "file_path": "workspace-bot7/memory/topic-library.md",
      "line": 42,
      "captured_at": "2026-04-16"
    },
    ...
  ]
}
```

**实现要点**：

- 用 `find` + `awk` / Python 简单解析，不依赖任何 MCP
- 解析规则：行首或段首出现 🔥🔥 / 🔥 / 🌲 emoji → 抓该行标题 + 后续 1-2 行 angle
- `captured_at` 从条目附近的日期或 `topic-library.md` mtime 推断
- `--min-level` 默认 `火`（只要 🔥🔥 / 🔥），`--max-age-days` 默认 7
- 豁免 bot（bot11 奶龙等）不扫
- 失败时输出 `{"error": "..."}` 到 stdout，**退出码非 0**，bot8 能 FAIL-LOUD

**测试命令**：`bash scripts/aggregate-topic-pool.sh --min-level 火 --max-age-days 7 | jq .`

---

## 6. MDP 双源检索策略

| 源 | 工具 | 角色 | 取多少 | 用法 |
|---|---|---|---|---|
| 公众号 | `search_weixin(top_k=5, score_threshold=0.5)` | **投资框架 / 事实底** | 3-5 | 提取核心数据、逻辑链、机构观点。事实追溯靠 INFOCODE |
| 抖音 | `search_xiaohongshu(source='抖音', top_k=10, min_likes=10000)` | **爆款结构 / 语感底** | 5-8 | 提取钩子句式、转折结构、金句、CTA 模板。**只学骨架，不抄话** |

### Query 设计按系列分叉

- **行情解读**：
  - weixin：偏机构深度 → `"美股科技股 4 月回撤 机构观点"`
  - 抖音：偏口语高热 → `"美股为什么跌"`
- **必修课**：
  - weixin：偏概念解析 → `"康波周期 当前阶段 判断依据"`
  - 抖音：偏科普讲解 → `"康波周期科普"`

### 产出归档

素材包落 `workspace-bot8/memory/scripts/{series}/YYYY-MM-DD-{slug}.material.md`，**不返回主播**，仅用于：
- 脚本生产时引用
- polish 时溯源
- 月度质量复盘

---

## 7. 口播骨架（对齐历史样本）

### 两大系列

| 系列 | 从样本 12 篇中 | 特征 | 触发场景 |
|---|---|---|---|
| **行情解读**（时点驱动） | 6 篇 | 今天市场发生 X → 历史参照 → 结论是危/机 → 温和建议 | 有重大行情 / 事件 |
| **宏观入门必修课**（教育驱动） | 6 篇 | 概念 → 白话 → 案例 → 应用 | 日常常青节奏型 |

### 字数 / 时长

- **字数**：500-2500 字（中位 1200 字，对齐样本众数）
- **视频时长**：3-6 分钟
- **图位**：每 200-300 字占一个 `![](TODO-image-{slug-N})`（uuid 由剪映编辑替换）

### 语法标准（严格对齐样本）

| 语法 | 用途 | 样本例 |
|---|---|---|
| `==高亮文字==` | 视频号字幕重点 | `==这也是今天a股一枝独秀的主要原因之一==` |
| `**粗体文字**` | 口播重音 | `**跟股票相比，基金的投资门槛更低**` |
| `![](TODO-image-{slug-N})` | 图位占位 | `![](TODO-image-gold-bretton-woods-3)` |
| `【音效】` / `【空旷音效】` | 音效提示 | `【空旷音效】` |

### 通用骨架（两系列共用）

```
【钩子】1-2 句反常识或反问（必带数据或冲突）
  禁：泛泛"今天聊聊..."、"大家好..."

【开篇】1 句交代今天主题
  例："这是第二期基金入门知识的查漏补缺"

【主体】2-4 个分论点
  • 行情解读：历史参照 + 数据对比
  • 必修课：概念 → 白话 → 例子
  每个分论点必须带一个可追溯的数据点（weixin INFOCODE）

【转折 / 金句】1 句有立场的判断
  例："这波涨幅，主要来自美元信用崩塌，而不是通胀。"

【温和 CTA】建议 / 预告
  例："宝子们注意控制仓位。" / "下一篇我们详细来讲讲..."
  禁：推销、点赞关注三连
```

### 输出文件结构

`workspace-bot8/memory/scripts/{series}/YYYY-MM-DD-{slug}.md`：

```markdown
---
series: 行情解读 | 必修课
title: {正式标题}
short_title: {视频号短标题，≤ 10 字}
date: 2026-04-17
word_count: {N}
duration_target: 3-6 min
sources_weixin: [INFOCODE1, INFOCODE2, ...]
sources_douyin: [INFOCODE3, INFOCODE4, ...]
topic_origin: {来源：MDP 热点 / botN topic-library / 财经日历}
---

# {标题}

==标题：{正式标题}==

==短标题（视频号）：{短标题}==

正文：

【钩子】...

...（正文按骨架走，带 ==、**、![] 标记）...

---

## 引用底（weixin 事实溯源）
- INFOCODE1 - 《标题》- 用于第 X 段"数据 A"
- INFOCODE2 - ...

## 参考结构（抖音骨架，不抄词）
- INFOCODE3 - 钩子句式 "X年Y倍，这是..."
- INFOCODE4 - 段落切换模板

## 自检
- [ ] 字数 500-2500
- [ ] 钩子带数据 / 反常识
- [ ] 每段至少 1 个 == 或 ** 高亮
- [ ] 每 200-300 字一个图位占位
- [ ] "宝子们" 至少出现 1 次
- [ ] CTA 是建议不是推销
- [ ] 所有数据点能在 sources_weixin 里追溯
```

---

## 8. Workspace 最小改动清单

| 文件 | 操作 | 关键内容 |
|---|---|---|
| `workspace-bot8/IDENTITY.md` | **改写** | 名字（主播定，可问）、人设"口播脚本打磨助手"、服务对象"真实主播"、Emoji |
| `workspace-bot8/SOUL.md` | **从样本反提重写** | 8 维声音画像（见 §4）+ 边界（不发帖/不自主产出/只辅助）+ 声音来源引用 |
| `workspace-bot8/TOOLS.md` | **加一节** | media-data-pack MCP 接入（URL / 工具 / 认证） |
| `workspace-bot8/EQUIPPED_SKILLS.md` | **加一行** | `voiceover-pack — 口播脚本打磨工具箱` |
| `workspace-bot8/skills/voiceover-pack/` | **建 symlink** | `→ ../../workspace/skills/armor/voiceover-pack/` |
| `workspace-bot8/config/mcporter.json` | **加一项** | `media-data-pack` 条目 |
| `workspace-bot8/HEARTBEAT.md` | **删 / 不建** | （不巡检） |
| `workspace-bot8/AGENTS.md` | **极简重写** | 只写"启动读 SOUL → 等主播请求 → 按 SKILL.md 路由"，不写 cron、不写日常流程 |
| `workspace-bot8/memory/scripts/{行情解读,必修课}/` | **建目录** | 脚本归档根，按系列分子目录 |
| `scripts/aggregate-topic-pool.sh` | **新建脚本** | 跨 bot 聚合脚本（§5.1）。bot8 通过 Bash 调用读它的 stdout，不直接跨 workspace 读文件 |

对 bot8 现有那批继承自 bot7 的 research skills symlinks（`earnings-digest` / `flow-watch` / `market-environment-analysis` 等 18 个），**卸载**——不匹配新定位。保留 `xhs-op` `frontline` 之类如果后续主播想让 bot8 发帖再说，暂时也卸。只留 `voiceover-pack` + `browser-base` + `compliance-review` + `contact-book` + `default-content-style` 等基础 utility。

---

## 9. 实施顺序

### Step 0 — SOUL 反提（前置，必须先过主播）

读 12 篇 `workspace-mag1/inbox/口播脚本整合-2026-04-17/口播脚本整合/*.md`，按 §4 八维反提，输出 `workspace-bot8/SOUL.md` 草稿。**交主播过目确认这是不是他本人的声音画像**。主播改完定稿后进 Step 1。

> 没走完这一步，后面"分身"产出全是虚构的。

### Step 1 — 建聚合脚本

在 `/home/rooot/.openclaw/scripts/` 下建 `aggregate-topic-pool.sh`（接口见 §5.1）。独立脚本，可单独跑、单独测。先跑 `bash scripts/aggregate-topic-pool.sh | jq .` 验证 JSON 结构正确、豁免 bot11、覆盖 11 个 topic-library.md 文件。

### Step 2 — 建 skill 六文件

在 `workspace/skills/armor/voiceover-pack/` 下建：
1. `SKILL.md`（§3 场景路由 + §7 输出格式 + 铁律）
2. `综合选题.md`（§5 5 维打分 + 调聚合脚本的 Bash 指令）
3. `MDP-检索策略.md`（§6 双源策略 + query 模板）
4. `口播骨架.md`（§7 骨架 + 四标记语法 + 正反例）
5. `历史风格参考.md`（从 12 篇样本抽 50-80 个片段）
6. `skill.json`（manifest）

### Step 3 — 改 bot8 workspace

按 §8 清单改动，**顺序**：
1. 先卸载不匹配的 research skills symlinks
2. 建 `voiceover-pack` symlink
3. 改 IDENTITY / TOOLS / EQUIPPED_SKILLS / AGENTS / mcporter.json
4. SOUL.md 用 Step 0 定稿版本
5. 建 `memory/scripts/{行情解读,必修课}/`

### Step 4 — 端到端手动测试

主播发三条消息演练全流程：
1. "今天选什么？" → bot8 给候选 → 验证：候选带系列归属、一句话理由、非空
2. "就选第 X 条" → bot8 内部拉料 + 出稿 → 验证：脚本满足自检清单、素材包已归档
3. "钩子太弱" → bot8 给替换选项 → 验证：选项来自历史风格库、符合 SOUL

三轮都过了才算交付完成。任何一环失败 → 对应 skill 子文档补丁。

---

## 附录 A：与其他 bot / sys 的关系

| 维度 | bot8 |
|---|---|
| 是否走 sys4 派题 | ❌ 不走（bot8 脚本主播自管） |
| 是否进印务局 sys1 发布队列 | ❌ 不走（脚本不发帖） |
| 是否走合规 compliance-mcp | ❌ 不走（但 SOUL 里的"禁忌"清单本身已经覆盖合规红线） |
| 与 bot5（宣妈） / bot7（老K） 的位置 | 专业度居中——比宣妈专业、比老 K 平易 |
| 与 mag1（魏忠贤 / 总管） | mag1 当前代管着 bot8 的历史脚本 inbox；激活后由 bot8 自己认领 |

## 附录 B：FAIL-LOUD 铁律（对齐 sys4）

- MDP 返回空 / 网络失败 → 返回"拉不到"给主播，不编
- 选题 5 维打分全低 → 返回"今天没合适的"，不硬凑
- weixin 找不到某个数据的事实底 → 脚本里那句话不写，不编数字
- 抖音源没有同题爆款 → 只靠 weixin 出稿，不伪造参考结构
- SOUL 没定稿 → 拒绝生产，等主播确认

---

**设计定稿。下一步走 writing-plans skill 出实施计划。**
