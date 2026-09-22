"""Model pricing registry, for per-run cost accounting."""
from ..config import load_yaml

_REGISTRY = None


def registry() -> dict:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = load_yaml("models.yaml")["models"]
    return _REGISTRY


def cost(model: str, prompt_tokens: int, completion_tokens: int):
    """USD cost for a call, or None if the model isn't in the registry
    (we record None rather than guess a price)."""
    m = registry().get(model)
    if not m:
        return None
    return prompt_tokens * m["input_per_token"] + completion_tokens * m["output_per_token"]
