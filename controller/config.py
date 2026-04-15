import os

# ── GitHub ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")    # e.g. "org/repo"

# When set, overrides the git ref used to fetch templates and values from GitHub.
# Useful in local dev where the PR head SHA may not exist in the remote repo yet
# (e.g. when using simulate-pr.sh with a synthetic SHA). Set to "main" in the
# controller deployment manifest for local kind clusters.
TEMPLATE_REF = os.getenv("TEMPLATE_REF", "")

# ── Routing ────────────────────────────────────────────────────────────────────
INGRESS_DOMAIN = os.getenv("INGRESS_DOMAIN", "localenv.dev")

# ── TTL reaper ─────────────────────────────────────────────────────────────────
TTL_MINUTES = int(os.getenv("TTL_MINUTES", "60"))
REAPER_INTERVAL_MINUTES = int(os.getenv("REAPER_INTERVAL", "5"))

# ── Security ───────────────────────────────────────────────────────────────────
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# ── Kubernetes ─────────────────────────────────────────────────────────────────
KUBECONFIG_PATH = os.getenv("KUBECONFIG", None)
