"""
renderer.py — renders Jinja2 manifest templates into YAML strings.

Templates and values are fetched from the PR branch at provision time via the
GitHub API, so a PR that changes manifests/values.yaml or any template file will
see those changes reflected in its own ephemeral environment — no controller
rebuild required.

Each template receives a context dict containing:
  pr_number   : int
  namespace   : str
  domain      : str   (e.g. "localenv.dev")
  image_tag   : str   (7-char git SHA or "latest")
  ttl_minutes : int
  ...plus all top-level keys from manifests/values.yaml (e.g. api, postgres)
"""

import yaml
from jinja2 import DictLoader, Environment, StrictUndefined

import config
import github_client

_TEMPLATES_PATH = "manifests/templates"
_VALUES_PATH = "manifests/values.yaml"

# Manifests are applied in this order so dependencies are satisfied first.
# Any templates present in the repo that aren't listed here are appended last.
_KNOWN_ORDER = [
    "namespace.yaml.j2",
    "postgres.yaml.j2",
    "api.yaml.j2",
    "ingress.yaml.j2",
]


def _ordered(available: list[str]) -> list[str]:
    known = [t for t in _KNOWN_ORDER if t in available]
    extras = [t for t in available if t not in _KNOWN_ORDER]
    return known + extras


def render_all(ctx: dict, ref: str) -> list[str]:
    """
    Fetch templates and values from the repo at `ref`, then render all manifests.

    `ref` is the PR head SHA (or branch name). If config.TEMPLATE_REF is set it
    takes precedence — useful in local dev where the PR SHA may not exist in the
    remote repo yet.
    """
    effective_ref = config.TEMPLATE_REF or ref

    names = github_client.list_dir(_TEMPLATES_PATH, effective_ref)
    templates = {
        name: github_client.fetch_file(f"{_TEMPLATES_PATH}/{name}", effective_ref)
        for name in names
    }
    values = yaml.safe_load(github_client.fetch_file(_VALUES_PATH, effective_ref))

    # values provide per-repo defaults; ctx fields (pr_number, image_tag, …) take precedence
    full_ctx = {**values, **ctx}

    env = Environment(
        loader=DictLoader(templates),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    return [env.get_template(name).render(**full_ctx) for name in _ordered(names)]


def build_ctx(pr_number: int, image_tag: str = "latest") -> dict:
    return {
        "pr_number": pr_number,
        "namespace": f"pr-{pr_number}",
        "domain": config.INGRESS_DOMAIN,
        "image_tag": image_tag,
        "ttl_minutes": config.TTL_MINUTES,
    }
