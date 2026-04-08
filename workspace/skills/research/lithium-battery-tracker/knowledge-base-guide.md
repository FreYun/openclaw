# 知识库维护指南

## 文件结构

```
memory/lithium-battery/
├── daily-feed.md              # 每日资讯流水（滚动保留 7 天）
├── weekly/                    # 周报存档
│   └── 2026-WXX.md
├── price-tracker.md           # 核心品种价格跟踪表（每日更新）
├── supply-demand.md           # 碳酸锂供需平衡跟踪（月度更新）
├── capacity-pipeline.md       # 新增产能投产计划（月度更新）
├── stock-watchlist.md         # 股票标的跟踪（估值/催化更新）
├── research-notes.md          # 研报摘要（research-gateway + 知识星球）
├── chain-analysis/            # 各环节深度分析
│   ├── lithium-carbonate.md   # 碳酸锂供需分析
│   ├── cathode.md             # 正极材料分析
│   ├── anode.md               # 负极材料分析
│   ├── electrolyte.md         # 电解液分析
│   ├── separator.md           # 隔膜分析
│   └── solid-state.md         # 固态电池进展跟踪
├── event-archive.md           # 重大事件记录
└── content-archive.md         # 已发布内容记录
```

---

## price-tracker.md 格式

```markdown
# 锂电池产业链价格跟踪

> 最后更新：YYYY-MM-DD

## 上游锂盐

| 品种 | 现货均价(元/吨) | 周变化 | 月变化 | 备注 |
|------|----------------|--------|--------|------|
| 电池级碳酸锂 | XXXXX | ±X.X% | ±X.X% | Mysteel |
| 工业级碳酸锂 | XXXXX | ±X.X% | ±X.X% | |
| 氢氧化锂 | XXXXX | ±X.X% | ±X.X% | |
| 碳酸锂期货(主力) | XXXXX | ±X.X% | ±X.X% | 广期所 |

## 四大材料

| 品种 | 现货均价 | 单位 | 周变化 | 备注 |
|------|---------|------|--------|------|
| 磷酸铁锂(动力型) | XXXXX | 元/吨 | ±X.X% | |
| 三元NCM523 | XXXXX | 元/吨 | ±X.X% | |
| 三元NCM811 | XXXXX | 元/吨 | ±X.X% | |
| 人造石墨负极 | XXXXX | 元/吨 | ±X.X% | |
| 六氟磷酸锂 | XXXXX | 元/吨 | ±X.X% | |
| 电解液 | XXXXX | 元/吨 | ±X.X% | |
| 湿法隔膜(16μm) | X.XX | 元/m² | ±X.X% | |
| VC(碳酸亚乙烯酯) | XXXXX | 元/吨 | ±X.X% | |

## 关联品种

| 品种 | 价格 | 周变化 | 影响 |
|------|------|--------|------|
| 钴(MB标准级) | XX美元/磅 | ±X.X% | 三元正极成本 |
| 镍(LME) | XXXXX美元/吨 | ±X.X% | 高镍正极成本 |
| 针状焦 | XXXXX元/吨 | ±X.X% | 人造石墨成本 |
```

---

## 维护规则

| 文件 | 更新频率 | 说明 |
|------|---------|------|
| `daily-feed.md` | 每日追加 | 超过 7 天的内容移除 |
| `price-tracker.md` | 交易日收盘后 | 碳酸锂数据优先 |
| `supply-demand.md` | 每月 | 碳酸锂全球供需平衡表 |
| `capacity-pipeline.md` | 每月初 | 新增投产信息随时更新 |
| `chain-analysis/` | 有重大变化时 | 各环节深度分析 |
| `research-notes.md` | 每月 | 通过 research-gateway search_report 搜索更新 |
| `event-archive.md` | 即时 | 重大事件立即记录 |
