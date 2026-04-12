"""
k8s_client.py — thin subprocess wrapper around kubectl.

Production note: swap this out for the official `kubernetes` Python client
(https://github.com/kubernetes-client/python) or use Helm SDK for richer
error handling, watch streams, and server-side apply.
"""

import subprocess
import logging
import json
import tempfile
import os
from typing import Optional

log = logging.getLogger(__name__)


def _run(args: list[str], input: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
    log.debug("kubectl %s", " ".join(args))
    return subprocess.run(
        ["kubectl", *args],
        input=input,
        capture_output=True,
        text=True,
        check=check,
    )


# ── Namespace ──────────────────────────────────────────────────────────────────

def namespace_exists(name: str) -> bool:
    result = _run(["get", "namespace", name], check=False)
    return result.returncode == 0


def create_namespace(name: str, labels: dict = None, annotations: dict = None) -> None:
    """Idempotently create a namespace with optional labels/annotations."""
    if namespace_exists(name):
        log.info("Namespace %s already exists — skipping create", name)
        return

    manifest = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": name,
            "labels": labels or {},
            "annotations": annotations or {},
        },
    }
    apply_manifest(json.dumps(manifest))
    log.info("Created namespace %s", name)


def delete_namespace(name: str) -> None:
    """Delete a namespace and all resources inside it."""
    if not namespace_exists(name):
        log.info("Namespace %s not found — nothing to delete", name)
        return
    _run(["delete", "namespace", name, "--wait=false"])
    log.info("Deleted namespace %s", name)


def list_pr_namespaces() -> list[dict]:
    """Return all namespaces tagged with ephemeral-env=true as dicts."""
    result = _run([
        "get", "namespaces",
        "-l", "ephemeral-env=true",
        "-o", "json",
    ])
    data = json.loads(result.stdout)
    return data.get("items", [])


# ── Manifests ─────────────────────────────────────────────────────────────────

def apply_manifest(yaml_or_json: str, namespace: Optional[str] = None) -> None:
    """Apply a manifest string (YAML or JSON) via kubectl apply."""
    args = ["apply", "-f", "-"]
    if namespace:
        args += ["-n", namespace]
    result = _run(args, input=yaml_or_json)
    log.debug(result.stdout)


def apply_file(path: str, namespace: Optional[str] = None) -> None:
    args = ["apply", "-f", path]
    if namespace:
        args += ["-n", namespace]
    _run(args)
