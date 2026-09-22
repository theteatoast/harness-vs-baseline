"""Objective matcher: map free-text findings onto ground-truth vulns.

A finding matches a vuln iff:  same file  AND  line within [start-tol, end+tol]
AND  the type is compatible (exact CWE id match, or the vuln's keywords appear in
the finding's type/description). Deterministic and free — no LLM in the loop.
Each vuln is matched by at most one finding; leftover findings are false positives.
"""
import re

from .base import ScoreResult


def _norm_cwe(s: str) -> str:
    m = re.search(r"cwe[-_ ]?(\d+)", (s or "").lower())
    return f"CWE-{m.group(1)}" if m else ""


def _norm_path(p: str) -> str:
    p = (p or "").strip().lstrip("./")
    for prefix in ("targets/nodegoat/",):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return p


def _type_match(vuln, finding) -> bool:
    guess = _norm_cwe(finding.cwe_guess) or _norm_cwe(finding.vuln_type)
    if guess and guess == vuln.cwe:
        return True
    text = f"{finding.vuln_type} {finding.description}".lower()
    return any(kw.lower() in text for kw in vuln.keywords)


def score(findings, vulns, line_tol: int = 8) -> ScoreResult:
    used = set()
    matched = []
    for v in vulns:
        for i, f in enumerate(findings):
            if i in used or _norm_path(f.file) != _norm_path(v.file):
                continue
            if not (v.line_start - line_tol <= f.line <= v.line_end + line_tol):
                continue
            if not _type_match(v, f):
                continue
            matched.append((f, v))
            used.add(i)
            break

    matched_ids = {v.id for _, v in matched}
    missed = [v for v in vulns if v.id not in matched_ids]
    false_positives = [f for i, f in enumerate(findings) if i not in used]

    recall = len(matched) / len(vulns) if vulns else 0.0
    precision = len(matched) / len(findings) if findings else 0.0
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) else 0.0
    return ScoreResult(matched=matched, missed=missed, false_positives=false_positives,
                       recall=recall, precision=precision, f1=f1)
