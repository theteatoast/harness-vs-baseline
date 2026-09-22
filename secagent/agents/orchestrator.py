"""Orchestrator: runs the Planner -> Worker -> Verifier loop.

Planner (deterministic): decompose the audit into per-file subtasks — this forces
coverage of every file, the recall mechanism. Worker audits each file; Verifier (if on)
applies the exploitability gate. Per-file audits run concurrently to keep wall-clock low.
"""
from concurrent.futures import ThreadPoolExecutor

from . import worker, verifier


def _accumulate(usages) -> dict:
    pt = ct = calls = 0
    cost = 0.0
    cached_all = True
    for r in usages:
        if r is None:
            continue
        calls += 1
        pt += r.prompt_tokens
        ct += r.completion_tokens
        cost += r.cost_usd or 0.0
        cached_all = cached_all and r.cached
    return {"prompt_tokens": pt, "completion_tokens": ct,
            "cost_usd": round(cost, 6), "calls": calls, "cached": cached_all}


def run_harness(corpus, client, ablation, reasoning=None, max_workers=6):
    files = corpus.files()                       # planner: per-file decomposition
    use_verifier = ablation.get("verifier", True)

    def audit(path):
        findings, w_resp = worker.audit_file(client, corpus, path, reasoning)
        usages = [w_resp]
        if use_verifier and findings:
            kept, v_resp = verifier.verify_file(client, corpus, path, findings, reasoning)
            usages.append(v_resp)
        else:
            kept = findings
        return kept, usages

    all_findings, all_usages = [], []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for kept, usages in ex.map(audit, files):
            all_findings.extend(kept)
            all_usages.extend(usages)
    return all_findings, _accumulate(all_usages)
