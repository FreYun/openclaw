#!/usr/bin/env python3
"""
催化剂分析器 — 从 FinRobot CatalystAnalyzer 提取，增加中英文双语关键词
用法: echo '{"news_data": [...], "ticker": "NVDA", "company_name": "NVIDIA"}' | python3 catalyst.py

输入 JSON:
  news_data: [{"title": "...", "text": "...", "publishedDate": "2026-03-20", "site": "Reuters"}, ...]
  ticker: str
  company_name: str (optional)

输出 JSON:
  catalysts: {positive: [...], negative: [...], neutral: [...]}
  top5: Top 5 (按|weighted_impact|排序)
  summary: markdown 文本
  stats: {total, positive, negative, neutral}
"""
import sys, json

# ─── 中英文双语关键词 ───
CATALYST_KEYWORDS = {
    "product_launch": ["launch", "release", "unveil", "introduce", "new product",
                       "debut", "rollout", "发布", "上线", "推出", "亮相", "新品"],
    "earnings": ["earnings", "quarterly results", "financial results", "revenue",
                 "profit", "guidance", "forecast", "outlook",
                 "业绩", "财报", "营收", "利润", "指引", "预期"],
    "regulatory": ["fda", "approval", "regulation", "compliance", "lawsuit",
                   "investigation", "antitrust", "settlement",
                   "批准", "合规", "诉讼", "反垄断", "监管", "审批"],
    "acquisition": ["acquire", "merger", "acquisition", "buyout", "deal",
                    "partnership", "joint venture", "stake",
                    "收购", "合并", "并购", "合资", "入股", "战略合作"],
    "management": ["ceo", "cfo", "executive", "leadership", "board",
                   "appointment", "resignation", "restructuring",
                   "高管", "任命", "辞职", "换帅", "重组", "管理层"],
    "market": ["market share", "expansion", "growth", "competition", "pricing",
               "demand", "supply", "市场份额", "扩张", "竞争", "定价", "供需"],
}

ANALYST_POS = ["initiates coverage", "upgrades to", "raises target", "overweight",
               "buy rating", "outperform rating", "top pick",
               "首次覆盖", "上调评级", "上调目标价", "买入", "增持"]
ANALYST_NEG = ["downgrades to", "cuts target", "lowers target", "underweight",
               "sell rating", "underperform rating",
               "下调评级", "下调目标价", "卖出", "减持"]

SENT_POS = ["growth", "increase", "beat", "exceed", "strong", "upgrade", "success",
            "win", "gain", "improve", "record", "outperform", "bullish",
            "增长", "超预期", "强劲", "突破", "上调", "创新高", "看多"]
SENT_NEG = ["decline", "decrease", "miss", "weak", "downgrade", "loss", "fail",
            "drop", "concern", "risk", "underperform", "bearish", "recall",
            "下滑", "不及预期", "疲软", "下调", "风险", "召回", "看空"]

IMPACT_HIGH = {"earnings", "acquisition", "regulatory"}
IMPACT_MED = {"product_launch", "management"}
BASE_PROB = {"earnings": 0.95, "product_launch": 0.70, "regulatory": 0.50,
             "acquisition": 0.40, "management": 0.60, "market": 0.50, "other": 0.50}
IMPACT_SCORES = {"high": 3, "medium": 2, "low": 1}
SENT_MULT = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}


def classify_event(text):
    tl = text.lower()
    for etype, kws in CATALYST_KEYWORDS.items():
        if any(kw in tl for kw in kws):
            return etype
    return "other"

def analyze_sentiment(text):
    tl = text.lower()
    for p in ANALYST_POS:
        if p in tl:
            return "positive"
    for p in ANALYST_NEG:
        if p in tl:
            return "negative"
    pc = sum(1 for kw in SENT_POS if kw in tl)
    nc = sum(1 for kw in SENT_NEG if kw in tl)
    if pc > nc:
        return "positive"
    if nc > pc:
        return "negative"
    return "neutral"

def impact_level(etype):
    if etype in IMPACT_HIGH:
        return "high"
    if etype in IMPACT_MED:
        return "medium"
    return "low"

def estimate_prob(etype, source):
    p = BASE_PROB.get(etype, 0.50)
    sl = source.lower()
    if any(kw in sl for kw in ["official", "company", "公告", "官方"]):
        p = min(p + 0.2, 1.0)
    return p

def is_relevant(title, text, ticker, company_name):
    terms = [ticker.upper()]
    if company_name:
        terms.append(company_name.lower())
        skip = {"inc", "inc.", "corp", "corp.", "ltd", "ltd.", "co", "co.",
                "the", "and", "of", "group", "holdings", "plc"}
        for w in company_name.split():
            if w.lower() not in skip and len(w) > 2:
                terms.append(w.lower())
    tl = title.lower()
    xl = (text[:500] if text else "").lower()
    return any(t.lower() in tl or t.lower() in xl for t in terms)

def process(data):
    news = data.get("news_data", [])
    ticker = data.get("ticker", "")
    cname = data.get("company_name", "")

    catalysts = []
    for art in news:
        title = art.get("title", "")
        text = art.get("text", "")
        date = art.get("publishedDate", "")[:10]
        source = art.get("site", "")
        if not is_relevant(title, text, ticker, cname):
            continue
        combined = f"{title} {text}"
        et = classify_event(combined)
        sent = analyze_sentiment(combined)
        il = impact_level(et)
        prob = estimate_prob(et, source)
        if et == "other" and il != "high":
            continue
        score = IMPACT_SCORES[il] * prob * SENT_MULT[sent]
        catalysts.append({
            "event_type": et,
            "description": title[:200] if title else text[:200],
            "date": date,
            "impact_level": il,
            "probability": round(prob, 2),
            "sentiment": sent,
            "source": source,
            "weighted_impact": round(score, 3),
        })

    catalysts.sort(key=lambda c: abs(c["weighted_impact"]), reverse=True)

    categorized = {"positive": [], "negative": [], "neutral": []}
    for c in catalysts:
        categorized[c["sentiment"]].append(c)

    top5 = catalysts[:5]

    # Generate summary
    parts = [f"## {ticker} 催化剂分析\n"]
    if categorized["positive"]:
        parts.append("### 正面催化剂（上行潜力）")
        for c in categorized["positive"][:5]:
            et_label = c["event_type"].replace("_", " ").title()
            parts.append(f"- **{et_label}** ({c['date']}): {c['description']}")
            parts.append(f"  影响:{c['impact_level']} | 概率:{c['probability']*100:.0f}% | 评分:{c['weighted_impact']:+.2f}")
        parts.append("")
    if categorized["negative"]:
        parts.append("### 风险催化剂（下行风险）")
        for c in categorized["negative"][:5]:
            et_label = c["event_type"].replace("_", " ").title()
            parts.append(f"- **{et_label}** ({c['date']}): {c['description']}")
            parts.append(f"  影响:{c['impact_level']} | 概率:{c['probability']*100:.0f}% | 评分:{c['weighted_impact']:+.2f}")
        parts.append("")
    if categorized["neutral"]:
        parts.append("### 待观察事件")
        for c in categorized["neutral"][:3]:
            parts.append(f"- {c['description']} ({c['date']})")

    return {
        "catalysts": categorized,
        "top5": top5,
        "summary": "\n".join(parts),
        "stats": {
            "total": len(catalysts),
            "positive": len(categorized["positive"]),
            "negative": len(categorized["negative"]),
            "neutral": len(categorized["neutral"]),
        },
    }

def main():
    data = json.load(sys.stdin)
    result = process(data)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
