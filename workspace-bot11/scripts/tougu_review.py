#!/usr/bin/env python3
"""
投顾组合巡检脚本 - 执行 /tougu-portfolio-review 流程
"""
import json
import subprocess
from datetime import datetime, timedelta

def call_mcp_tool(tool_name, params):
    """调用 MCP 工具"""
    cmd = f"npx mcporter call 'tougu-portfolio-mcp.{tool_name}' '{json.dumps(params)}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": result.stderr or result.stdout}

def get_product_pool():
    """获取产品池"""
    return call_mcp_tool("get_product_pool", {})

def get_bot_holdings(bot_id):
    """获取当前持仓"""
    return call_mcp_tool("get_bot_holdings", {"bot_id": bot_id})

def check_cooldown(bot_id):
    """检查冷静期"""
    return call_mcp_tool("check_cooldown", {"bot_id": bot_id})

def get_product_detail(product_id):
    """获取产品详情"""
    return call_mcp_tool("get_product_detail", {"product_id": product_id})

def main():
    bot_id = "bot11"
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"=== 投顾组合巡检 {today} ===")
    print(f"Bot ID: {bot_id}")
    
    # Step 1: 获取产品池
    print("\n[Step 1] 获取产品池...")
    pool = get_product_pool()
    if pool.get("success"):
        print(f"产品池: {pool.get('count', 0)} 只产品")
    else:
        print(f"获取产品池失败: {pool}")
        return
    
    # Step 2: 获取当前持仓
    print("\n[Step 2] 获取当前持仓...")
    holdings = get_bot_holdings(bot_id)
    print(json.dumps(holdings, indent=2, ensure_ascii=False))
    
    # Step 3: 检查冷静期
    print("\n[Step 3] 检查冷静期...")
    cooldown = check_cooldown(bot_id)
    print(json.dumps(cooldown, indent=2, ensure_ascii=False))
    
    print("\n=== 巡检完成 ===")

if __name__ == "__main__":
    main()
