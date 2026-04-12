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
SHA="${3:-$(head -c 4 /dev/urandom | xxd -p)}"
CONTROLLER_URL="${CONTROLLER_URL:-http://localhost:8080}"

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

curl -s -X POST "${CONTROLLER_URL}/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d "${PAYLOAD}" | python3 -m json.tool

echo ""
echo "Environment URL: http://pr-${PR_NUMBER}.localenv.dev"
echo "(Add to /etc/hosts: 127.0.0.1  pr-${PR_NUMBER}.localenv.dev)"
