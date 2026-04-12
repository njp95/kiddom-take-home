#!/usr/bin/env bash
# start-tunnel.sh — expose localhost:8080 to the internet so GitHub can reach it.
#
# Supports two tunnel modes (set TUNNEL_MODE in .env):
#   smee   — uses smee.io via npx (no install or account required)
#   ngrok  — uses ngrok (free tier works; set NGROK_AUTHTOKEN for stable URLs)

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."

# Load .env if present
[[ -f "$ROOT_DIR/.env" ]] && source "$ROOT_DIR/.env"

MODE="${TUNNEL_MODE:-smee}"
PORT="${CONTROLLER_PORT:-8080}"
URL_FILE="$ROOT_DIR/.tunnel-url"

case "$MODE" in

  # ── smee ────────────────────────────────────────────────────────────────────
  smee)
    if ! command -v npx &>/dev/null; then
      echo "Error: npx not found. Install Node.js from https://nodejs.org"
      exit 1
    fi

    # Reuse an existing channel URL so webhook registration stays valid
    # across restarts. Delete .tunnel-url to force a new channel.
    if [[ -f "$URL_FILE" ]]; then
      SMEE_URL=$(cat "$URL_FILE" | tr -d '[:space:]')
      echo "Reusing smee channel: $SMEE_URL"
    else
      echo "Creating a new smee.io channel..."
      # Follow the redirect from smee.io/new and capture the final URL
      SMEE_URL=$(curl -Ls -o /dev/null -w '%{url_effective}' https://smee.io/new)

      if [[ -z "$SMEE_URL" || "$SMEE_URL" == "https://smee.io/new" ]]; then
        echo ""
        echo "Could not auto-create a smee channel (smee.io may be unreachable)."
        echo "Create one manually:"
        echo "  1. Visit https://smee.io/new in your browser"
        echo "  2. Copy the channel URL"
        echo "  3. Run: echo 'https://smee.io/YOUR_CHANNEL' > .tunnel-url"
        echo "  4. Re-run: make tunnel"
        exit 1
      fi

      echo "$SMEE_URL" > "$URL_FILE"
      echo "Created new smee channel: $SMEE_URL"
    fi

    echo ""
    echo "Public webhook URL: $SMEE_URL"
    echo "Forwarding to:      http://localhost:${PORT}/webhook"
    echo ""
    echo "Run 'make webhook' in another terminal to register this URL with GitHub."
    echo "(Press Ctrl-C to stop)"
    echo ""

    exec npx --yes smee-client@1 --url "$SMEE_URL" --path /webhook --port "$PORT"
    ;;

  # ── ngrok ───────────────────────────────────────────────────────────────────
  ngrok)
    if ! command -v ngrok &>/dev/null; then
      echo "ngrok not found. Install from https://ngrok.com/download or use TUNNEL_MODE=smee"
      exit 1
    fi

    if [[ -n "${NGROK_AUTHTOKEN:-}" ]]; then
      ngrok config add-authtoken "$NGROK_AUTHTOKEN" --quiet
    fi

    # Start ngrok in background, wait for its local API to be ready
    ngrok http "$PORT" --log=stdout --log-level=warn &
    NGROK_PID=$!
    sleep 3

    PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels \
      | python3 -c "
import sys, json
data = json.load(sys.stdin)
tunnels = data.get('tunnels', [])
url = next((t['public_url'] for t in tunnels if t['proto'] == 'https'), None)
print(url or '')
")

    if [[ -z "$PUBLIC_URL" ]]; then
      echo "Failed to get ngrok URL — check that ngrok started correctly."
      kill "$NGROK_PID" 2>/dev/null
      exit 1
    fi

    # Store just the base URL; register-webhook.sh appends /webhook
    echo "$PUBLIC_URL" > "$URL_FILE"
    echo ""
    echo "Public webhook URL: ${PUBLIC_URL}/webhook"
    echo "Forwarding to:      http://localhost:${PORT}/webhook"
    echo ""
    echo "Run 'make webhook' in another terminal to register this URL with GitHub."
    echo "(Press Ctrl-C to stop)"
    echo ""

    wait "$NGROK_PID"
    ;;

  *)
    echo "Unknown TUNNEL_MODE='$MODE'. Use 'smee' or 'ngrok'."
    exit 1
    ;;
esac
