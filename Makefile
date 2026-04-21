.PHONY: cluster-up cluster-down ingress-up controller clean simulate-open simulate-sync simulate-close sync-local-values

CLUSTER_NAME ?= ephemeral-envs
PR           ?= 1

# Load .env if it exists (exposes GITHUB_TOKEN, WEBHOOK_SECRET, etc.)
-include .env
export

# ... existing variables ...

IMAGE_NAME = controller:latest

build:
	docker build -t $(IMAGE_NAME) -f Dockerfile .

load:
	kind load docker-image $(IMAGE_NAME) --name $(CLUSTER_NAME)

deploy-controller: build load
	envsubst < manifests/controller.yaml | kubectl apply -f -
	@echo "✅ Controller deployed to cluster"

# Update your setup to include the deployment
setup: cluster-up deploy-controller ingress-up

# ── First-time setup ───────────────────────────────────────────────────────────

# setup: cluster-up ingress-up
# 	@echo ""
# 	@echo "✅  Cluster ready. Next steps:"
# 	@echo "   1. Fill in .env (copy from .env.example)"
# 	@echo "   2. Run: make dev"

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
	cd controller && LOCAL_MANIFESTS_PATH=$(CURDIR)/manifests uvicorn main:app --reload --port 8080

clean:
	kubectl get namespaces -o name | grep "namespace/pr-" | xargs -r kubectl delete
	@echo "✅  All PR namespaces deleted"

# ── Simulate PR webhooks (local dev) ──────────────────────────────────────────

simulate-open: sync-local-values
	@./scripts/simulate-pr.sh open $(PR)

simulate-sync: sync-local-values
	@./scripts/simulate-pr.sh sync $(PR)

simulate-close:
	@./scripts/simulate-pr.sh close $(PR)

sync-local-values:
	@kubectl create configmap local-values-override \
	  --from-file=values.yaml=manifests/values.yaml \
	  --dry-run=client -o yaml | kubectl apply -f -
