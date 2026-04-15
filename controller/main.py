"""
main.py — Lifecycle controller for ephemeral PR environments.

Endpoints:
  POST /webhook          GitHub pull_request webhook (or simulated payload)
  GET  /envs             List all live environments
  DELETE /envs/{pr}      Manually tear down an environment

Background task:
  TTL reaper — scans namespaces every REAPER_INTERVAL_MINUTES and deletes
  any whose `created-at` annotation exceeds TTL_MINUTES.
"""

import asyncio
import hashlib
import hmac
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse

import config
import k8s_client as k8s
import renderer

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("controller")


# ── Reaper ─────────────────────────────────────────────────────────────────────

async def reaper_loop():
    """Background task: periodically delete environments past their TTL."""
    interval = config.REAPER_INTERVAL_MINUTES * 60
    log.info("Reaper started — interval=%dm  TTL=%dm", config.REAPER_INTERVAL_MINUTES, config.TTL_MINUTES)

    while True:
        await asyncio.sleep(interval)
        try:
            namespaces = k8s.list_pr_namespaces()
            now = time.time()

            for ns in namespaces:
                name = ns["metadata"]["name"]
                annotations = ns["metadata"].get("annotations", {})
                created_at = float(annotations.get("ephemeral-env/created-at", now))
                age_minutes = (now - created_at) / 60

                if age_minutes >= config.TTL_MINUTES:
                    log.info("TTL exceeded for %s (age=%.1fm) — tearing down", name, age_minutes)
                    k8s.delete_namespace(name)
                else:
                    log.debug("%s age=%.1fm (TTL=%dm)", name, age_minutes, config.TTL_MINUTES)

        except Exception as exc:
            log.error("Reaper error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(reaper_loop())
    yield
    task.cancel()


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Ephemeral Env Controller", lifespan=lifespan)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verify_signature(body: bytes, sig_header: str) -> None:
    """Validate GitHub's X-Hub-Signature-256 header if WEBHOOK_SECRET is set."""
    if not config.WEBHOOK_SECRET:
        return
    expected = "sha256=" + hmac.new(
        config.WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header or ""):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _provision(pr_number: int, image_tag: str = "latest", head_sha: str = "main") -> str:
    """Create/update all resources for a PR. Returns the environment URL."""
    ctx = renderer.build_ctx(pr_number, image_tag)
    namespace = ctx["namespace"]

    # Namespace with labels for reaper targeting and annotations for TTL tracking
    k8s.create_namespace(
        namespace,
        labels={"ephemeral-env": "true", "pr": str(pr_number)},
        annotations={
            "ephemeral-env/created-at": str(time.time()),
            "ephemeral-env/pr": str(pr_number),
        },
    )

    # Fetch templates and values from the PR branch, then apply in dependency order
    for manifest_yaml in renderer.render_all(ctx, ref=head_sha):
        k8s.apply_manifest(manifest_yaml, namespace=namespace)

    url = f"http://pr-{pr_number}.{config.INGRESS_DOMAIN}"
    log.info("Provisioned environment for PR #%d → %s", pr_number, url)
    return url


def _teardown(pr_number: int) -> None:
    k8s.delete_namespace(f"pr-{pr_number}")
    log.info("Torn down environment for PR #%d", pr_number)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default="pull_request"),
):
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if x_github_event != "pull_request":
        return JSONResponse({"ignored": True, "event": x_github_event})

    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    # Full SHA is used to fetch templates/values from the correct commit.
    # The 7-char prefix is used as the image tag for the application container.
    head_sha = pr.get("head", {}).get("sha", "main")
    image_tag = head_sha[:7]

    if not pr_number:
        raise HTTPException(status_code=400, detail="Missing pull_request.number")

    log.info("PR #%d — action=%s  sha=%s", pr_number, action, image_tag)

    if action in ("opened", "reopened", "synchronize"):
        url = _provision(pr_number, image_tag, head_sha)
        return {"status": "provisioned", "pr": pr_number, "url": url}

    elif action == "closed":
        _teardown(pr_number)
        return {"status": "torn_down", "pr": pr_number}

    return {"status": "ignored", "action": action}


@app.get("/envs")
def list_envs():
    """List all live ephemeral environments."""
    namespaces = k8s.list_pr_namespaces()
    envs = []
    for ns in namespaces:
        meta = ns["metadata"]
        annotations = meta.get("annotations", {})
        created_ts = float(annotations.get("ephemeral-env/created-at", 0))
        age_minutes = (time.time() - created_ts) / 60 if created_ts else None
        pr_num = annotations.get("ephemeral-env/pr", "?")
        envs.append({
            "namespace": meta["name"],
            "pr": pr_num,
            "url": f"http://pr-{pr_num}.{config.INGRESS_DOMAIN}",
            "age_minutes": round(age_minutes, 1) if age_minutes else None,
            "ttl_minutes": config.TTL_MINUTES,
        })
    return {"environments": envs}


@app.delete("/envs/{pr_number}")
def delete_env(pr_number: int):
    """Manually tear down an environment."""
    _teardown(pr_number)
    return {"status": "torn_down", "pr": pr_number}


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
