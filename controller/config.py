import os

# ── Routing ────────────────────────────────────────────────────────────────────
INGRESS_DOMAIN = os.getenv("INGRESS_DOMAIN", "localenv.dev")

# ── TTL reaper ─────────────────────────────────────────────────────────────────
# Environments older than this are reaped automatically
TTL_MINUTES = int(os.getenv("TTL_MINUTES", "60"))

# How often the reaper wakes up (minutes)
REAPER_INTERVAL_MINUTES = int(os.getenv("REAPER_INTERVAL", "5"))

# ── Security ───────────────────────────────────────────────────────────────────
# Set to a non-empty string to validate GitHub's X-Hub-Signature-256 header
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# ── Kubernetes ─────────────────────────────────────────────────────────────────
# Path to kubeconfig; None means use in-cluster ServiceAccount
KUBECONFIG_PATH = os.getenv("KUBECONFIG", None)

# ── Manifests ──────────────────────────────────────────────────────────────────
import pathlib
TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "manifests" / "templates"
