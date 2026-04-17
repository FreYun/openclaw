# 研报发现与全文阅读协议

**这是 industry-deep-dive 的基石。** L1-L5 的提取首先从这里读到的研报全文中获取，search API 只做补充。

> **⚠️ 前置步骤**：本协议使用 `research_search`、`news_search` 等 research-mcp 工具。如果你不确定如何调用这些工具，先 **Read `research-mcp/SKILL.md`** 了解调用方式。`research_search` 不是 web_search——它是 research-mcp 的专用研报搜索工具，能返回研报 ID 用于下载 PDF 全文，web_search 做不到这一点。

## 1. 发现深度报告

**必须用 research-mcp 的 `research_search` 工具**（不是 web_search）：

```bash
npx mcporter call 'research-mcp.research_search' "query={行业} 产业链 深度报告" "top_k=5" "search_day_ago=30"
npx mcporter call 'research-mcp.research_search' "query={行业} 行业研究 年度策略" "top_k=3" "search_day_ago=30"
```

> ⚠️ `search_day_ago` 上限 30 天。深度报告超过 30 天的用 `web_search("{行业} 深度研究报告 PDF site:eastmoney.com")` 补充发现。
> ⛔ **禁止用 web_search 替代 research_search**——web_search 搜不到研报 ID，只有 research_search 能返回可用于构建 PDF 下载链接的研报 ID。

返回结果包含**研报 ID、机构名、摘要、评分**。筛选优先级：
1. 行业深度报告 > 行业点评/快报 > 个股研报
2. 头部券商（中信/中金/华泰/国泰君安/招商/海通/广发等）> 中小券商
3. 近期 > 远期

选出 **2-3 篇**，记录研报 ID 和机构名。

## 2. 下载与验证

```bash
mkdir -p /tmp/deep-dive-pdf

curl -sSL "https://pdf.dfcfw.com/pdf/H3_{研报ID}_1.pdf" \
  -o /tmp/deep-dive-pdf/{研报ID}.pdf --max-time 30

# 验证（个别研报链接本身可能失效）
size=$(stat -c%s /tmp/deep-dive-pdf/{研报ID}.pdf)
mime=$(file -b /tmp/deep-dive-pdf/{研报ID}.pdf)
# size < 10240 或 mime 不含 "PDF document" → 链接无效，跳过换下一篇
```

## 3. 提取与确认

```bash
pdftotext -f 1 -l 30 -layout /tmp/deep-dive-pdf/{研报ID}.pdf -
```

确认：首页机构署名 vs 搜索返回的机构名（必须一致）、报告标题是该行业深度报告、目录结构。不匹配 → 丢弃换下一篇。

## 4. 通读标注

按以下维度在研报中定位信息，为 L1-L5 提取做准备：

| 维度 | 研报中寻找 |
|------|----------|
| 产业链结构（→L1） | "产业链概览"、"行业全景" |
| 核心公司（→L1） | "受益标的"、"投资建议"、"重点公司" |
| 供需分析（→L2） | "供给端/需求端"、"产能"、"开工率" |
| 价格数据（→L2） | "景气跟踪"、"价格周报" |
| 竞争格局（→L3） | "竞争格局"、"市场份额"、"CR5" |
| 政策（→L4） | "政策梳理"、"监管动态" |
| 估值（→L5） | "估值对比"、"投资建议" |

**完成标志**：能用自己的话描述产业链结构、当前供需、核心玩家。

## 5. 补充阅读

| 情况 | 处理 |
|------|------|
| 选中的研报链接均无效 | 回步骤 1 扩大 top_k 重试 → `web_search` 找公开研报页面 → 降级为纯搜索模式（标注 `[未获取研报全文]`） |
| 只覆盖部分环节 | `research_search("{行业} {缺失环节} 深度")` 补找 |
| 研报太老（>6 月） | 框架性知识可用，供需/价格用 news_search 更新 |

## 6. 清理

```bash
rm -rf /tmp/deep-dive-pdf
```
