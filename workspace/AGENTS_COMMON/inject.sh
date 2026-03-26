#!/usr/bin/env bash
# Injects AGENTS_COMMON.md into every bot's AGENTS.md (top of file).
# Idempotent — re-run after editing AGENTS_COMMON.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMMON_FILE="$SCRIPT_DIR/AGENTS_COMMON.md"
START="<!-- AGENTS_COMMON:START -->"
END="<!-- AGENTS_COMMON:END -->"

if [[ ! -f "$COMMON_FILE" ]]; then
  echo "ERROR: $COMMON_FILE not found" >&2; exit 1
fi

# Extract content: skip HTML comment line and the "# AGENTS_COMMON" header line
CONTENT=$(sed '1{/^<!--.*-->/d}; /^# AGENTS_COMMON/d' "$COMMON_FILE")

n=0
for f in "$OPENCLAW_DIR"/workspace-*/AGENTS.md; do
  [[ -f "$f" ]] || continue
  bot=$(basename "$(dirname "$f")")

  # 1. Remove old block if present
  if grep -q "$START" "$f" 2>/dev/null; then
    sed -i "/$START/,/$END/d" "$f"
  fi

  # 2. Remove legacy "Read SOUL_COMMON" / "Read AGENTS_COMMON" instructions
  sed -i '/Read \.\.\/workspace\/SOUL_COMMON/d; /Read \.\.\/workspace\/AGENTS_COMMON/d' "$f"

  # 3. Prepend AGENTS_COMMON content at top of file
  {
    echo "$START"
    echo "$CONTENT"
    echo "$END"
    echo ""
    cat "$f"
  } > "$f.tmp"
  mv "$f.tmp" "$f"

  echo "  ✓ $bot"
  n=$((n + 1))
done

echo ""
echo "Injected into $n files from $COMMON_FILE"
