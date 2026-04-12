#!/usr/bin/env bash
# register-webhook.sh — creates or updates a pull_request webhook on your GitHub repo.
#
# Prerequisites: GITHUB_TOKEN, GITHUB_REPO, WEBHOOK_SECRET set in .env
# The tunnel must be running first so .tunnel-url exists.
#
# Usage:
#   ./scripts/register-webhook.sh
#   GITHUB_REPO=owner/repo ./scripts/register-webhook.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."

# Load .env
if [[ -f "$ROOT_DIR/.env" ]]; then
  source "$ROOT_DIR/.env"
else
  echo "Error: .env not found. Copy .env.example → .env and fill in values."
  exit 1
fi

# Validate required vars
: "${GITHUB_TOKEN:?Set GITHUB_TOKEN in .env}"
: "${GITHUB_REPO:?Set GITHUB_REPO in .env (e.g. owner/repo)}"
: "${WEBHOOK_SECRET:?Set WEBHOOK_SECRET in .env}"

# Read tunnel URL
TUNNEL_URL_FILE="$ROOT_DIR/.tunnel-url"
if [[ ! -f "$TUNNEL_URL_FILE" ]]; then
  echo "Error: .tunnel-url not found. Run 'make tunnel' first."
  exit 1
fi

RAW_URL=$(cat "$TUNNEL_URL_FILE" | tr -d '[:space:]')

# smee saves just the channel URL; append /webhook for the actual endpoint
if [[ "$RAW_URL" == *"smee.io"* ]] && [[ "$RAW_URL" != *"/webhook"* ]]; then
  WEBHOOK_URL="${RAW_URL}"   # smee client handles path routing internally
else
  WEBHOOK_URL="$RAW_URL"
fi

API_BASE="https://api.github.com/repos/${GITHUB_REPO}/hooks"

echo "Repo:        $GITHUB_REPO"
echo "Webhook URL: $WEBHOOK_URL"
echo ""

# Check if a webhook pointing at this URL already exists
EXISTING_ID=$(curl -sf \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "$API_BASE" \
  | python3 -c "
import sys, json
hooks = json.load(sys.stdin)
match = next((h['id'] for h in hooks if h.get('config', {}).get('url','') == '$WEBHOOK_URL'), None)
print(match or '')
" 2>/dev/null || echo "")

PAYLOAD=$(cat <<EOF
{
  "name": "web",
  "active": true,
  "events": ["pull_request"],
  "config": {
    "url": "${WEBHOOK_URL}",
    "content_type": "json",
    "secret": "${WEBHOOK_SECRET}",
    "insecure_ssl": "0"
  }
}
EOF
)

if [[ -n "$EXISTING_ID" ]]; then
  echo "Updating existing webhook (id=$EXISTING_ID)..."
  RESPONSE=$(curl -sf -X PATCH \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    "$API_BASE/$EXISTING_ID" \
    -d "$PAYLOAD")
  echo "✅  Webhook updated."
else
  echo "Creating new webhook..."
  RESPONSE=$(curl -sf -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    "$API_BASE" \
    -d "$PAYLOAD")
  echo "✅  Webhook created."
fi

HOOK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "   Hook ID: $HOOK_ID"
echo ""
echo "Open a PR in https://github.com/$GITHUB_REPO to trigger your first environment."
