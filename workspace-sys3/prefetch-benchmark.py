#!/usr/bin/env python3
"""
最简 Benchmark：串行 vs 并行预拉，调 research-mcp 对比耗时。

模拟一个迷你 skill "市场快照"，需要拉 5 个数据：
  1. market_overview()
  2. get_cn_bond_yield(maturity="10Y")
  3. get_ashares_index_val()
  4. news_search(query="A股 市场 热点", top_k=3)
  5. research_search(query="行业研究 景气度", top_k=3)

方案 A（串行）：一个一个调，模拟 LLM 串行决策
方案 B（DAG 并行）：5 个请求同时发，模拟写死步骤后并行预拉
方案 C（Markov 缓存）：先跑一遍串行，第二遍用缓存命中模拟

用法：python3 prefetch-benchmark.py
"""

import requests
import json
import time
import concurrent.futures

URL = "http://research-mcp.jijinmima.cn/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 迷你 skill 的 5 个调用
CALLS = [
    ("market_overview", {}),
    ("get_cn_bond_yield", {"maturity": "10Y"}),
    ("get_ashares_index_val", {}),
    ("news_search", {"query": "A股 市场 热点", "top_k": 3, "search_day_ago": 3}),
    ("research_search", {"query": "行业研究 景气度", "top_k": 3}),
]


def mcp_init():
    """初始化 MCP session"""
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bench", "version": "1.0"},
        },
    }
    requests.post(URL, json=body, headers=HEADERS, timeout=10)


def mcp_tool_call(tool_name, arguments, req_id=2):
    """调用一个 MCP tool，返回 (耗时秒, 结果摘要)"""
    body = {
        "jsonrpc": "2.0", "id": req_id, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    t0 = time.time()
    resp = requests.post(URL, json=body, headers=HEADERS, timeout=60)
    elapsed = time.time() - t0

    result_text = ""
    for line in resp.text.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                content = data.get("result", {}).get("content", [])
                if content:
                    result_text = content[0].get("text", "")[:100]
            except json.JSONDecodeError:
                pass
            break

    return elapsed, result_text


def run_serial():
    """方案 A：串行调用，模拟 LLM 一个一个决策"""
    print("\n方案 A: 串行（模拟 LLM 逐步调用）")
    print("-" * 50)

    total = 0
    timings = []
    for i, (tool, args) in enumerate(CALLS):
        elapsed, summary = mcp_tool_call(tool, args, req_id=i + 10)
        timings.append((tool, elapsed))
        total += elapsed
        print(f"  {i+1}. {tool:30s} {elapsed:.2f}s")

    print(f"  {'总耗时':30s} {total:.2f}s")
    return total, timings


def run_parallel():
    """方案 B：DAG 并行预拉，所有请求同时发"""
    print("\n方案 B: 并行预拉（DAG 写死，同时发出）")
    print("-" * 50)

    timings = []
    t0 = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for i, (tool, args) in enumerate(CALLS):
            f = executor.submit(mcp_tool_call, tool, args, i + 20)
            futures[f] = tool

        for f in concurrent.futures.as_completed(futures):
            tool = futures[f]
            elapsed, summary = f.result()
            timings.append((tool, elapsed))

    total = time.time() - t0

    for tool, elapsed in timings:
        print(f"  - {tool:30s} {elapsed:.2f}s")
    print(f"  {'总耗时（wall clock）':30s} {total:.2f}s")
    return total, timings


def run_markov_cache():
    """方案 C：Markov 缓存模拟 — 先跑一遍建缓存，第二遍命中"""
    print("\n方案 C: Markov 缓存（第一遍串行，第二遍命中缓存）")
    print("-" * 50)

    # 第一遍：冷启动，串行调用（同方案 A）
    cache = {}
    cold_total = 0
    for i, (tool, args) in enumerate(CALLS):
        cache_key = f"{tool}:{json.dumps(args, sort_keys=True)}"
        elapsed, summary = mcp_tool_call(tool, args, req_id=i + 30)
        cache[cache_key] = summary
        cold_total += elapsed

    print(f"  第一遍（冷启动）: {cold_total:.2f}s")

    # 第二遍：模拟 Markov 预测
    # 假设 29% 完全命中（用 PoC 的结论），71% 还是要真调
    import random
    random.seed(42)
    hit_rate = 0.29

    warm_total = 0
    hits = 0
    for i, (tool, args) in enumerate(CALLS):
        if random.random() < hit_rate:
            # 缓存命中，0ms
            warm_total += 0.001  # 1ms 模拟内存读取
            hits += 1
            print(f"  {i+1}. {tool:30s} 缓存命中 ~0ms")
        else:
            elapsed, _ = mcp_tool_call(tool, args, req_id=i + 40)
            warm_total += elapsed
            print(f"  {i+1}. {tool:30s} {elapsed:.2f}s (未命中)")

    print(f"  第二遍总耗时: {warm_total:.2f}s (命中 {hits}/{len(CALLS)})")
    return cold_total, warm_total


def main():
    print("=" * 60)
    print("Prefetch Benchmark: 串行 vs 并行 vs 缓存")
    print(f"目标：调 research-mcp 的 {len(CALLS)} 个工具")
    print("=" * 60)

    # 初始化
    mcp_init()
    time.sleep(0.5)

    # 跑三种方案
    serial_total, _ = run_serial()

    mcp_init()
    time.sleep(0.5)
    parallel_total, _ = run_parallel()

    mcp_init()
    time.sleep(0.5)
    cold, warm = run_markov_cache()

    # 汇总
    print("\n" + "=" * 60)
    print("汇总对比")
    print("=" * 60)
    print(f"  方案 A（串行）:     {serial_total:.2f}s  — baseline")
    print(f"  方案 B（DAG并行）:  {parallel_total:.2f}s  — 省 {(1 - parallel_total/serial_total)*100:.0f}%")
    print(f"  方案 C（Markov）:   {warm:.2f}s  — 省 {(1 - warm/serial_total)*100:.0f}%（需冷启动 {cold:.2f}s）")
    print()
    print("注意：")
    print("  - 方案 B 的收益是确定的（参数写死，一定能并行）")
    print("  - 方案 C 的 29% 命中率是从历史统计来的，实际因 skill 而异")
    print("  - 真实场景中 LLM 思考时间（~2-5s/step）也是串行开销的一部分")
    print("  - 方案 B 把 LLM 思考时间也省了（数据已经在那了，LLM 不用等）")


if __name__ == "__main__":
    main()
