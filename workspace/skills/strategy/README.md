# strategy/ skill 组 — 目录约定

这里住着量化策略相关的 skill。为了避免 skill 越用越臃肿 ("历史包袱"问题), 所有 strategy 组的 skill 都遵循以下约定。

## 顶层布局

```
strategy/
├── _lib/                      共享模块 (market.db schema + 连接帮助), 所有 strategy 代码可 import
├── README.md                  ← 本文件
└── <skill-name>/              纯 skill 定义目录, 不再住代码
    ├── SKILL.md               skill 行为说明 (给 bot 看的, 指向 /scripts/ 下的实际命令)
    ├── skill.json             skill 元数据
    ├── references/            稳定规则 / 参考文档 (只存长期有效的)
    └── memory/experiments/    ⚠️ 归档区: 一次性工具 / 实验报告 (随时 rm -rf)

# 代码与 cron 脚本统一住在仓库根 /home/rooot/.openclaw/scripts/:
scripts/
├── daily-regime-pipeline.sh   工作日 16:00 cron 入口
├── market-regime/             regime 数据管道 (不是 skill, 是后台管道)
│   └── scripts/backfill/replay.py
├── s5/                        S5 战法的代码实现
│   ├── select.py / verify.py / render.py / backtest.py / data_fetcher.py / ...
│   └── tests/
└── s5-prewarm.py              cron step 3, 调用 s5/data_fetcher 预热 cache
```

## 铁律

1. **skill 目录不住代码**: `workspace/skills/strategy/<skill>/` 只放 SKILL.md / skill.json / references/ / memory/experiments/. 实际代码放 `/scripts/<skill>/`, SKILL.md 通过命令示例指向那里.
   - 为什么: skill = "给 bot 的说明书", 代码是实现细节
   - bot 读 SKILL.md 就知道"cd 哪个目录跑什么命令", 不需要也不应该在 skill 目录里翻代码

2. **`references/` 只放稳定规则**: mapping / scoring / playbook / 示例案例这类"长期有效"的文档.
   - ❌ 实验报告 (`xxx_2026-04.md`) 不进 references/ — 它们属于 `memory/experiments/reports/`
   - ❌ HTML 图表不进 references/
   - ✅ `regime-examples.md` 这类"规则的正例/反例"可以留下, 因为它跟 mapping 一体

3. **`/scripts/<skill>/` 只放生产代码**: 被 cron 或用户每天调的入口 + 其依赖.
   - ❌ 一次性迁移工具 (`migrate.py`) 不留在 scripts/ — 跑完归档到 skill 的 `memory/experiments/`
   - ❌ 回测/分析脚本 (`*_backtest.py` / `simulate_*.py` / `generate_*_report.py`) 不留在 scripts/

4. **`memory/` 里任何东西都应该可以随时 `rm -rf`**: 归档的实验丢了只少一份"历史证据"但不影响生产.
   - 这意味着: 生产代码不能依赖 memory/ 里的文件**存在**
   - 规则文档被其它 skill 引用要走 `references/`, 不走 `memory/`

5. **Python artifacts 不进仓库**: `__pycache__/` 和 `.pytest_cache/` 在项目根 `.gitignore` 里已经 block, 别手动 track 进来.

## 新增实验的流程

跑一个新的策略回测 / 信号评估 / 数据分析?

1. 在 `<skill>/memory/experiments/` 下建脚本和报告
2. 跑完产出结论后, 在 `memory/experiments/README.md` 里写一句话记录:
   - **目的**: 想验证什么
   - **结论**: 跑出了什么 (采用/证伪/待定)
   - **去向**: 结论在哪里落地 (比如"采纳到 `references/mapping.md` 第 X 节")
3. 以后这个实验不再需要复用, 直接 `rm` 整个文件就行 — 结论已经落地到 references/ 或代码里

## 跨 skill 共享

- 共享 schema + 连接帮助放 `strategy/_lib/db.py`
- 共享规则表 (如 `regime_code → playbook` 的映射) 住在产生它的模块的 `references/` + 对应 py, 其他脚本 `sys.path.insert` 后 import 复用
- **共享运行数据走 market.db 这张大共享 DB**, 不走跨目录读文件

## 当前 strategy 下的 skill

| skill 目录 | 代码位置 | 是否在生产链路 |
|-----------|---------|---------------|
| `s5-dragon-pullback/` | `/home/rooot/.openclaw/scripts/s5/` | ✅ |

## 相关的非 skill 组件 (cron 管道)

- `/home/rooot/.openclaw/scripts/daily-regime-pipeline.sh` — 工作日 16:00 cron 入口
- `/home/rooot/.openclaw/scripts/market-regime/` — regime 数据管道 + 打分规则库. 不是 skill (没有 bot-invocable 入口)
- `/home/rooot/.openclaw/scripts/s5-prewarm.py` — S5 cache 预热 (cron step 3)
