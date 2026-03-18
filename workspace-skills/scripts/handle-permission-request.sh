#!/bin/bash
# 权限申请处理脚本
# 用法: ./handle-permission-request.sh <bot_id> <tool_name1,tool_name2,...>
# 示例: ./handle-permission-request.sh bot3 stock_research,bond_monitor

set -e

PERM_FILE="/home/rooot/.openclaw/research-gateway/permissions.yaml"
GATEWAY_SCRIPT="/home/rooot/.openclaw/research-gateway/run.sh"

BOT_ID="$1"
TOOLS="$2"

if [ -z "$BOT_ID" ] || [ -z "$TOOLS" ]; then
    echo "用法: $0 <bot_id> <tool1,tool2,...>"
    echo "可用工具: market_snapshot, fund_analysis, fund_screen, stock_research, bond_monitor, macro_overview, commodity_quote, search_news, search_report, index_valuation"
    exit 1
fi

# 读取当前角色
CURRENT_ROLE=$(grep "^  ${BOT_ID}:" "$PERM_FILE" | awk '{print $2}')
if [ -z "$CURRENT_ROLE" ]; then
    echo "错误: 未找到 $BOT_ID 的角色配置"
    exit 1
fi

echo "当前 $BOT_ID 角色: $CURRENT_ROLE"
echo "当前角色工具:"
# 提取当前角色的工具列表
awk "/^  ${CURRENT_ROLE}:/{flag=1; next} flag && /^  [a-z]/{flag=0} flag && /- /{print}" "$PERM_FILE"

echo ""
echo "申请添加的工具: $TOOLS"
echo ""
echo "注意: 此脚本仅做信息展示。实际权限变更需要："
echo "  1. 编辑 $PERM_FILE"
echo "  2. 方案A: 将 bot 迁移到更高权限角色"
echo "  3. 方案B: 为该 bot 创建自定义角色"
echo "  4. 重启网关: bash $GATEWAY_SCRIPT restart"
