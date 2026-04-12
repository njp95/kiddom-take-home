.PHONY: cluster-up cluster-down ingress-up controller tunnel webhook dev \
        sim-open sim-sync sim-close hosts clean

CLUSTER_NAME ?= ephemeral-envs
PR           ?= 1

# Load .env if it exists (exposes GITHUB_TOKEN, WEBHOOK_SECRET, etc.)
-include .env
export

# ── First-time setup ───────────────────────────────────────────────────────────

setup: cluster-up ingress-up
	@echo ""
	@echo "✅  Cluster ready. Next steps:"
	@echo "   1. Fill in .env (copy from .env.example)"
	@echo "   2. Run: make dev"

# ── Cluster lifecycle ──────────────────────────────────────────────────────────

cluster-up:
	kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml
	@echo "✅  kind cluster '$(CLUSTER_NAME)' is up"

cluster-down:
	kind delete cluster --name $(CLUSTER_NAME)

ingress-up:
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx \
	  --for=condition=ready pod \
	  --selector=app.kubernetes.io/component=controller \
	  --timeout=120s
	@echo "✅  nginx ingress controller ready"

# ── Controller ─────────────────────────────────────────────────────────────────

controller:
	cd controller && uvicorn main:app --reload --port 8080

# ── GitHub integration ────────────────────────────────────────────────────────

tunnel:
	./scripts/start-tunnel.sh

webhook:
	./scripts/register-webhook.sh

dev:
	@echo "Start these in separate terminals:"
	@echo ""
	@echo "  Terminal 1 — controller:"
	@echo "    make controller"
	@echo ""
	@echo "  Terminal 2 — tunnel:"
	@echo "    make tunnel"
	@echo ""
	@echo "  Terminal 3 — register webhook (after tunnel is up):"
	@echo "    make webhook"
	@echo ""
	@echo "Then open a PR in https://github.com/$$GITHUB_REPO"

# ── Simulate GitHub webhook events (local dev, no tunnel needed) ─────────────

sim-open:
	./scripts/simulate-pr.sh open $(PR)

sim-sync:
	./scripts/simulate-pr.sh synchronize $(PR)

sim-close:
	./scripts/simulate-pr.sh closed $(PR)

# ── Helpers ───────────────────────────────────────────────────────────────────

hosts:
	./scripts/seed-hosts.sh $(PR)

clean:
	kubectl get namespaces -o name | grep "namespace/pr-" | xargs -r kubectl delete
	@echo "✅  All PR namespaces deleted"
