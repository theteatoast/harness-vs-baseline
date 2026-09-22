"""Model-agnostic OpenRouter client.

Design choices (both for budget + model-agnosticism):
  * On-disk response cache keyed by (model, temperature, max_tokens, messages) so
    re-running anything downstream never re-bills the model.
  * dry_run mode returns a stub so all plumbing can be tested with zero API calls.
  * Uses the stdlib (urllib) so there is no extra dependency to break on new Python.
"""
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..config import ROOT, api_key
from . import models as pricing

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float | None = None
    cached: bool = False


def extract_json(text: str):
    """Pull the first JSON object out of a model reply, tolerating ``` fences and
    surrounding prose. Returns the parsed dict, or None. Reused by the worker's
    parse-based action protocol."""
    s = text.strip()
    if s.startswith("```"):
        parts = s.split("```")
        s = parts[1] if len(parts) >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        a, b = s.find(open_c), s.rfind(close_c)
        if a != -1 and b != -1 and b > a:
            try:
                return json.loads(s[a:b + 1])
            except json.JSONDecodeError:
                continue
    return None


class LLMClient:
    def __init__(self, model: str, temperature: float = 0.2, cache: bool = True,
                 dry_run: bool = False):
        self.model = model
        self.temperature = temperature
        self.cache = cache
        self.dry_run = dry_run
        self.cache_dir = ROOT / "results" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, messages, max_tokens, reasoning) -> str:
        payload = json.dumps(
            {"model": self.model, "temp": self.temperature, "max_tokens": max_tokens,
             "reasoning": reasoning, "messages": messages},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def chat(self, messages, max_tokens: int = 1024, reasoning=None) -> LLMResponse:
        if self.dry_run:
            return LLMResponse(text='{"action": "done", "summary": "dry-run stub"}')

        cache_file = self.cache_dir / f"{self._cache_key(messages, max_tokens, reasoning)}.json"
        if self.cache and cache_file.exists():
            d = json.loads(cache_file.read_text())
            return LLMResponse(text=d["text"], prompt_tokens=d["prompt_tokens"],
                               completion_tokens=d["completion_tokens"],
                               cost_usd=d["cost_usd"], cached=True)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if reasoning is not None:
            payload["reasoning"] = reasoning
        body = json.dumps(payload).encode()
        req = urllib.request.Request(OPENROUTER_URL, data=body, headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "X-Title": "secagent-harness",
        })
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OpenRouter HTTP {e.code}: {e.read().decode()[:600]}")

        if "choices" not in data:
            raise RuntimeError(f"Unexpected OpenRouter response: {json.dumps(data)[:600]}")

        text = data["choices"][0]["message"].get("content") or ""
        usage = data.get("usage") or {}
        pt = usage.get("prompt_tokens", 0)
        ct = usage.get("completion_tokens", 0)
        resp = LLMResponse(text=text, prompt_tokens=pt, completion_tokens=ct,
                           cost_usd=pricing.cost(self.model, pt, ct))

        if self.cache:
            cache_file.write_text(json.dumps({
                "text": text, "prompt_tokens": pt, "completion_tokens": ct,
                "cost_usd": resp.cost_usd,
            }))
        return resp


def _smoke():
    """One tiny real call: verify connectivity, cost accounting, and that we can
    parse a JSON action out of the reply (the parse-based protocol foundation)."""
    from ..config import load_yaml
    cfg = load_yaml("default.yaml")
    client = LLMClient(cfg["model"], temperature=0)
    messages = [{"role": "user", "content":
                 'Respond with ONLY a JSON object and no other text, exactly of the '
                 'form {"action": "read_file", "path": "app.js"}.'}]
    r = client.chat(messages, max_tokens=100)
    print(f"model={client.model}  cached={r.cached}")
    print(f"reply={r.text!r}")
    print(f"parsed_action={extract_json(r.text)}")
    print(f"tokens: in={r.prompt_tokens} out={r.completion_tokens}  cost=${r.cost_usd:.6f}")


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        _smoke()
    else:
        print("usage: python -m secagent.llm.client --smoke")
