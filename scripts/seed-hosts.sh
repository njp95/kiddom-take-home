#!/usr/bin/env bash
# seed-hosts.sh — adds pr-<N>.localenv.dev entries to /etc/hosts.
# Run once after provisioning an environment for the first time.
#
# Usage: ./scripts/seed-hosts.sh 42

set -euo pipefail

PR_NUMBER="${1:-}"
DOMAIN="localenv.dev"
HOSTS_FILE="/etc/hosts"
IP="127.0.0.1"

if [[ -z "$PR_NUMBER" ]]; then
  # Seed all live PR namespaces found in the cluster
  PRS=$(kubectl get namespaces -l ephemeral-env=true -o jsonpath='{.items[*].metadata.labels.pr}')
  if [[ -z "$PRS" ]]; then
    echo "No ephemeral namespaces found in cluster."
    exit 0
  fi
else
  PRS="$PR_NUMBER"
fi

for pr in $PRS; do
  HOST="pr-${pr}.${DOMAIN}"
  if grep -q "$HOST" "$HOSTS_FILE" 2>/dev/null; then
    echo "  ✓ ${HOST} already in ${HOSTS_FILE}"
  else
    echo "${IP}  ${HOST}" | sudo tee -a "$HOSTS_FILE" > /dev/null
    echo "  + Added ${IP}  ${HOST}"
  fi
done

echo ""
echo "Done. Test with:"
for pr in $PRS; do
  echo "  curl http://pr-${pr}.${DOMAIN}"
done
