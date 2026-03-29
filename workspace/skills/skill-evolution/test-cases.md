# 测试用例表

> 每个可安全进化的 skill 对应一个测试任务。测试 bot 应装备了对应线上版 skill。

## 知识型 / 写作类

| skill | 测试任务 | 预期结果 | 测试 bot |
|-------|---------|---------|---------|
| xhs-writing | 写一篇 200 字黄金投资短评（不发布，只输出文本） | 标题≤20字、符合排版规范、有互动引导 | 任意 frontline bot |
| record-insight | 根据今天的工作内容写一段复盘洞察 | 结构化输出、有反思和改进点 | 任意 frontline bot |
| self-review | 复盘昨天的操作，列出做得好和待改进的 | 结构化复盘、自我评估 | 任意 frontline bot |

## 分析型 / 研究类

| skill | 测试任务 | 预期结果 | 测试 bot |
|-------|---------|---------|---------|
| research-stock | 查询 600519.SH（贵州茅台）的当前估值和财务概况 | 返回 PE/PB/市值/ROE 等数据 | 装备 research 的 bot |
| sector-pulse | 分析半导体行业近一周动态 | 结构化行业分析报告 | 装备 research 的 bot |
| technical-analyst | 分析上证指数最近的日线走势形态 | 技术面判断（支撑/阻力/趋势） | 装备 research 的 bot |
| market-environment-analysis | 分析当前 A 股整体市场环境 | 宏观+资金面+情绪面综合判断 | 装备 research 的 bot |
| earnings-digest | 摘要贵州茅台最新一期财报要点 | 营收/利润/现金流关键指标 | 装备 research 的 bot |
| news-factcheck | 核查 "央行本周降准0.5个百分点" 这条消息 | 真实性判断 + 来源引用 | 任意 bot |
| flow-watch | 查看今日北向资金流向 | 净流入/流出数据 + 行业分布 | 装备 research 的 bot |
| stock-watcher | 监控 600519.SH 今日异动 | 涨跌幅/成交量变化/异常信号 | 装备 research 的 bot |
| deepresearch | 对"新能源车补贴政策变化"做一次简要深度研究 | 政策梳理 + 影响分析 | 装备 research 的 bot |

## 角色型

| skill | 测试任务 | 预期结果 | 测试 bot |
|-------|---------|---------|---------|
| frontline | 描述你作为前台内容创作者的职责边界 | 准确复述角色定义 | 任意 frontline bot |
| management | 描述你作为管理者的职责边界 | 准确复述角色定义 | mag1 |
| ops | 描述你作为运维的职责边界 | 准确复述角色定义 | sys1 |

## 工具指南型

| skill | 测试任务 | 预期结果 | 测试 bot |
|-------|---------|---------|---------|
| research-mcp | 列出 research-mcp 提供的主要工具和用法 | 准确列出工具清单 | 装备 research 的 bot |
| browser-base | 描述浏览器操作的铁律和关闭规则 | 准确复述操作规范 | 任意 bot |
| compliance-review | 描述合规审核的流程和判定标准 | 准确复述流程 | sys1 |

---

## 注意事项

- 所有测试任务都是**只读/分析/生成文本**，不触发任何外部操作
- 测试 bot 执行时读的是**沙盒路径**的 SKILL.md，不是自己装备的线上版
- 角色型 skill 的测试主要验证描述准确性，不需要执行复杂任务
