#!/bin/bash
# 安装定时任务：每个交易日 15:05 自动执行盘后更新
# 用法: bash install_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3 2>/dev/null || which python 2>/dev/null)"

if [ -z "$PYTHON" ]; then
    echo "错误: 未找到 python，请先安装 python3"
    exit 1
fi

# 检查 tushare 是否可用
$PYTHON -c "import tushare" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "错误: tushare 未安装，请运行: pip install tushare"
    exit 1
fi

CRON_CMD="5 15 * * 1-5 cd $SCRIPT_DIR && $PYTHON $SCRIPT_DIR/daily_update.py >> $SCRIPT_DIR/data/cron.log 2>&1"

# 检查是否已存在
(crontab -l 2>/dev/null | grep -q "daily_update.py") && {
    echo "定时任务已存在，先移除旧任务..."
    crontab -l 2>/dev/null | grep -v "daily_update.py" | crontab -
}

# 添加定时任务
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "定时任务已安装:"
echo "  时间: 每周一到周五 15:05"
echo "  脚本: $SCRIPT_DIR/daily_update.py"
echo "  Python: $PYTHON"
echo ""
echo "验证: crontab -l"
