"""
每日复盘数据自动化采集 — 入口脚本

用法:
    python daily_review.py              # 获取今日数据
    python daily_review.py 2026-03-14   # 获取指定日期数据

输出:
    workspace/review-output/复盘_YYYY-MM-DD.md
"""

import sys
import os
import logging
import traceback
from datetime import datetime

# 项目路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)
WORKSPACE_DIR = os.path.dirname(SCRIPTS_DIR)
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "review-output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")

sys.path.insert(0, SCRIPTS_DIR)
from config import get_tushare_pro

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging(date_str):
    """配置日志"""
    log_file = os.path.join(LOG_DIR, f"review_{date_str}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def is_trading_day(date_str):
    """检查是否为交易日"""
    try:
        pro = get_tushare_pro()
        date_fmt = date_str.replace("-", "")
        cal = pro.trade_cal(
            exchange="SSE", start_date=date_fmt, end_date=date_fmt
        )
        if len(cal) > 0 and cal.iloc[0]["is_open"] == 1:
            return True
        return False
    except Exception as e:
        logging.warning(f"交易日历查询失败: {e}，默认继续执行")
        # 周末直接跳过
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.weekday() < 5


def run_module(name, func, date_str):
    """安全执行单个模块"""
    try:
        logging.info(f"[开始] {name}")
        result = func(date_str)
        logging.info(f"[完成] {name}")
        return result
    except Exception as e:
        logging.error(f"[失败] {name}: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}


def main():
    # 解析日期参数
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    setup_logging(date_str)
    logging.info(f"===== 每日复盘数据采集 {date_str} =====")

    # 交易日检查
    if not is_trading_day(date_str):
        logging.info(f"{date_str} 不是交易日，跳过")
        print(f"{date_str} 不是交易日，跳过")
        return

    # 延迟导入各模块（避免启动时全部加载）
    from review.mod_market_overview import fetch_market_overview
    from review.mod_intraday_profile import fetch_intraday_profile
    from review.mod_sentiment import fetch_sentiment
    from review.mod_sector_rotation import fetch_sector_rotation
    from review.mod_limit_up_tracking import fetch_limit_up_data
    from review.mod_capital_flow import fetch_capital_flow
    from review.mod_shareholder import fetch_shareholder_activity
    from review.mod_equity_risk_premium import fetch_erp
    from review.markdown_renderer import render_markdown

    # 按顺序执行各模块
    results = {}

    # 1. 市场全景（先跑，提取 breadth 供下游复用）
    results["market_overview"] = run_module("市场全景", fetch_market_overview, date_str)
    shared_breadth = None
    mo = results.get("market_overview", {})
    if isinstance(mo, dict) and "error" not in mo:
        shared_breadth = mo.get("breadth")

    # 2. 其余模块（情绪温度计使用共享 breadth）
    modules = [
        ("日内画像", fetch_intraday_profile),
        ("情绪温度计", lambda d: fetch_sentiment(d, shared_breadth=shared_breadth)),
        ("板块轮动", fetch_sector_rotation),
        ("连板前瞻", fetch_limit_up_data),
        ("资金与流动性", fetch_capital_flow),
        ("股东行为", fetch_shareholder_activity),
        ("股债收益比", fetch_erp),
    ]

    for name, func in modules:
        # 从 func name 提取 key，lambda 没有好名字则用模块名映射
        if hasattr(func, '__name__') and func.__name__ != '<lambda>':
            key = func.__name__.replace("fetch_", "")
        else:
            key = {"情绪温度计": "sentiment"}.get(name, name)
        results[key] = run_module(name, func, date_str)

    # 渲染 Markdown
    logging.info("[开始] 渲染 Markdown")
    md_content = render_markdown(date_str, results)

    output_path = os.path.join(OUTPUT_DIR, f"复盘_{date_str}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logging.info(f"[完成] 输出文件: {output_path}")
    print(f"\n复盘文件已生成: {output_path}")

    # 统计成功/失败
    ok = sum(1 for v in results.values() if "error" not in v)
    fail = sum(1 for v in results.values() if "error" in v)
    logging.info(f"===== 完成: {ok} 成功, {fail} 失败 =====")


if __name__ == "__main__":
    main()
