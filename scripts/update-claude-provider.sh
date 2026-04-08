#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CONFIG_FILE="$OPENCLAW_DIR/openclaw.json"

usage() {
  cat <<'EOF'
Usage:
  update-claude-provider.sh --base-url <url> --auth-token <token>
  update-claude-provider.sh --base-url <url> --api-key <key>
  update-claude-provider.sh <url> <token_or_key>

Updates the live Claude provider config in ~/.openclaw/openclaw.json.
Auto-detects auth type: cr_* prefix → AUTH_TOKEN, sk-* prefix → API_KEY.
EOF
}

BASE_URL=""
AUTH_TOKEN=""
API_KEY=""

if [[ $# -eq 2 && "$1" != --* ]]; then
  BASE_URL="$1"
  if [[ "$2" == cr_* ]]; then
    AUTH_TOKEN="$2"
  else
    API_KEY="$2"
  fi
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --base-url)
        [[ $# -ge 2 ]] || { echo "Missing value for --base-url" >&2; usage; exit 1; }
        BASE_URL="$2"
        shift 2
        ;;
      --auth-token)
        [[ $# -ge 2 ]] || { echo "Missing value for --auth-token" >&2; usage; exit 1; }
        AUTH_TOKEN="$2"
        shift 2
        ;;
      --api-key)
        [[ $# -ge 2 ]] || { echo "Missing value for --api-key" >&2; usage; exit 1; }
        API_KEY="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
fi

if [[ -z "$BASE_URL" ]]; then
  echo "Base URL is required." >&2
  usage
  exit 1
fi

if [[ -z "$AUTH_TOKEN" && -z "$API_KEY" ]]; then
  echo "Either --auth-token or --api-key is required." >&2
  usage
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config not found: $CONFIG_FILE" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed." >&2
  exit 1
fi

tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"' EXIT

if [[ -n "$AUTH_TOKEN" ]]; then
  jq \
    --arg baseUrl "$BASE_URL" \
    --arg authToken "$AUTH_TOKEN" \
    '
    .models.providers.legacylands.baseUrl = $baseUrl
    | .models.providers.legacylands.apiKey = $authToken
    | .agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_AUTH_TOKEN = $authToken
    | .agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_BASE_URL = $baseUrl
    | del(.agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_API_KEY)
    | del(.modelProviders)
    ' "$CONFIG_FILE" > "$tmp_file"
else
  jq \
    --arg baseUrl "$BASE_URL" \
    --arg apiKey "$API_KEY" \
    '
    .models.providers.legacylands.baseUrl = $baseUrl
    | .models.providers.legacylands.apiKey = $apiKey
    | .agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_API_KEY = $apiKey
    | .agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_BASE_URL = $baseUrl
    | del(.agents.defaults.cliBackends["claude-cli-glm"].env.ANTHROPIC_AUTH_TOKEN)
    | del(.modelProviders)
    ' "$CONFIG_FILE" > "$tmp_file"
fi

mv "$tmp_file" "$CONFIG_FILE"
trap - EXIT

echo "Updated $CONFIG_FILE"
echo "- provider legacylands baseUrl → $BASE_URL"
if [[ -n "$AUTH_TOKEN" ]]; then
  echo "- auth mode: AUTH_TOKEN (cr_*)"
  echo "- claude-cli-glm env ANTHROPIC_AUTH_TOKEN set"
  echo "- claude-cli-glm env ANTHROPIC_API_KEY removed"
else
  echo "- auth mode: API_KEY (sk-*)"
  echo "- claude-cli-glm env ANTHROPIC_API_KEY set"
  echo "- claude-cli-glm env ANTHROPIC_AUTH_TOKEN removed"
fi
