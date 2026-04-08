# 知识库维护指南

## 文件结构

```
memory/memory-chip/
├── daily-feed.md              # 每日资讯流水（滚动保留 7 天）
├── weekly/                    # 周报存档
│   └── 2026-WXX.md
├── price-tracker.md           # 核心品种价格跟踪表（每周更新）
├── supply-demand.md           # DRAM/NAND 全球供需平衡（季度更新）
├── capacity-pipeline.md       # 原厂扩产/新Fab计划（月度更新）
├── stock-watchlist.md         # 股票标的跟踪（估值/催化更新）
├── research-notes.md          # 研报摘要（research-mcp + 知识星球）
├── chain-analysis/            # 各品类深度分析
│   ├── dram.md                # DRAM 供需分析（DDR4/DDR5/LPDDR）
│   ├── nand.md                # NAND Flash 分析（企业级/消费级）
│   ├── hbm.md                 # HBM 跟踪（代际/产能/价格）
│   ├── nor-flash.md           # NOR Flash 分析
│   └── domestic.md            # 国产替代进展（CXMT/YMTC）
├── event-archive.md           # 重大事件记录
└── content-archive.md         # 已发布内容记录
```

---

## price-tracker.md 格式

```markdown
# 半导体存储芯片价格跟踪

> 最后更新：YYYY-MM-DD

## DRAM 合约价（季度/月度）

| 品种 | 当前合约价 | QoQ 变化 | YoY 变化 | 来源 |
|------|-----------|---------|---------|------|
| DDR5 8Gb | $X.XX | +XX% | +XX% | TrendForce |
| DDR4 8Gb | $X.XX | +XX% | +XX% | TrendForce |
| LPDDR5X 16Gb | $X.XX | +XX% | +XX% | TrendForce |
| 服务器DDR5 RDIMM 64GB | $XXX | +XX% | +XX% | 渠道 |

## DRAM 现货价

| 品种 | 现货价 | 周变化 | 月变化 | 来源 |
|------|--------|--------|--------|------|
| DDR5 16Gb eTT | $XX.XX | +X.X% | +XX% | CFM |
| DDR4 8Gb eTT | $X.XX | +X.X% | +XX% | CFM |

## NAND Flash 合约价

| 品种 | 当前合约价 | QoQ 变化 | 来源 |
|------|-----------|---------|------|
| TLC 256Gb | $X.XX | +XX% | TrendForce |
| QLC 512Gb | $X.XX | +XX% | TrendForce |
| 企业级SSD 1TB | $XXX | +XX% | 渠道 |
| 消费级SSD 1TB | $XXX | +XX% | 渠道 |

## HBM 价格

| 品种 | 单颗价格 | vs 上代 | 状态 |
|------|---------|--------|------|
| HBM3E 12Hi | ~$500 | — | 量产出货 |
| HBM4 16Hi | ~$700 | +40% | 2026量产，全年售罄 |

## NOR Flash

| 品种 | 价格 | 周变化 | 备注 |
|------|------|--------|------|
| 128Mb SPI NOR | $X.XX | +X.X% | 兆易创新 +10% |
| 车规NOR 256Mb | $X.XX | +X.X% | 供需偏紧 |
```

---

## 维护规则

| 文件 | 更新频率 | 说明 |
|------|---------|------|
| `daily-feed.md` | 每日追加 | 超过 7 天的内容移除 |
| `price-tracker.md` | 每周 | 合约价为季度/月度频率，现货可按周 |
| `supply-demand.md` | 每季度 | 跟随 TrendForce 季度报告节奏 |
| `capacity-pipeline.md` | 每月初 | 重大扩产消息随时更新 |
| `chain-analysis/` | 有重大变化时 | 原厂财报/技术突破/政策变动 |
| `research-notes.md` | 每月 | 通过 research-mcp search_report 搜索更新 |
| `event-archive.md` | 即时 | 重大事件立即记录 |

---

## 关键数据发布日历

| 数据 | 发布频率 | 发布时间 | 来源 |
|------|---------|---------|------|
| DRAM/NAND 合约价预测 | 每季度 | 季初 | TrendForce |
| DRAM/NAND 现货价 | 每日 | 交易日 | CFM/DRAMeXchange |
| 三星季度财报 | 每季度 | 1/4/7/10月 | 三星电子 |
| SK海力士季度财报 | 每季度 | 1/4/7/10月 | SK海力士 |
| 美光季度财报 | 每季度 | 3/6/9/12月 | Micron |
| 全球半导体销售额 | 每月 | 次月初 | WSTS/SIA |
| 全球半导体设备销售额 | 每季度 | 季后1-2月 | SEMI/SEAJ |
| NVIDIA GTC/财报 | 不定期 | — | NVIDIA |
| 北美云厂商 Capex 指引 | 每季度 | 随财报 | Google/MS/Meta/Amazon |
