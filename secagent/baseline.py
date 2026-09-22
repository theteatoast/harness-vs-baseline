"""Baseline arm: the naive single-shot audit we aim to beat.

Whole in-scope source in one prompt, one model call, parse the JSON findings.
No tools, no planner, no verifier. Intentionally the naive approach.
"""
from .parsing import parse_findings

FINDINGS_INSTRUCTION = (
    'Respond with ONLY a JSON object of this exact form and no prose:\n'
    '{"findings": [{"file": "<path>", "line": <int>, "vuln_type": "<short type>", '
    '"cwe_guess": "CWE-<n>", "description": "<one sentence>", "confidence": <0..1>}]}\n'
    'List every vulnerability you can find.'
)


def _corpus_dump(corpus) -> str:
    parts = []
    for rel in corpus.files():
        parts.append(f"===== FILE: {rel} =====\n{corpus.read(rel)}")
    return "\n\n".join(parts)


def run_baseline(corpus, client, max_tokens: int = 20000, reasoning=None):
    prompt = (corpus.task_prompt() + "\n\n" + FINDINGS_INSTRUCTION + "\n\n"
              + "SOURCE:\n" + _corpus_dump(corpus))
    resp = client.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens,
                       reasoning=reasoning)
    return parse_findings(resp.text, key="findings"), resp
