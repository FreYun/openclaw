"""
Markdown 渲染器
将各模块数据组装为公众号复盘文章 Markdown
"""

from datetime import datetime


def _fmt(val, fmt=".2f", default="—"):
    """安全格式化数值"""
    if val is None:
        return default
    try:
        return f"{float(val):{fmt}}"
    except (ValueError, TypeError):
        return default


def _sign(val, fmt=".2f"):
    """带正负号的格式化"""
    if val is None:
        return "—"
    try:
        v = float(val)
        return f"{v:+{fmt}}"
    except (ValueError, TypeError):
        return "—"


def _section_error(title):
    """模块数据获取失败时的占位"""
    return f"## {title}\n\n> 数据获取失败，请检查日志\n"


# ============================================================
# 各段落渲染
# ============================================================

def render_title(date_str, overview):
    """标题 & 导语"""
    lines = [f"# 每日复盘 | {date_str}\n"]

    if "error" in overview:
        lines.append("> 市场数据获取失败\n")
        return "\n".join(lines)

    indices = overview.get("indices", {})
    breadth = overview.get("breadth", {})

    # 构造导语
    sh = indices.get("上证指数", {})
    cy = indices.get("创业板指", {})
    total_amount = breadth.get("total_amount", 0) if breadth else 0
    up = breadth.get("up", 0) if breadth else 0
    down = breadth.get("down", 0) if breadth else 0

    lead = f"> 今日三大指数"
    sh_pct = sh.get("pct_chg", 0)
    cy_pct = cy.get("pct_chg", 0)

    if sh_pct > 0 and cy_pct > 0:
        lead += "集体上涨"
    elif sh_pct < 0 and cy_pct < 0:
        lead += "集体下跌"
    else:
        lead += "涨跌分化"

    lead += f"，上证 {_sign(sh_pct)}%，创业板 {_sign(cy_pct)}%"
    lead += f"，成交额 {_fmt(total_amount, '.0f')} 亿"
    lead += f"。全市场 {up} 家上涨、{down} 家下跌。"

    lines.append(lead)
    lines.append("")
    return "\n".join(lines)


def render_market_overview(overview, intraday=None):
    """市场全景"""
    if "error" in overview:
        return _section_error("一、市场全景")

    lines = ["## 一、市场全景\n"]
    indices = overview.get("indices", {})
    breadth = overview.get("breadth", {})
    intraday_indices = intraday.get("indices", {}) if intraday and "error" not in intraday else {}

    # 指数表格 — 有日内数据时增加振幅和高低点时间列
    has_intraday = bool(intraday_indices)
    lines.append("### 指数表现\n")
    if has_intraday:
        lines.append("| 指数 | 收盘 | 涨跌幅 | 振幅 | 高点时间 | 低点时间 |")
        lines.append("|------|------|--------|------|---------|---------|")
    else:
        lines.append("| 指数 | 收盘 | 涨跌幅 |")
        lines.append("|------|------|--------|")

    for name in ["上证指数", "深证成指", "创业板指", "沪深300"]:
        d = indices.get(name, {})
        close = _fmt(d.get("close"), ".2f")
        pct = _sign(d.get("pct_chg")) + "%" if d.get("pct_chg") is not None else "—"
        if has_intraday:
            intra = intraday_indices.get(name, {})
            amp = _fmt(intra.get("amplitude"), ".2f") + "%" if intra.get("amplitude") is not None else "—"
            ht = intra.get("high_time", "—")
            lt = intra.get("low_time", "—")
            lines.append(f"| {name} | {close} | {pct} | {amp} | {ht} | {lt} |")
        else:
            lines.append(f"| {name} | {close} | {pct} |")

    # 涨跌家数
    if breadth:
        lines.append(f"\n### 市场宽度\n")
        lines.append(f"- 上涨：**{breadth.get('up', 0)}** 家 / 下跌：**{breadth.get('down', 0)}** 家 / 平盘：{breadth.get('flat', 0)} 家")
        lines.append(f"- 涨停：**{breadth.get('limit_up', 0)}** 家 / 跌停：**{breadth.get('limit_down', 0)}** 家")
        lines.append(f"- 全市场成交额：**{_fmt(breadth.get('total_amount'), '.0f')}** 亿")

    lines.append("")
    return "\n".join(lines)


def render_intraday_profile(intraday):
    """日内画像"""
    if not intraday or "error" in intraday:
        return ""

    lines = ["### 日内画像\n"]

    # 叙述段落
    narrative = intraday.get("narrative", "")
    if narrative:
        lines.append(f"> {narrative}\n")

    # 分段表格 (基于上证指数)
    sh = intraday.get("indices", {}).get("上证指数")
    if sh:
        lines.append("| 阶段 | 区间涨跌 | 说明 |")
        lines.append("|------|---------|------|")

        gap = sh.get("open_gap_pct")
        if gap is not None:
            gap_label = "高开" if gap >= 0.3 else ("低开" if gap <= -0.3 else "平开")
            lines.append(f"| 开盘跳空 | {_sign(gap)}% | {gap_label} |")

        morning_pct = sh.get("morning_pct")
        if morning_pct is not None:
            lines.append(f"| 上午 (9:30-11:30) | {_sign(morning_pct)}% | |")

        afternoon_pct = sh.get("afternoon_pct")
        if afternoon_pct is not None:
            lines.append(f"| 下午 (13:00-15:00) | {_sign(afternoon_pct)}% | |")

        last30 = sh.get("last30_pct")
        if last30 is not None:
            tail_label = "翘尾" if last30 > 0.15 else ("跳水" if last30 < -0.15 else "平稳")
            lines.append(f"| 尾盘 (14:30-15:00) | {_sign(last30)}% | {tail_label} |")

        # 量能分布
        vol_pct = sh.get("morning_vol_pct")
        if vol_pct is not None:
            afternoon_vol_pct = round(100 - vol_pct, 1)
            lines.append(f"\n**量能分布**：上午 **{vol_pct:.0f}%** / 下午 **{afternoon_vol_pct:.0f}%**")

    lines.append("")
    return "\n".join(lines)


def render_sentiment(sentiment):
    """情绪温度计"""
    if "error" in sentiment:
        return _section_error("二、情绪温度计")

    lines = ["## 二、情绪温度计\n"]

    score = sentiment.get("score", 50)
    label = sentiment.get("label", "中性")
    profit = sentiment.get("profit_effect", "未知")
    up_ratio = sentiment.get("up_ratio")
    lu_ld = sentiment.get("limit_up_down_ratio")

    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 情绪评分 | **{score}** / 100（{label}）|")
    lines.append(f"| 赚钱效应 | {profit} |")
    if up_ratio is not None:
        lines.append(f"| 上涨比例 | {_fmt(up_ratio, '.1f')}% |")
    if lu_ld:
        lines.append(f"| 涨停:跌停 | {lu_ld} |")

    # PCR 预留
    if sentiment.get("pcr"):
        lines.append(f"| 期权 PCR | {_fmt(sentiment['pcr'])} |")
    else:
        lines.append(f"| 期权 PCR | 数据暂缺 |")

    lines.append("")
    return "\n".join(lines)


def render_sector_rotation(sector):
    """板块轮动"""
    if "error" in sector:
        return _section_error("三、板块轮动")

    lines = ["## 三、板块轮动\n"]

    # 行业板块
    industry = sector.get("industry")
    if industry:
        lines.append("### 行业板块 TOP5\n")
        lines.append("| 排名 | 板块 | 涨跌幅 | 领涨股 |")
        lines.append("|------|------|--------|--------|")
        for i, item in enumerate(industry.get("top", [])[:5], 1):
            lines.append(f"| {i} | {item['name']} | {_sign(item['pct_chg'])}% | {item.get('leader', '')} |")

        lines.append(f"\n### 行业板块 后5\n")
        lines.append("| 排名 | 板块 | 涨跌幅 |")
        lines.append("|------|------|--------|")
        for i, item in enumerate(industry.get("bottom", [])[:5], 1):
            lines.append(f"| {i} | {item['name']} | {_sign(item['pct_chg'])}% |")

    # 概念板块
    concept = sector.get("concept")
    if concept:
        lines.append(f"\n### 概念板块 TOP5\n")
        lines.append("| 排名 | 概念 | 涨跌幅 | 领涨股 |")
        lines.append("|------|------|--------|--------|")
        for i, item in enumerate(concept.get("top", [])[:5], 1):
            lines.append(f"| {i} | {item['name']} | {_sign(item['pct_chg'])}% | {item.get('leader', '')} |")

        lines.append(f"\n### 概念板块 后5\n")
        lines.append("| 排名 | 概念 | 涨跌幅 |")
        lines.append("|------|------|--------|")
        for i, item in enumerate(concept.get("bottom", [])[:5], 1):
            lines.append(f"| {i} | {item['name']} | {_sign(item['pct_chg'])}% |")

    lines.append("")
    return "\n".join(lines)


def render_limit_up(limit_data):
    """连板 & 题材前瞻"""
    if "error" in limit_data:
        return _section_error("四、连板 & 题材前瞻")

    lines = ["## 四、连板 & 题材前瞻\n"]

    total = limit_data.get("total_limit_up", 0)
    max_c = limit_data.get("max_consecutive", 0)
    dist = limit_data.get("consecutive_dist", {})

    lines.append(f"- 今日涨停：**{total}** 家")
    lines.append(f"- 最高连板：**{max_c}** 板")

    # 连板分布
    if dist:
        dist_str = "、".join([f"{k}板 {v}家" for k, v in sorted(dist.items(), reverse=True) if k > 1])
        if dist_str:
            lines.append(f"- 连板分布：{dist_str}")

    # 高位连板股
    top = limit_data.get("top_consecutive", [])
    if top:
        high_board = [item for item in top if item.get("consecutive", 1) >= 2]
        if high_board:
            lines.append(f"\n### 连板股（2板及以上）\n")
            lines.append("| 代码 | 名称 | 连板 | 涨跌幅 | 封单(亿) | 首封时间 |")
            lines.append("|------|------|------|--------|---------|---------|")
            for item in high_board[:15]:
                # 封单金额：tushare 返回元，转为亿
                fd = item.get('fd_amount', 0)
                if fd > 1e6:
                    fd_str = f"{fd / 1e8:.2f}"
                else:
                    fd_str = f"{fd / 1e4:.0f}万"
                # 首封时间格式化：94004 → 09:40:04
                ft = str(item.get('first_time', ''))
                if ft and ft.isdigit() and len(ft) >= 5:
                    ft = ft.zfill(6)
                    ft = f"{ft[0:2]}:{ft[2:4]}:{ft[4:6]}"
                lines.append(
                    f"| {item.get('ts_code', '')} | {item.get('name', '')} "
                    f"| {item.get('consecutive', 1)}板 "
                    f"| {_sign(item.get('pct_chg'))}% "
                    f"| {fd_str} "
                    f"| {ft} |"
                )

    # 题材分布
    themes = limit_data.get("theme_dist", {})
    if themes:
        lines.append(f"\n### 涨停题材分布\n")
        lines.append("| 行业 | 涨停数 |")
        lines.append("|------|--------|")
        for industry, count in list(themes.items())[:8]:
            lines.append(f"| {industry} | {count} |")

    lines.append("")
    return "\n".join(lines)


def render_capital_flow(capital, shareholder, erp):
    """资金与流动性"""
    lines = ["## 五、资金与流动性\n"]

    # 北向资金
    if "error" not in capital:
        nb = capital.get("northbound")
        if nb:
            flow = nb.get("net_flow", 0)
            direction = "净流入" if flow > 0 else "净流出"
            lines.append(f"### 北向资金\n")
            lines.append(f"- {direction}：**{_sign(flow)}** 亿元")
        else:
            lines.append(f"### 北向资金\n")
            lines.append(f"- 数据暂缺")

        # 国债收益率
        bond = capital.get("bond_yield")
        if bond:
            lines.append(f"\n### 债券市场\n")
            lines.append(f"- 10年期国债收益率：**{_fmt(bond.get('yield_10y'), '.4f')}%**")
    else:
        lines.append("> 资金数据获取失败\n")

    # 股东行为
    if "error" not in shareholder:
        inc = shareholder.get("increase_count", 0)
        dec = shareholder.get("decrease_count", 0)
        level = shareholder.get("level", "")
        lines.append(f"\n### 重要股东行为\n")
        lines.append(f"- 拟增持：**{inc}** 家")
        lines.append(f"- 拟减持：**{dec}** 家")
        lines.append(f"- 减持区间：**{level}**")
    else:
        lines.append(f"\n### 重要股东行为\n")
        lines.append(f"> 数据获取失败")

    # 股债收益比
    if "error" not in erp:
        erp_val = erp.get("erp")
        pe_data = erp.get("csi300_pe")
        bond_10y = erp.get("bond_yield_10y")
        pct = erp.get("erp_percentile")

        lines.append(f"\n### 股债收益比\n")
        if pe_data:
            lines.append(f"- 沪深300 PE(TTM)：**{_fmt(pe_data.get('pe_ttm'))}**")
            lines.append(f"- 盈利收益率：**{_fmt(pe_data.get('earnings_yield'), '.2f')}%**")
        if bond_10y is not None:
            lines.append(f"- 10年国债收益率：**{_fmt(bond_10y, '.4f')}%**")
        if erp_val is not None:
            lines.append(f"- **股债收益比(ERP)：{_fmt(erp_val, '.2f')}%**")
        if pct is not None:
            lines.append(f"- 历史分位：**{_fmt(pct, '.1f')}%**（近3年）")
    else:
        lines.append(f"\n### 股债收益比\n")
        lines.append(f"> 数据获取失败")

    lines.append("")
    return "\n".join(lines)


def render_strategy_placeholder():
    """操作思路占位（需人工填写）"""
    return """## 六、操作思路 & 策略展望

<!-- TODO: 以下内容需要人工填写 -->

### 主线方向
- 方向：
- 逻辑：
- 参与建议：

### 机动方向（打野）
- 方向1：
- 方向2：

### 仓位建议
- 整体仓位：
- 策略要点：

### 明日关注
-

> **策略金句**：
"""


def render_disclaimer():
    """风险提示"""
    return """---

## 风险提示

- 以上内容仅为个人复盘记录，不构成任何投资建议
- 股市有风险，投资需谨慎
- 数据来源：akshare / tushare / 东方财富 / 中国债券信息网
"""


def render_validation(results):
    """数据交叉验证摘要"""
    validations = []

    for key, data in results.items():
        if isinstance(data, dict) and "_validation" in data:
            v = data["_validation"]
            if isinstance(v, dict):
                for name, detail in v.items():
                    if isinstance(detail, dict) and not detail.get("ok", True):
                        validations.append(
                            f"- **{name}**: akshare={detail.get('akshare')} vs tushare={detail.get('tushare')} (差异 {detail.get('diff_pct', 0):.2f}%)"
                        )

    if not validations:
        return ""

    lines = ["\n---\n", "<details>", "<summary>数据交叉验证警告</summary>\n"]
    lines.extend(validations)
    lines.append("\n</details>")
    return "\n".join(lines)


# ============================================================
# 主渲染函数
# ============================================================

def render_markdown(date_str, results):
    """将所有模块数据渲染为完整 Markdown"""
    overview = results.get("market_overview", {"error": "missing"})
    intraday = results.get("intraday_profile", {})
    sentiment = results.get("sentiment", {"error": "missing"})
    sector = results.get("sector_rotation", {"error": "missing"})
    limit_up = results.get("limit_up_data", results.get("limit_up", {"error": "missing"}))
    capital = results.get("capital_flow", {"error": "missing"})
    shareholder = results.get("shareholder_activity", results.get("shareholder", {"error": "missing"}))
    erp_data = results.get("erp", {"error": "missing"})

    sections = [
        render_title(date_str, overview),
        render_market_overview(overview, intraday),
        render_intraday_profile(intraday),
        render_sentiment(sentiment),
        render_sector_rotation(sector),
        render_limit_up(limit_up),
        render_capital_flow(capital, shareholder, erp_data),
        render_strategy_placeholder(),
        render_disclaimer(),
        render_validation(results),
    ]

    footer = f"\n---\n_生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n"
    sections.append(footer)

    return "\n".join(sections)
