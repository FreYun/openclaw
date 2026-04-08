#!/usr/bin/env python3
"""
Prefetch PoC v2：带参数精确匹配的 Markov 缓存命中模拟

两层分析：
  Level 1 — tool name only（上一版）
  Level 2 — tool_name + args_hash（精确缓存 key，能不能省实际 IO）

用法：python3 prefetch-poc.py
"""

import json, glob, os, collections, hashlib

AGENTS_DIR = "/home/rooot/.openclaw/agents"
BOTS = ["bot7", "bot8", "bot11"]
LOCAL_TOOLS = {"read", "write", "edit", "bash", "glob", "grep", "todowrite",
               "askuserquestion", "agent", "exec", "process", "message",
               "send_message", "reply_message", "get_message", "session_status",
               "agents_list", "image"}


def args_hash(args):
    """参数字典 → 短 hash"""
    raw = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def extract_tool_sequences(bot_id):
    """提取两种粒度的序列：(tool_name, tool_name+args_hash)"""
    sessions_dir = os.path.join(AGENTS_DIR, bot_id, "sessions")
    sequences = []  # list of [(name, name+hash, full_args), ...]

    for fp in glob.glob(os.path.join(sessions_dir, "*.jsonl")):
        seq = []
        try:
            with open(fp) as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") != "message":
                        continue
                    content = obj.get("message", {}).get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "toolCall":
                            name = block.get("name", "")
                            if name and name not in LOCAL_TOOLS:
                                args = block.get("arguments", {}) or block.get("input", {}) or {}
                                ahash = args_hash(args)
                                exact_key = f"{name}:{ahash}"
                                seq.append((name, exact_key, args))
        except Exception:
            continue
        if len(seq) >= 2:
            sequences.append(seq)

    return sequences


def build_markov(sequences, key_fn, order=1):
    """构建转移计数，key_fn 从 tuple 中提取用哪个粒度"""
    transitions = collections.defaultdict(collections.Counter)
    for seq in sequences:
        keys = [key_fn(item) for item in seq]
        for i in range(len(keys) - order):
            state = tuple(keys[i:i + order])
            nxt = keys[i + order]
            transitions[state][nxt] += 1
    return transitions


def to_probs(transitions):
    probs = {}
    for state, counter in transitions.items():
        total = sum(counter.values())
        probs[state] = {t: c / total for t, c in counter.most_common()}
    return probs


def simulate(sequences, probs, key_fn, top_k=1, order=1):
    total = hits = waste = 0
    for seq in sequences:
        keys = [key_fn(item) for item in seq]
        for i in range(len(keys) - order):
            state = tuple(keys[i:i + order])
            actual = keys[i + order]
            if state not in probs:
                continue
            predicted = list(probs[state].keys())[:top_k]
            total += 1
            if actual in predicted:
                hits += 1
            waste += len(predicted) - (1 if actual in predicted else 0)
    return total, hits, waste


def analyze_arg_patterns(sequences):
    """分析同一 tool 连续调用时，参数的变化模式"""
    patterns = collections.defaultdict(lambda: {"same": 0, "diff": 0, "examples": []})

    for seq in sequences:
        for i in range(len(seq) - 1):
            curr_name, _, curr_args = seq[i]
            next_name, _, next_args = seq[i + 1]
            if curr_name == next_name:  # 同 tool 连续调用
                if curr_args == next_args:
                    patterns[curr_name]["same"] += 1
                else:
                    patterns[curr_name]["diff"] += 1
                    if len(patterns[curr_name]["examples"]) < 3:
                        # 记录参数差异
                        diff_keys = set()
                        all_keys = set(list(curr_args.keys()) + list(next_args.keys()))
                        for k in all_keys:
                            if curr_args.get(k) != next_args.get(k):
                                diff_keys.add(k)
                        patterns[curr_name]["examples"].append({
                            "changed_keys": list(diff_keys),
                            "curr": {k: curr_args.get(k) for k in diff_keys},
                            "next": {k: next_args.get(k) for k in diff_keys},
                        })

    return patterns


def main():
    print("=" * 70)
    print("Prefetch PoC v2: Tool Name vs Exact Args 命中率对比")
    print("=" * 70)

    # 1. 提取
    all_seqs = []
    for bot in BOTS:
        seqs = extract_tool_sequences(bot)
        n_calls = sum(len(s) for s in seqs)
        print(f"  {bot}: {len(seqs)} sessions, {n_calls} MCP calls")
        all_seqs.extend(seqs)

    total_calls = sum(len(s) for s in all_seqs)
    print(f"\n  Total: {len(all_seqs)} sessions, {total_calls} MCP calls")

    # 2. 两层对比
    name_fn = lambda x: x[0]   # tool name only
    exact_fn = lambda x: x[1]  # tool name + args hash

    print(f"\n{'':=<70}")
    print(f"Level 1: Tool Name Only (能预测调哪个工具)")
    print(f"{'':=<70}")
    print(f"{'order':>5s} {'top_k':>5s} {'total':>6s} {'hits':>6s} {'rate':>7s} {'waste':>6s} {'eff':>6s}")

    for order in [1]:
        trans = build_markov(all_seqs, name_fn, order)
        probs = to_probs(trans)
        for top_k in [1, 2, 3]:
            t, h, w = simulate(all_seqs, probs, name_fn, top_k, order)
            if t:
                print(f"{order:5d} {top_k:5d} {t:6d} {h:6d} {h/t:7.1%} {w:6d} {h/(h+w):6.1%}")

    print(f"\n{'':=<70}")
    print(f"Level 2: Tool + Args Hash (能精确命中缓存，省实际 IO)")
    print(f"{'':=<70}")
    print(f"{'order':>5s} {'top_k':>5s} {'total':>6s} {'hits':>6s} {'rate':>7s} {'waste':>6s} {'eff':>6s}")

    for order in [1]:
        trans = build_markov(all_seqs, exact_fn, order)
        probs = to_probs(trans)
        for top_k in [1, 2, 3]:
            t, h, w = simulate(all_seqs, probs, exact_fn, top_k, order)
            if t:
                print(f"{order:5d} {top_k:5d} {t:6d} {h:6d} {h/t:7.1%} {w:6d} {h/(h+w):6.1%}")

    # 3. 参数变化模式分析
    print(f"\n{'':=<70}")
    print(f"参数变化模式：同 tool 连续调用时参数怎么变？")
    print(f"{'':=<70}")

    patterns = analyze_arg_patterns(all_seqs)
    for tool, data in sorted(patterns.items(), key=lambda x: -(x[1]["same"] + x[1]["diff"])):
        total = data["same"] + data["diff"]
        same_pct = data["same"] / total if total else 0
        print(f"\n  {tool}: {total} 次连续调用, 参数相同 {data['same']}({same_pct:.0%}), 不同 {data['diff']}({1-same_pct:.0%})")
        for ex in data["examples"][:2]:
            changed = ", ".join(ex["changed_keys"])
            print(f"    变化字段: {changed}")
            for k in ex["changed_keys"][:2]:
                c = str(ex["curr"].get(k, ""))[:40]
                n = str(ex["next"].get(k, ""))[:40]
                print(f"      {k}: {c} → {n}")

    # 4. 真实缓存分析：同一 session 内有多少调用是重复的（可直接缓存）
    print(f"\n{'':=<70}")
    print(f"真实缓存价值：同一次 skill 执行内，有多少调用参数完全重复？")
    print(f"（只有同一 session 内的重复调用才能安全缓存，跨 session 数据会变）")
    print(f"{'':=<70}")

    total_calls_all = 0
    cacheable_calls = 0
    session_details = []

    for seq in all_seqs:
        seen = set()  # 本 session 内已见过的 (tool, args_hash)
        session_total = len(seq)
        session_cached = 0
        for name, exact_key, args in seq:
            if exact_key in seen:
                session_cached += 1  # 参数完全一样，可以直接返回缓存
            else:
                seen.add(exact_key)
            total_calls_all += 1
        cacheable_calls += session_cached
        if session_total >= 3:
            session_details.append((session_total, session_cached))

    intra_rate = cacheable_calls / total_calls_all if total_calls_all else 0
    print(f"\n  总 MCP 调用: {total_calls_all}")
    print(f"  同 session 内完全重复: {cacheable_calls} ({intra_rate:.1%})")
    print(f"  不可缓存（首次调用）: {total_calls_all - cacheable_calls} ({1-intra_rate:.1%})")

    # 5. 预拉分析：同一 session 内，能通过 Markov 预拉省掉的调用
    print(f"\n{'':=<70}")
    print(f"预拉价值：不是重复调用，但能提前预拉的有多少？")
    print(f"（当前调 tushare_index_daily(A)，预测下一个也是 tushare_index_daily，")
    print(f"  虽然参数不同(B)不知道是什么，但工具类型对了 → 可以预热连接/并行化）")
    print(f"{'':=<70}")

    # 统计同 session 内：当前 tool → 下一个是同 tool 但不同参数
    prefetchable = 0  # 工具类型对了，但参数不同
    total_transitions = 0
    for seq in all_seqs:
        for i in range(len(seq) - 1):
            curr_name, curr_key, _ = seq[i]
            next_name, next_key, _ = seq[i + 1]
            total_transitions += 1
            if curr_name == next_name and curr_key != next_key:
                prefetchable += 1

    prefetch_rate = prefetchable / total_transitions if total_transitions else 0
    print(f"\n  同 tool 不同参数（可预热连接）: {prefetchable} ({prefetch_rate:.1%})")

    # 6. 综合
    print(f"\n{'':=<70}")
    print(f"综合结论")
    print(f"{'':=<70}")
    print(f"  总 MCP 调用: {total_calls_all}")
    print(f"  ├─ 完全重复（直接返回缓存）: {cacheable_calls} ({intra_rate:.1%})")
    print(f"  ├─ 同 tool 不同参数（可预热）: {prefetchable} ({prefetch_rate:.1%})")
    other = total_calls_all - cacheable_calls - prefetchable
    other_rate = other / total_calls_all if total_calls_all else 0
    print(f"  └─ 完全不可预测: {other} ({other_rate:.1%})")
    print()
    useful = cacheable_calls + prefetchable
    useful_rate = useful / total_calls_all if total_calls_all else 0
    if useful_rate > 0.3:
        print(f"  ✅ {useful_rate:.0%} 的调用可以受益于缓存/预热")
    else:
        print(f"  ⚠️  只有 {useful_rate:.0%} 的调用可受益，收益有限")


if __name__ == "__main__":
    main()
