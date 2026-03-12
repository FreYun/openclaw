#!/usr/bin/env bash
# Merge ~/.openclaw/config/mcporter-global.json into each workspace's config/mcporter.json.
# Global mcpServers are merged first; workspace entries override on same key.
set -e

OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
GLOBAL_CONFIG="$OPENCLAW_DIR/config/mcporter-global.json"

if [[ ! -f "$GLOBAL_CONFIG" ]]; then
  echo "Global config not found: $GLOBAL_CONFIG" >&2
  exit 1
fi

for ws_config in "$OPENCLAW_DIR"/workspace*/config/mcporter.json; do
  [[ -f "$ws_config" ]] || continue
  workspace_name=$(basename "$(dirname "$(dirname "$ws_config")")")
  tmp=$(mktemp)
  jq -s '
    (.[0].mcpServers // {}) as $global
  | (.[1].mcpServers // {}) as $local
  | .[1]
  | .mcpServers = ($global + $local)
  ' "$GLOBAL_CONFIG" "$ws_config" > "$tmp"
  mv "$tmp" "$ws_config"
  echo "Merged: $workspace_name"
done

echo "Done."
