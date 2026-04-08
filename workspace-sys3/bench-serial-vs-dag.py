#!/usr/bin/env python3
"""
迷你 skill "市场快照" — 串行 vs DAG 并行对比

skill 做的事：拉 5 个 research-mcp 数据 → 汇总成一段文字
串行：一个调完再调下一个（模拟 LLM 逐步执行 SKILL.md）
DAG：5 个同时发出（模拟系统层预拉，LLM 拿到时数据已备好）

跑 3 轮取平均。
"""

import requests, json, time, concurrent.futures

MCP = "http://research-mcp.jijinmima.cn/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

# 迷你 skill 的数据需求
STEPS = [
    ("market_overview", {}),
    ("get_cn_bond_yield", {"maturity": "10Y"}),
    ("get_ashares_index_val", {}),
    ("news_search", {"query": "A股热点", "top_k": 3, "search_day_ago": 3}),
    ("research_search", {"query": "行业景气", "top_k": 3}),
]

def call(tool, args, rid=1):
    t0 = time.time()
    r = requests.post(MCP, json={
        "jsonrpc": "2.0", "id": rid, "method": "tools/call",
        "params": {"name": tool, "arguments": args}
    }, headers=H, timeout=30)
    dt = time.time() - t0
    return tool, dt

def init():
    requests.post(MCP, json={
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "bench", "version": "1"}}
    }, headers=H, timeout=10)

def serial():
    """串行：依次调用"""
    times = []
    for i, (t, a) in enumerate(STEPS):
        _, dt = call(t, a, i)
        times.append((t, dt))
    return sum(d for _, d in times), times

def dag():
    """DAG 并行：全部同时发"""
    t0 = time.time()
    times = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(STEPS)) as ex:
        futs = {ex.submit(call, t, a, i): t for i, (t, a) in enumerate(STEPS)}
        for f in concurrent.futures.as_completed(futs):
            tool, dt = f.result()
            times.append((tool, dt))
    return time.time() - t0, times

def main():
    ROUNDS = 3
    init()
    time.sleep(0.3)

    serial_results = []
    dag_results = []

    for r in range(ROUNDS):
        s_total, s_times = serial()
        serial_results.append(s_total)
        d_total, d_times = dag()
        dag_results.append(d_total)

        if r == 0:  # 只打印第一轮明细
            print(f"{'tool':30s} {'串行':>6s}  {'DAG单个':>7s}")
            print("-" * 48)
            s_dict = {t: d for t, d in s_times}
            d_dict = {t: d for t, d in d_times}
            for t, _ in STEPS:
                print(f"{t:30s} {s_dict.get(t,0):.2f}s  {d_dict.get(t,0):.2f}s")
            print("-" * 48)

    s_avg = sum(serial_results) / ROUNDS
    d_avg = sum(dag_results) / ROUNDS

    print(f"\n{'':30s} {'串行':>6s}  {'DAG':>7s}")
    print("-" * 48)
    for i in range(ROUNDS):
        print(f"{'Round '+str(i+1):30s} {serial_results[i]:.2f}s  {dag_results[i]:.2f}s")
    print("-" * 48)
    print(f"{'平均':30s} {s_avg:.2f}s  {d_avg:.2f}s")
    print(f"{'DAG 省时':30s}         {(1-d_avg/s_avg)*100:.0f}%")

if __name__ == "__main__":
    main()
