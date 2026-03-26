# Brain.db — Bot 结构化记忆数据库规范

## 1. 概述

`brain.db` 是每个 bot 的 **结构化长期记忆**，采用 SQLite 3 存储，位于各 bot 的 `memory/` 目录下。

设计思路：**每张表都是统一的三字段结构（date, filename, content）**，本质是把 bot 的 Markdown 记忆文件结构化入库，方便按日期、文件名检索和按类别归档，同时保留 Markdown 的完整内容。

与现有的 Markdown 日记体系（`memory/YYYY-MM-DD.md`、`MEMORY.md`）互补：
- **Markdown 文件** → 人类可读的日记和笔记，bot 日常读写
- **brain.db** → 按类别分表归档，支持 SQL 查询、统计、跨日期检索

### 当前部署状态

| Bot | brain.db | 数据量 |
|-----|----------|--------|
| bot1 (来财妹妹) | ✅ 132KB | 34 rows |
| bot2 (狗哥说财) | ✅ 56KB | 8 rows |
| bot3 | ❌ | — |
| bot4 (研报搬运工阿泽) | ✅ 96KB | 17 rows |
| bot5 | ❌ | — |
| bot6 | ❌ | — |
| bot7 | ❌ | — |
| bot8 | ❌ | — |
| bot9 | ❌ | — |
| bot10 (测试君) | ✅ 76KB | 5 rows |
| bot11 | ❌ | — |

---

## 2. Schema 定义

### 2.1 统一表结构

**所有业务表共用同一个三字段结构**，通过不同的表名区分内容类别：

```sql
-- 会话日记
CREATE TABLE conversations (
    date TEXT NOT NULL,        -- 日期，如 '2026-03-12'
    filename TEXT NOT NULL,    -- 源文件名，如 '2026-03-12.md'
    content TEXT NOT NULL      -- 完整 Markdown 内容
);

-- 发帖记录
CREATE TABLE posts (
    date TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT NOT NULL
);

-- 研究笔记
CREATE TABLE research (
    date TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT NOT NULL
);

-- 事件追踪
CREATE TABLE events (
    date TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT NOT NULL
);

-- 长期记忆
CREATE TABLE long_term (
    date TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT NOT NULL
);

-- 元数据（key-value 存储）
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
```

### 2.2 meta 表必填字段

所有 bot 的 `meta` 表必须包含以下 4 个 key：

| key | 说明 | 示例 |
|-----|------|------|
| `schema_version` | Schema 版本号 | `1.0` |
| `bot_id` | Bot 标识 | `bot7` |
| `bot_name` | Bot 显示名 | `老K投资笔记` |
| `created_at` | 数据库创建时间 | `2026-03-25 16:57:38` |

---

## 3. 各表用途说明

| 表 | 写入时机 | content 里存什么 |
|----|---------|-----------------|
| `conversations` | 每次会话结束 | 当日工作日志（完整 Markdown） |
| `posts` | 发帖后 | 帖子完整内容（标题、正文、标签等） |
| `research` | 完成研究后 | 热点解读、行业分析、个股研究报告 |
| `events` | 重要事件发生时 | 异常错误、里程碑、研究部指令变更 |
| `long_term` | 提炼持久知识时 | 工具规范、运营经验、风格参考、踩坑教训 |
| `meta` | 初始化时 | （特殊表，key-value 结构，非三字段） |

### 字段约定

- **date**: `YYYY-MM-DD` 格式，表示该条记录对应的日期
- **filename**: 对应的 Markdown 源文件名（如 `2026-03-12.md`、`大盘绿了，油气却爆了？💚.md`）
- **content**: 完整的 Markdown 文本，保留原始格式

---

## 4. 文件路径规范

### 4.1 目录结构

brain.db 和三个必备子文件夹组成完整的记忆存储系统。**数据库是索引，文件夹是实体**——brain.db 的 `filename` 字段指向对应文件夹里的实际文件。

```
workspace-botN/
├── memory/
│   ├── brain.db              ← 结构化记忆数据库（索引）
│   │
│   │
│   ├── posts/                ← 对应 posts 表
│   │   ├── 2026-03-19.md     ←   发帖记录
│   │   ├── 2026-03-19-帖子内容.md  ← 帖子正文
│   │   ├── 2026-03-19-封面图.png   ← 封面图片
│   │   └── ...
│   │
│   ├── research/             ← 对应 research 表
│   │   ├── 2026-03-19-每日热点解读.md
│   │   └── ...
│   │
│   ├── long_term/            ← 对应 long_term 表
│       ├── 发帖规范.md
│       ├── 发帖数据需求清单.md
│       └── Bool 资本不眠 - 发帖风格分析.md
│
├── MEMORY.md                 ← 长期记忆精华索引
├── SOUL.md
├── AGENTS.md
└── ...
```

### 4.2 必备文件夹与表的对应关系

| 文件夹 | 对应表 | 文件命名规则 | 内容 |
|--------|--------|-------------|------|
| `agents/botX` | `conversations` | `YYYY-MM-DD.md` | 每日工作日记 |
| `posts/` | `posts` | `YYYY-MM-DD-标题.md`、`.png` | 帖子内容、封面图 |
| `research/` | `research` | `YYYY-MM-DD-主题.md` | 研究报告、热点解读 |
| `long_term/` | `long_term` | 按主题命名，如 `发帖规范.md` | 持久知识沉淀 |

> `events` 表没有独立文件夹，事件记录通常内联在 diary 或直接写入数据库。

### 4.3 数据库与文件夹的关系

- **brain.db 是索引**：`filename` 字段存的是文件名（不含路径前缀），对应文件存放在同名文件夹里
- **文件夹是实体**：Markdown 原文和图片等资源都放在文件夹中，bot 日常读写直接操作文件
- **双向一致**：写入文件时同步 INSERT 到 brain.db；反过来，通过 brain.db 查到的 filename 可以直接在对应文件夹里找到原文件

### 4.4 权限

```
drwx------ (700)  diary/ posts/ research/ long_term/
-rw-r--r-- (644)  brain.db
```

---

## 5. 新 Bot 建库流程

### 5.1 初始化脚本

```bash
BOT_ID="bot7"
BOT_NAME="老K投资笔记"
MEMORY_DIR="/home/rooot/.openclaw/workspace-${BOT_ID}/memory"
DB_PATH="${MEMORY_DIR}/brain.db"

# 创建 memory 目录和三个必备子文件夹
mkdir -p "${MEMORY_DIR}"/{diary,posts,research,long_term}

python3 -c "
import sqlite3

conn = sqlite3.connect('${DB_PATH}')
cur = conn.cursor()

# 5 张业务表，统一三字段结构
for table in ['conversations', 'posts', 'research', 'events', 'long_term']:
    cur.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
        date TEXT NOT NULL,
        filename TEXT NOT NULL,
        content TEXT NOT NULL
    )''')

# meta 表
cur.execute('''CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
)''')

# 写入必填 meta
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for k, v in [('schema_version', '1.0'), ('bot_id', '${BOT_ID}'), ('bot_name', '${BOT_NAME}'), ('created_at', now)]:
    cur.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', (k, v))

conn.commit()
conn.close()
print(f'brain.db created at ${DB_PATH}')
"
```

### 5.2 批量为缺失 bot 建库

```bash
# 需要建库的 bot 列表（根据实际情况修改 bot_name）
declare -A BOTS=(
    [bot3]="清柠檬"
    [bot5]="宣妈慢慢变富"
    [bot6]="James投研"
    [bot7]="老K投资笔记"
    [bot8]="研究员小张"
    [bot9]="复盘日记"
    [bot11]="能源小白"
)

for BOT_ID in "${!BOTS[@]}"; do
    BOT_NAME="${BOTS[$BOT_ID]}"
    DB_PATH="/home/rooot/.openclaw/workspace-${BOT_ID}/memory/brain.db"
    [ -f "$DB_PATH" ] && echo "SKIP ${BOT_ID} (already exists)" && continue
    # 运行上面的 python3 建库脚本...
    echo "CREATED ${BOT_ID} → ${DB_PATH}"
done
```

---

## 6. 与 Markdown 记忆体系的关系

| 维度 | Markdown 文件 | brain.db |
|------|--------------|----------|
| 可读性 | 人类直接阅读 | 需要 SQL 查询 |
| 查询 | grep/全文搜索 | SQL 精确查询、聚合、关联 |
| 写入 | bot 每次会话自然写入 | 需要显式 INSERT |
| 历史 | git 版本控制 | 数据库内 created_at |
| 适合场景 | 日记、笔记、风格参考 | 发帖统计、研究追踪、事件审计 |

**两套系统互补，不是替代关系。** Bot 日常仍以 Markdown 为主，brain.db 用于需要结构化查询的场景（如"最近 7 天发了几篇帖子"、"置信度 > 0.8 的研究有哪些"）。
