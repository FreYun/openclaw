#!/bin/bash
# sync-skills-to-sandbox.sh
# Sync safe skills from production to sandbox for OpenSpace evolution.
# Skips red-zone skills and already-evolved sandbox copies.

set -euo pipefail

SRC="/home/rooot/.openclaw/workspace/skills"
DST="/home/rooot/.openclaw/skills-sandbox"

# Red zone: never sync these (testing = real side effects)
EXCLUDE=(
  xhs-pub
  gzh-publish
  scheduled-post
  submit-to-publisher
  xhs-nurture
  xhs-op
  report-incident
  contact-book
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

mkdir -p "$DST"

synced=0
skipped_exclude=0
skipped_evolved=0

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
echo "Sync complete: $synced synced, $skipped_exclude excluded (red zone), $skipped_evolved skipped (already evolved)"
