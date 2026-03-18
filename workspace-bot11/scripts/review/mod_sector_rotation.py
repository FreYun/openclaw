"""
模块：板块轮动
- 行业板块 TOP5 涨/跌
- 概念板块 TOP5 涨/跌
- akshare 为主
"""

import logging
import akshare as ak


def _fetch_industry_boards():
    """获取行业板块排名"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return None

        df = df.sort_values("涨跌幅", ascending=False).reset_index(drop=True)

        def extract(row):
            return {
                "name": row.get("板块名称", ""),
                "pct_chg": float(row.get("涨跌幅", 0)),
                "amount": float(row.get("成交额", 0)),
                "leader": row.get("领涨股票", ""),
                "leader_pct": float(row.get("涨跌幅.1", row.get("领涨股票-涨跌幅", 0)) if "涨跌幅.1" in row.index or "领涨股票-涨跌幅" in row.index else 0),
                "up_count": int(row.get("上涨家数", 0)),
                "down_count": int(row.get("下跌家数", 0)),
            }

        top5 = [extract(df.iloc[i]) for i in range(min(5, len(df)))]
        bottom5 = [extract(df.iloc[-(i + 1)]) for i in range(min(5, len(df)))]
        bottom5.reverse()

        return {"top": top5, "bottom": bottom5, "total": len(df)}
    except Exception as e:
        logging.warning(f"获取行业板块失败: {e}")
        return None


def _fetch_concept_boards():
    """获取概念板块排名"""
    try:
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            return None

        df = df.sort_values("涨跌幅", ascending=False).reset_index(drop=True)

        def extract(row):
            return {
                "name": row.get("板块名称", ""),
                "pct_chg": float(row.get("涨跌幅", 0)),
                "leader": row.get("领涨股票", ""),
            }

        top5 = [extract(df.iloc[i]) for i in range(min(5, len(df)))]
        bottom5 = [extract(df.iloc[-(i + 1)]) for i in range(min(5, len(df)))]
        bottom5.reverse()

        return {"top": top5, "bottom": bottom5, "total": len(df)}
    except Exception as e:
        logging.warning(f"获取概念板块失败: {e}")
        return None


def fetch_sector_rotation(date_str):
    """主函数：获取板块轮动数据"""
    industry = _fetch_industry_boards()
    concept = _fetch_concept_boards()

    return {
        "industry": industry,
        "concept": concept,
    }
