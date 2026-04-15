"""
github_client.py — fetches file contents from the configured GitHub repo at a given ref.
"""

import base64
import logging

import requests as http

import config

log = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return h


def fetch_file(path: str, ref: str) -> str:
    """Return the decoded contents of `path` in the repo at the given git ref."""
    url = f"{_GITHUB_API}/repos/{config.GITHUB_REPO}/contents/{path}?ref={ref}"
    resp = http.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return base64.b64decode(resp.json()["content"]).decode()


def list_dir(path: str, ref: str) -> list[str]:
    """Return the file names inside a directory in the repo at the given git ref."""
    url = f"{_GITHUB_API}/repos/{config.GITHUB_REPO}/contents/{path}?ref={ref}"
    resp = http.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return [item["name"] for item in resp.json() if item["type"] == "file"]
