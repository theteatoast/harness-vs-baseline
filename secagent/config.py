"""Config + secrets loading. Never prints or logs the API key."""
import os
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load KEY=VALUE lines from .env into the environment (without overriding
    values already set in the real environment)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def load_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "configs" / name).read_text())


def api_key() -> str:
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (put it in .env at the repo root)")
    return key
