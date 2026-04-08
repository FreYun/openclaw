#!/bin/bash
# sync-skills-to-sandbox.sh
# Sync skills from production to sandbox for OpenSpace evolution.
# Moves any .backup-* dirs to recycle bin.

set -euo pipefail

SRC="/home/rooot/.openclaw/workspace/skills"
DST="/home/rooot/.openclaw/skills-sandbox"
RECYCLE="$DST/.recycle"

# Exclude non-skill files only
EXCLUDE=(
  META-SKILL-README.md
  SKILL-GUIDE.md
)

is_excluded() {
  local name="$1"
  for ex in "${EXCLUDE[@]}"; do
    [[ "$name" == "$ex" ]] && return 0
  done
  return 1
}

mkdir -p "$DST" "$RECYCLE"

synced=0
skipped_exclude=0
skipped_evolved=0
recycled=0

# Move .backup-* dirs from both workspace and sandbox to recycle bin
for dir in "$SRC" "$DST"; do
  for bak in "$dir"/*.backup-*/; do
    [[ -d "$bak" ]] || continue
    name=$(basename "$bak")
    # Remove skill.json from backup before recycling
    rm -f "$bak/skill.json"
    # Prefix with source to avoid collisions
    prefix="ws"
    [[ "$dir" == "$DST" ]] && prefix="sb"
    mv "$bak" "$RECYCLE/${prefix}-${name}" 2>/dev/null || true
    recycled=$((recycled + 1))
  done
done

for skill_dir in "$SRC"/*/; do
  name=$(basename "$skill_dir")

  # Skip excluded skills
  if is_excluded "$name"; then
    skipped_exclude=$((skipped_exclude + 1))
    continue
  fi

  dst_skill="$DST/$name"

  # Skip if sandbox version has been evolved (has .upload_meta.json)
  if [[ -f "$dst_skill/.upload_meta.json" ]]; then
    skipped_evolved=$((skipped_evolved + 1))
    echo "SKIP (evolved): $name"
    continue
  fi

  # Sync: create dir, copy all files except .skill_id (preserve existing)
  mkdir -p "$dst_skill"

  # Copy all files from source
  for f in "$skill_dir"*; do
    fname=$(basename "$f")
    # Preserve sandbox .skill_id if it exists
    if [[ "$fname" == ".skill_id" && -f "$dst_skill/.skill_id" ]]; then
      continue
    fi
    cp "$f" "$dst_skill/" 2>/dev/null || true
  done

  synced=$((synced + 1))
done

echo ""
echo "Sync complete: $synced synced, $skipped_exclude excluded, $skipped_evolved skipped (evolved), $recycled recycled"
