"""Phase-1 verify: prove the scorer + corpus work BEFORE any model runs.

Feeds a hand-written, deliberately-partial findings list and checks that the
scorer correctly reports matches (via exact CWE, via keywords, and within the
line tolerance), misses, and false positives. No API calls.
"""
import pathlib

from secagent.corpus.app_corpus import AppCorpus
from secagent.corpus.base import Finding

ROOT = str(pathlib.Path(__file__).resolve().parents[1] / "targets" / "nodegoat")


def main():
    corpus = AppCorpus(ROOT)
    gt = corpus.ground_truth()
    print(f"ground-truth vulns: {len(gt)}")

    findings = [
        # exact CWE match
        Finding(file="app/routes/contributions.js", line=32, vuln_type="Code Injection",
                description="eval() on user-supplied request body", cwe_guess="CWE-95"),
        # keyword match, line within tolerance (vuln is 70-73)
        Finding(file="app/routes/index.js", line=71, vuln_type="Open Redirect",
                description="redirect target taken from req.query.url"),
        # keyword match, line just outside the range but within tolerance (vuln 77-79)
        Finding(file="app/data/allocations-dao.js", line=82, vuln_type="NoSQL injection",
                description="$where clause built from unsanitized threshold"),
        # false positive — no vuln in memos.js
        Finding(file="app/routes/memos.js", line=5, vuln_type="SQL Injection",
                description="not a real issue"),
    ]

    res = corpus.score(findings)
    print(f"recall={res.recall:.2f} precision={res.precision:.2f} f1={res.f1:.2f}")
    print("matched:", [(f.file, v.id) for f, v in res.matched])
    print("false positives:", [(f.file, f.line) for f in res.false_positives])

    assert len(res.matched) == 3, f"expected 3 matches, got {len(res.matched)}"
    assert len(res.false_positives) == 1, res.false_positives
    assert res.false_positives[0].file == "app/routes/memos.js"
    assert len(res.missed) == len(gt) - 3
    print("SCORER TEST PASSED")


if __name__ == "__main__":
    main()
