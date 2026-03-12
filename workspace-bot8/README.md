# 老k — A股科技行业投研 Agent

> 直接给判断，不说废话。结论先行，数据说话。

一个专注 A股科技赛道的投研 AI Agent，基于 [OpenClaw](https://openclaw.com) 平台构建。集成智谱 GLM-5 大模型、Tushare Pro 金融数据、智谱联网搜索，能够独立完成从行业研究到个股分析的完整投研工作流。

---

## 它能做什么

| 技能 | 触发方式 | 说明 |
|------|---------|------|
| 行业深度研究 | `/sector-pulse 半导体` | 产业链梳理、竞争格局、供需景气、估值横比、投资结论 |
| 财报季横评 | `/industry-earnings AI算力` | 多家公司三张表横向对比，识别行业共性趋势与个股分化 |
| 北向资金轮动 | `/flow-watch` | 追踪外资在各行业的净流向，识别配置信号 |
| 全球宏观环境 | `/market-environment-analysis` | risk-on/off 判断，美股/汇率/大宗/VIX 综合分析 |
| 个股快速查询 | `/research-stock 600519.SH` | 当前估值、近期走势、最新财务、分析师评级 |
| 图表技术分析 | 发图 + `/technical-analyst` | 趋势、支撑压力、均线、形态，概率加权情景 |
| 资讯真实性核查 | `/news-factcheck [内容]` | 时间核验 + 数据交叉核实 + 逻辑一致性检查 |
| 自选股管理 | `/stock-watcher` | 添加/删除自选股，查看行情摘要 |
| 研究记录保存 | `/record` | 结构化写入记忆系统，供后续复盘和增量更新 |
| 定期复盘进化 | `/self-review` | 核验历史预测，更新行业观点，识别分析盲点 |

---

## 工作原理

### 三层数据来源，并行获取

```
Tushare Pro          智谱 MCP 搜索         OpenClaw Browser
─────────────        ──────────────        ──────────────────
行情/财务数据         联网实时资讯           雪球/东方财富/同花顺
结构化、精确          覆盖面广               原文、情绪、研报
```

每次研究，三个来源同步进行，互相补充和验证。

### 核心研究循环

```
信息收集（fetch）→ 分析研判（study）→ 核实验证（verify）→ 输出
        ↑___________________________|
              发现缺口时回头补充
```

- **每条核心结论**在输出前必须有具体数据支撑，来源和时效都要确认
- **逻辑自洽检查**：景气度高但毛利率连续下滑？格局稳定但价格战信号明确？发现矛盾必须解释
- **时间核验**：所有资讯标注发布日期，🟢 ≤7天 / 🟡 8-30天 / 🔴 >30天，杜绝旧数据冒充新信息

### 记忆系统

研究结论结构化存入本地记忆（QMD BM25 全文索引），下次研究同一行业时自动检索历史，做增量更新而不是从零开始。预测有单独跟踪表，定期核验正确/证伪，驱动 Agent 自我进化。

```
memory/
├── research/     每次研究的完整记录（按日期）
├── views/        各行业持续跟踪观点（滚动更新）
├── predictions/  预测登记与核验结果
└── evolution/    自我进化日志
```

---

## 安装

### 前置要求

安装前，先准备好以下账号和密钥：

| 服务 | 用途 | 注册地址 |
|------|------|---------|
| **智谱 BigModel API Key** | 大模型 + 联网搜索 + 视觉分析 | [bigmodel.cn](https://bigmodel.cn) — 免费注册，有免费额度 |
| **Tushare Pro Token** | A股行情和财务数据 | [tushare.pro](https://tushare.pro) — 免费注册，需积分 ≥2000（见下方说明） |
| **Node.js ≥18** | 运行 OpenClaw | [nodejs.org](https://nodejs.org) |
| **Python ≥3.10** | stock-watcher 依赖 | 系统自带或 [python.org](https://python.org) |

> **Tushare 积分**：免费注册 + 实名认证 + 手机绑定，可免费获得约 2000 积分，恰好达到财务报表接口门槛，无需付费。

---

### 第一步：安装 OpenClaw 和 QMD

```bash
npm install -g openclaw
npm install -g @tobilu/qmd
```

QMD 是 Agent 的记忆检索引擎（BM25 全文索引），负责在历史研究记录中快速搜索。安装后无需额外配置，OpenClaw 会自动初始化索引。

---

### 第二步：克隆本仓库

```bash
git clone https://gitee.com/alex_sun/zjstech.git ~/.openclaw/workspace
```

> 如果 `~/.openclaw/workspace` 已存在，先备份再克隆：
> ```bash
> mv ~/.openclaw/workspace ~/.openclaw/workspace.bak
> git clone https://gitee.com/alex_sun/zjstech.git ~/.openclaw/workspace
> ```

---

### 第三步：初始化记忆文件

```bash
cp ~/.openclaw/workspace/MEMORY.md.template ~/.openclaw/workspace/MEMORY.md

mkdir -p ~/.openclaw/workspace/memory/{research,views,predictions,evolution}
touch ~/.openclaw/workspace/memory/predictions/tracker.md
touch ~/.openclaw/workspace/memory/evolution/changelog.md
touch ~/.openclaw/workspace/memory/evolution/review-log.md
```

---

### 第四步：配置 OpenClaw

运行引导向导，选择**智谱 GLM** 模型并输入 API Key：

```bash
openclaw onboard
```

将仓库内的 Tushare 插件复制到 OpenClaw 插件目录：

```bash
cp -r ~/.openclaw/workspace/plugins/openclaw-tushare ~/.openclaw/extensions/openclaw-tushare
```

编辑 `~/.openclaw/openclaw.json`，填入 Tushare Token，并确认以下关键设置（参考 `config/openclaw.config.snippet.json`）：

```json
"tools": {
  "deny": ["web_search"]
},
"plugins": {
  "allow": ["openclaw-tushare"],
  "entries": {
    "openclaw-tushare": {
      "enabled": true,
      "config": {
        "token": "YOUR_TUSHARE_TOKEN"
      }
    }
  }
},
"memory": {
  "backend": "qmd"
}
```

> `tools.deny: ["web_search"]` 禁用内置搜索，强制走智谱 MCP，保证中文搜索质量。

---

### 第五步：配置智谱 MCP 服务器

安装 mcporter：

```bash
npm install -g mcporter
```

复制配置模板并填入智谱 API Key（两处）：

```bash
mkdir -p ~/.mcporter
cp ~/.openclaw/workspace/config/mcporter.config.template.json ~/.mcporter/mcporter.json
# 然后编辑 ~/.mcporter/mcporter.json，将 YOUR_ZHIPU_API_KEY 替换为真实密钥
```

验证 MCP 服务器状态：

```bash
mcporter list
# bigmodel-search 和 zai-vision 应均显示 healthy
```

---

### 第六步：安装 stock-watcher 依赖

```bash
pip install requests beautifulsoup4
# Ubuntu 系统 pip 未预装时：
# curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages
# python3 -m pip install requests beautifulsoup4 --break-system-packages

bash ~/.openclaw/workspace/skills/stock-watcher/scripts/install.sh
```

---

### 第七步：启动 Gateway

**Linux**：

```bash
# Ubuntu Server / SSH 环境必须先设置这个环境变量
echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u)' >> ~/.bashrc
source ~/.bashrc

openclaw gateway install
```

**macOS**：

```bash
openclaw gateway install
```

**Windows**：使用 OpenClaw Desktop 客户端，gateway 由 GUI 管理。

验证 gateway 运行中：

```bash
openclaw gateway status
```

---

### 验证安装

启动 Agent 对话界面：

```bash
openclaw
```

发送以下消息验证：

```
/sector-pulse AI算力
```

Agent 自动调用 Tushare 数据 + 智谱搜索 + browser 浏览，输出完整行业研究报告，说明安装成功。

---

## 配置文件说明

| 文件 | 路径 | 含密钥 |
|------|------|--------|
| OpenClaw 主配置 | `~/.openclaw/openclaw.json` | ✅ Tushare Token |
| MCP 服务器配置 | `~/.mcporter/mcporter.json` | ✅ 智谱 API Key |
| Agent 工作区 | `~/.openclaw/workspace/`（本仓库） | ❌ 无密钥 |

本仓库不包含任何密钥。密钥仅存于本地配置文件，不会被 git 追踪。

---

## 常见问题

**Tushare 返回空数据**：登录 tushare.pro 查看积分余额，财务报表接口需 ≥2000 积分。积分不足时 Agent 会说明原因，不会猜测数据。

**智谱搜索无结果**：检查 `~/.mcporter/mcporter.json` 中 API Key 是否正确，确认 mcporter 正在运行（`mcporter list`）。

**如何修改 Agent 性格**：编辑 `SOUL.md`（行为准则和研究风格）和 `IDENTITY.md`（名字和定位），改完即生效。

**如何添加新技能**：

```bash
clawhub install <技能名>
```

安装后在 `AGENTS.md` 的投研技能清单中登记，下次会话生效。

---

## 项目结构

```
~/.openclaw/workspace/
├── AGENTS.md              # Agent 行为规范（每次会话必读）
├── SOUL.md                # Agent 身份与研究风格
├── TOOLS.md               # 工具使用规范（Tushare / browser / zhipu MCP）
├── IDENTITY.md            # Agent 名字和定位
├── RESEARCH.md            # 投研记忆系统操作手册
├── HEARTBEAT.md           # 定期任务（预测核验、月度复盘）
├── USER.md                # 用户信息（Agent 自动填写）
├── MEMORY.md              # Agent 长期记忆（本地私有，不入库）
├── MEMORY.md.template     # 长期记忆初始模板
├── config/
│   ├── openclaw.config.snippet.json   # openclaw.json 关键字段参考
│   └── mcporter.config.template.json  # MCP 配置模板
├── plugins/
│   └── openclaw-tushare/              # Tushare Pro 数据插件（手动复制安装）
└── skills/
    ├── sector-pulse/                  # 行业深度研究（旗舰）
    ├── earnings-digest/               # 财报季横向比较
    ├── flow-watch/                    # 北向资金轮动
    ├── market-environment-analysis/   # 全球宏观环境
    ├── research-stock/                # 个股快速查询
    ├── technical-analyst/             # 图表技术分析
    ├── news-factcheck/                # 资讯核查
    ├── stock-watcher/                 # 自选股管理
    ├── record-insight/                # 研究记录保存
    └── self-review/                   # 复盘与自我进化
```

---

## License

MIT
