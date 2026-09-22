"""Shared: turn a model's JSON reply into Finding objects.

Robust to truncation: weak/verbose models often blow past the output cap, leaving an
unterminated JSON array. When the clean parse yields nothing, we salvage every complete
{...} object from the text so a truncated response still contributes the findings it did
emit (rather than scoring a misleading zero).
"""
import json

from .corpus.base import Finding
from .llm.client import extract_json


def _salvage_objects(text: str) -> list:
    """Recover every balanced {...} object, even inside an unterminated array."""
    objs, stack = [], []
    for i, ch in enumerate(text):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            frag = text[stack.pop():i + 1]
            try:
                o = json.loads(frag)
            except json.JSONDecodeError:
                continue
            if isinstance(o, dict):
                objs.append(o)
    return objs


def parse_findings(text: str, key: str = "findings", file: str = None) -> list:
    data = extract_json(text)
    if isinstance(data, dict):
        raw = data.get(key, [])
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    if not raw:  # truncated / malformed — salvage individual finding objects
        raw = [o for o in _salvage_objects(text) if "line" in o or "vuln_type" in o]

    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        try:
            out.append(Finding(
                file=file if file is not None else r.get("file", ""),
                line=int(r.get("line", 0) or 0),
                vuln_type=r.get("vuln_type", ""),
                description=r.get("description", ""),
                cwe_guess=r.get("cwe_guess", ""),
                confidence=float(r.get("confidence", 0.5) or 0.5),
            ))
        except (TypeError, ValueError):
            continue
    return out
