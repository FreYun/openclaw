#!/usr/bin/env python3
"""
模拟真实 skill 执行：串行 vs DAG

skill = "市场快照"，3 个 step：
  Step 1: 拉宏观数据 → LLM 分析宏观环境
  Step 2: 拉行业数据 → LLM 分析行业景气
  Step 3: LLM 汇总成报告

串行流程（现在的方式）：
  LLM读SKILL.md → LLM决定调market_overview → 等返回 → LLM决定调bond_yield → 等返回
  → LLM分析宏观 → LLM决定调news_search → 等返回 → LLM决定调research_search → 等返回
  → LLM分析行业 → LLM写报告

DAG流程（预拉）：
  系统读skill.json拿到DAG → 并行预拉Step1+Step2所有数据
  → LLM拿到全部数据 → 分析宏观 → 分析行业 → 写报告
  （LLM不用一个一个决定调什么工具，数据已经备好）
"""

import requests, json, time, concurrent.futures

MCP = "http://research-mcp.jijinmima.cn/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

# Skill DAG 定义
STEP1_CALLS = [
    ("market_overview", {}),
    ("get_cn_bond_yield", {"maturity": "10Y"}),
    ("get_ashares_index_val", {}),
]
STEP2_CALLS = [
    ("news_search", {"query": "A股热点", "top_k": 3, "search_day_ago": 3}),
    ("research_search", {"query": "行业景气", "top_k": 3}),
]

# LLM 思考时间模拟（基于真实观测）
LLM_READ_SKILL = 2.0    # 读 SKILL.md 并理解
LLM_DECIDE_TOOL = 1.5   # 每次决定调哪个工具
LLM_ANALYZE = 3.0        # 分析一个 step 的数据
LLM_WRITE_REPORT = 4.0   # 写最终报告


def mcp_call(tool, args, rid=1):
    t0 = time.time()
    requests.post(MCP, json={
        "jsonrpc": "2.0", "id": rid, "method": "tools/call",
        "params": {"name": tool, "arguments": args}
    }, headers=H, timeout=30)
    return time.time() - t0


def mcp_init():
    requests.post(MCP, json={
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "bench", "version": "1"}}
    }, headers=H, timeout=10)


def parallel_calls(calls):
    """并行发一组 MCP 调用，返回 wall clock 时间"""
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as ex:
        futs = [ex.submit(mcp_call, t, a, i) for i, (t, a) in enumerate(calls)]
        concurrent.futures.wait(futs)
    return time.time() - t0


def llm_think(seconds, label):
    """模拟 LLM 思考"""
    time.sleep(seconds)
    return seconds


def run_serial():
    """串行：LLM 一步步决策"""
    log = []
    total = 0

    # LLM 读 SKILL.md
    dt = llm_think(LLM_READ_SKILL, "读SKILL.md")
    log.append(("🧠 LLM 读 SKILL.md", dt))
    total += dt

    # Step 1: 宏观数据（LLM 逐个决定调用）
    for tool, args in STEP1_CALLS:
        dt = llm_think(LLM_DECIDE_TOOL, f"决定调{tool}")
        log.append((f"🧠 LLM 决定调 {tool}", dt))
        total += dt

        dt = mcp_call(tool, args)
        log.append((f"🌐 {tool} 返回", dt))
        total += dt

    # LLM 分析宏观
    dt = llm_think(LLM_ANALYZE, "分析宏观")
    log.append(("🧠 LLM 分析宏观环境", dt))
    total += dt

    # Step 2: 行业数据
    for tool, args in STEP2_CALLS:
        dt = llm_think(LLM_DECIDE_TOOL, f"决定调{tool}")
        log.append((f"🧠 LLM 决定调 {tool}", dt))
        total += dt

        dt = mcp_call(tool, args)
        log.append((f"🌐 {tool} 返回", dt))
        total += dt

    # LLM 分析行业
    dt = llm_think(LLM_ANALYZE, "分析行业")
    log.append(("🧠 LLM 分析行业景气", dt))
    total += dt

    # Step 3: 写报告
    dt = llm_think(LLM_WRITE_REPORT, "写报告")
    log.append(("🧠 LLM 写最终报告", dt))
    total += dt

    return total, log


def run_dag():
    """DAG：系统预拉数据，LLM 直接分析"""
    log = []
    total = 0

    # 系统解析 skill.json（几乎不耗时）
    log.append(("⚙️  系统解析 DAG", 0.01))
    total += 0.01

    # 系统并行预拉 Step1 + Step2 所有数据
    all_calls = STEP1_CALLS + STEP2_CALLS
    dt = parallel_calls(all_calls)
    log.append((f"⚙️  并行预拉 {len(all_calls)} 个数据", dt))
    total += dt

    # LLM 拿到全部数据，直接分析（不需要决定调什么工具）
    dt = llm_think(LLM_ANALYZE, "分析宏观")
    log.append(("🧠 LLM 分析宏观环境", dt))
    total += dt

    dt = llm_think(LLM_ANALYZE, "分析行业")
    log.append(("🧠 LLM 分析行业景气", dt))
    total += dt

    dt = llm_think(LLM_WRITE_REPORT, "写报告")
    log.append(("🧠 LLM 写最终报告", dt))
    total += dt

    return total, log


def print_timeline(label, total, log):
    print(f"\n{'=' * 60}")
    print(f"{label}  总耗时: {total:.1f}s")
    print(f"{'=' * 60}")
    cumulative = 0
    llm_total = 0
    net_total = 0
    for desc, dt in log:
        cumulative += dt
        tag = ""
        if "🧠" in desc:
            llm_total += dt
            tag = "LLM"
        elif "🌐" in desc or "预拉" in desc:
            net_total += dt
            tag = "NET"
        print(f"  {cumulative:5.1f}s  [{tag:3s}]  {desc:40s} +{dt:.2f}s")
    print(f"  --- LLM 思考: {llm_total:.1f}s | 网络等待: {net_total:.1f}s ---")


def main():
    mcp_init()
    time.sleep(0.3)

    s_total, s_log = run_serial()
    print_timeline("串行（现在的方式）", s_total, s_log)

    mcp_init()
    time.sleep(0.3)

    d_total, d_log = run_dag()
    print_timeline("DAG（系统预拉）", d_total, d_log)

    # 对比
    print(f"\n{'=' * 60}")
    print(f"对比")
    print(f"{'=' * 60}")
    print(f"  串行: {s_total:.1f}s")
    print(f"  DAG:  {d_total:.1f}s")
    print(f"  省时: {s_total - d_total:.1f}s ({(1 - d_total/s_total)*100:.0f}%)")

    # 拆解省在哪
    s_llm = sum(dt for desc, dt in s_log if "🧠" in desc)
    d_llm = sum(dt for desc, dt in d_log if "🧠" in desc)
    s_net = sum(dt for desc, dt in s_log if "🌐" in desc)
    d_net = sum(dt for desc, dt in d_log if "预拉" in desc)

    print(f"\n  省时来源:")
    print(f"    LLM 决策省掉: {s_llm - d_llm:.1f}s  (不用逐个决定调什么工具)")
    print(f"    网络并行省掉: {s_net - d_net:.1f}s  (串行→并行)")


if __name__ == "__main__":
    main()
