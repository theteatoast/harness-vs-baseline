"""Verifier: the exploitability gate. Keeps a candidate finding only if it is REAL and
EXPLOITABLE (a concrete attack vector); drops theoretical smells and correctness noise.
This is the harness's precision mechanism."""
from ..parsing import parse_findings

VERIFIER_PROMPT = (
    "You are a senior security reviewer verifying candidate findings in ONE file. "
    "Keep a finding ONLY if it is REAL and EXPLOITABLE: you can name a concrete attack "
    "vector (attacker-controlled input reaching a reachable, impactful sink). Drop "
    "theoretical smells, non-exploitable correctness bugs, and duplicates.\n"
    'Respond with ONLY JSON: {"kept": [{"line": <int>, "vuln_type": "<short>", '
    '"cwe_guess": "CWE-<n>", "description": "<one sentence including the attack vector>", '
    '"confidence": <0..1>}]}'
)


def verify_file(client, corpus, path, findings, reasoning=None, max_tokens=6000):
    if not findings:
        return [], None
    content = corpus.read(path)
    candidates = "\n".join(
        f"- line {f.line}: {f.vuln_type} — {f.description}" for f in findings)
    prompt = (f"{VERIFIER_PROMPT}\n\nFILE: {path}\n{content}\n\n"
              f"CANDIDATE FINDINGS:\n{candidates}")
    resp = client.chat([{"role": "user", "content": prompt}],
                       max_tokens=max_tokens, reasoning=reasoning)
    return parse_findings(resp.text, key="kept", file=path), resp
