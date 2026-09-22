"""Worker: a focused security audit of ONE file. This per-file focus is the
coverage mechanism — a single-shot pass over the whole codebase under-enumerates."""
from ..parsing import parse_findings

WORKER_PROMPT = (
    "You are a security code auditor examining ONE source file from a web application. "
    "Identify every genuinely EXPLOITABLE vulnerability — one a real attacker could trigger, "
    "with attacker-controlled input reaching an impactful sink. Ignore stylistic issues and "
    "non-exploitable correctness bugs.\n"
    'Respond with ONLY JSON: {"findings": [{"line": <int>, "vuln_type": "<short>", '
    '"cwe_guess": "CWE-<n>", "description": "<one sentence>", "confidence": <0..1>}]}'
)


def audit_file(client, corpus, path, reasoning=None, max_tokens=6000):
    content = corpus.read(path)
    prompt = f"{WORKER_PROMPT}\n\nFILE: {path}\n{content}"
    resp = client.chat([{"role": "user", "content": prompt}],
                       max_tokens=max_tokens, reasoning=reasoning)
    return parse_findings(resp.text, key="findings", file=path), resp
