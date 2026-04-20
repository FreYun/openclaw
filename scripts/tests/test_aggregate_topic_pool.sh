#!/usr/bin/env bash
# test_aggregate_topic_pool.sh — 聚合脚本单测

set -u
pass=0
fail=0

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/scripts/aggregate-topic-pool.sh"
FIXTURE="$ROOT/scripts/tests/fixtures/workspace-fake"

assert() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$actual" == *"$expected"* ]]; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ✗ $name"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    fail=$((fail + 1))
  fi
}

assert_not_contains() {
  local name="$1" forbidden="$2" actual="$3"
  if [[ "$actual" != *"$forbidden"* ]]; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ✗ $name"
    echo "    forbidden: $forbidden"
    echo "    actual:    $actual"
    fail=$((fail + 1))
  fi
}

# Test 1: script exists and is executable
echo "Test 1: script exists"
if [[ -x "$SCRIPT" ]]; then
  echo "  ✓ script exists and executable"
  pass=$((pass + 1))
else
  echo "  ✗ script missing or not executable: $SCRIPT"
  fail=$((fail + 1))
  exit 1
fi

# Test 2: default run
echo "Test 2: default run against fixture"
out=$(BASE="$FIXTURE" "$SCRIPT" 2>&1)
ec=$?
assert "exit code 0" "" "$([[ $ec -eq 0 ]] && echo ok)"
assert "valid JSON (has scanned_at)" "scanned_at" "$out"
assert "includes bot_a" "bot_a" "$out"
assert "includes 🔥🔥 item" "黄金 4 月回调" "$out"
assert "includes 🔥 item" "特朗普关税政策影响" "$out"
assert_not_contains "excludes 🌲 at default level" "指数基金长期定投" "$out"
assert_not_contains "excludes old item (>7d)" "旧热点" "$out"

# Test 3: --min-level 火树 includes 🌲
echo "Test 3: --min-level 火树 includes 🌲"
out=$(BASE="$FIXTURE" "$SCRIPT" --min-level 火树 2>&1)
assert "includes 🌲 item" "指数基金长期定投" "$out"

# Test 4: --max-age-days 9999 includes old
echo "Test 4: --max-age-days 9999 includes old item"
out=$(BASE="$FIXTURE" "$SCRIPT" --max-age-days 9999 2>&1)
assert "includes 旧热点" "旧热点" "$out"

# Test 5: bot11 exemption
echo "Test 5: bot11 exemption list in script"
if grep -q "bot11" "$SCRIPT"; then
  echo "  ✓ bot11 exemption hardcoded"
  pass=$((pass + 1))
else
  echo "  ✗ bot11 not in exclusion list"
  fail=$((fail + 1))
fi

# Test 6: FAIL-LOUD
echo "Test 6: FAIL-LOUD on missing BASE"
out=$(BASE="/nonexistent/xxxxx" "$SCRIPT" 2>&1)
ec=$?
if [[ $ec -ne 0 ]]; then
  echo "  ✓ non-zero exit code on missing BASE"
  pass=$((pass + 1))
else
  echo "  ✗ should exit non-zero when BASE missing"
  fail=$((fail + 1))
fi

echo ""
echo "─────────────────────────────"
echo "Passed: $pass   Failed: $fail"
[[ $fail -eq 0 ]] && exit 0 || exit 1
