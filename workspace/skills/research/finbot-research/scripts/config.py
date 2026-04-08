#!/usr/bin/env python3
"""公共配置：路径、默认参数"""
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = Path(os.environ.get("CHART_OUTPUT_DIR", "/tmp/equity-charts"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 估值默认参数
DEFAULT_DCF_ASSUMPTIONS = {
    "growth_rate_1_5": 0.10,
    "growth_rate_6_10": 0.05,
    "terminal_growth": 0.025,
    "wacc": 0.10,
    "projection_years": 10,
}

# 敏感性分析默认参数
DEFAULT_SENSITIVITY = {
    "revenue_range": [-0.05, 0.05],
    "margin_range": [-0.02, 0.02],
    "steps": 5,
}

# 催化剂中英文关键词
CATALYST_KEYWORDS = {
    "product_launch": [
        "launch", "release", "unveil", "introduce", "new product",
        "announcement", "debut", "rollout",
        "发布", "上线", "推出", "亮相", "新品",
    ],
    "earnings": [
        "earnings", "quarterly results", "financial results", "revenue",
        "profit", "guidance", "forecast", "outlook",
        "业绩", "财报", "营收", "利润", "指引", "预期",
    ],
    "regulatory": [
        "fda", "approval", "regulation", "compliance", "lawsuit",
        "investigation", "antitrust", "settlement",
        "批准", "合规", "诉讼", "反垄断", "监管", "审批",
    ],
    "acquisition": [
        "acquire", "merger", "acquisition", "buyout", "deal",
        "partnership", "joint venture", "stake",
        "收购", "合并", "并购", "合资", "入股", "战略合作",
    ],
    "management": [
        "ceo", "cfo", "executive", "leadership", "board",
        "appointment", "resignation", "restructuring",
        "高管", "任命", "辞职", "换帅", "重组", "管理层",
    ],
    "market": [
        "market share", "expansion", "growth", "competition",
        "pricing", "demand", "supply",
        "市场份额", "扩张", "竞争", "定价", "供需",
    ],
}

SENTIMENT_POSITIVE = [
    "growth", "increase", "beat", "exceed", "strong", "upgrade",
    "success", "win", "gain", "improve", "record", "outperform",
    "bullish", "top pick", "overweight",
    "增长", "超预期", "强劲", "突破", "上调", "创新高", "看多",
]

SENTIMENT_NEGATIVE = [
    "decline", "decrease", "miss", "weak", "downgrade", "loss",
    "fail", "drop", "concern", "risk", "underperform", "bearish",
    "recall", "investigation", "warning",
    "下滑", "不及预期", "疲软", "下调", "风险", "召回", "看空",
]

ANALYST_POSITIVE_PATTERNS = [
    "initiates coverage", "upgrades to", "raises target",
    "overweight", "buy rating", "outperform rating", "top pick",
    "首次覆盖", "上调评级", "上调目标价", "买入", "增持",
]

ANALYST_NEGATIVE_PATTERNS = [
    "downgrades to", "cuts target", "lowers target",
    "underweight", "sell rating", "underperform rating",
    "下调评级", "下调目标价", "卖出", "减持",
]
