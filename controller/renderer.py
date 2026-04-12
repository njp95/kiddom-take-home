"""
renderer.py — renders Jinja2 manifest templates into YAML strings.

Each template receives a `ctx` dict with at minimum:
  pr_number   : int
  namespace   : str
  domain      : str   (e.g. "localenv.dev")
  image_tag   : str   (git SHA or "latest")
"""

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import config


_env = Environment(
    loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_name: str, ctx: dict) -> str:
    """Render a template file and return the YAML string."""
    tmpl = _env.get_template(template_name)
    return tmpl.render(**ctx)


def render_all(ctx: dict) -> list[str]:
    """Render all manifests for a PR environment in dependency order."""
    # Order matters: namespace first, then stateful services, then app, then ingress
    templates = [
        "namespace.yaml.j2",
        "postgres.yaml.j2",
        "api.yaml.j2",
        "ingress.yaml.j2",
    ]
    return [render(t, ctx) for t in templates]


def build_ctx(pr_number: int, image_tag: str = "latest") -> dict:
    return {
        "pr_number": pr_number,
        "namespace": f"pr-{pr_number}",
        "domain": config.INGRESS_DOMAIN,
        "image_tag": image_tag,
        "ttl_minutes": config.TTL_MINUTES,
    }
