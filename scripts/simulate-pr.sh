#!/usr/bin/env bash
# simulate-pr.sh — fire a fake GitHub pull_request webhook at the controller.
#
# Usage:
#   ./scripts/simulate-pr.sh open        42
#   ./scripts/simulate-pr.sh synchronize 42   [optional-sha]
#   ./scripts/simulate-pr.sh closed      42

set -euo pipefail

ACTION="${1:-open}"
PR_NUMBER="${2:-1}"
SHA="${3:-$(git rev-parse HEAD 2>/dev/null || echo main)}"
CONTROLLER_URL="${CONTROLLER_URL:-}"

# If no CONTROLLER_URL is set, prefer a locally-running controller (make controller),
# and fall back to port-forwarding to the in-cluster controller.
if [ -z "$CONTROLLER_URL" ]; then
  if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "Using local controller at http://127.0.0.1:8080"
    CONTROLLER_URL="http://127.0.0.1:8080"
  else
    echo "No local controller found — port-forwarding to lifecycle-controller..."
    kubectl port-forward deployment/lifecycle-controller 8080:8080 >/dev/null 2>&1 &
    PF_PID=$!
    trap 'kill "$PF_PID" 2>/dev/null; wait "$PF_PID" 2>/dev/null' EXIT

    # Wait up to 5s for the port-forward to be ready
    for i in $(seq 1 10); do
      if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then break; fi
      sleep 0.5
    done

    CONTROLLER_URL="http://127.0.0.1:8080"
  fi
fi

# Map friendly aliases → GitHub action strings
case "$ACTION" in
  open)    ACTION="opened"       ;;
  sync)    ACTION="synchronize"  ;;
  close)   ACTION="closed"       ;;
  *)       : ;;   # pass through raw value (opened, synchronize, closed, reopened)
esac

PAYLOAD=$(cat <<EOF
{
  "action": "${ACTION}",
  "number": ${PR_NUMBER},
  "pull_request": {
    "number": ${PR_NUMBER},
    "title": "feat: simulated PR #${PR_NUMBER}",
    "state": "$([ "$ACTION" = "closed" ] && echo closed || echo open)",
    "head": {
      "sha": "${SHA}",
      "ref": "feat/pr-${PR_NUMBER}"
    },
    "base": {
      "ref": "main"
    }
  }
}
EOF
)

echo "→ Sending action='${ACTION}' for PR #${PR_NUMBER} (sha=${SHA:0:7}) to ${CONTROLLER_URL}/webhook"
echo ""

RESPONSE=$(curl -s --fail-with-body -X POST "${CONTROLLER_URL}/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d "${PAYLOAD}" 2>&1) || {
  echo "Error: could not reach controller at ${CONTROLLER_URL}"
  echo "  Is the lifecycle-controller pod running? Try: kubectl get pods"
  exit 1
}

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "Environment URL: http://pr-${PR_NUMBER}.localenv.dev"
echo "(Add to /etc/hosts: 127.0.0.1  pr-${PR_NUMBER}.localenv.dev)"
