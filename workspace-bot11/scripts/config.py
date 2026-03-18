"""
小奶龙的统一配置文件
所有脚本通过 from config import * 引入，Token 和通用参数只写这一处。
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

# ===== Tushare =====
TUSHARE_TOKEN = "ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4"

# ===== 通用设置 =====
PREFERRED_DATA_SOURCE = "akshare"  # 默认数据源: "akshare" 或 "tushare"


def get_tushare_pro():
    """获取 Tushare Pro API 实例"""
    import tushare as ts
    ts.set_token(TUSHARE_TOKEN)
    return ts.pro_api()
