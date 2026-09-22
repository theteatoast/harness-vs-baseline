"""The vulnerable-app corpus: source access + ground truth + scoring.

Read-only. In-scope = the application logic where the ground-truth vulns live
(app/data, app/routes, server.js). Excludes app/views/tutorial/** — that is the
app's own documented answer key and must never be shown to the agent.
"""
import pathlib
import re

import yaml

from .base import Vuln
from . import scorer

INSCOPE = ["app/data/*.js", "app/routes/*.js", "server.js"]
EXCLUDE = {"app/routes/tutorial.js"}  # mounts the answer-key tutorial views


class AppCorpus:
    def __init__(self, root: str):
        self.root = pathlib.Path(root).resolve()
        cfg_path = self.root / "corpus.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text())
            self.inscope = cfg.get("inscope", INSCOPE)
            self.exclude = set(cfg.get("exclude", []))
        else:
            self.inscope, self.exclude = INSCOPE, EXCLUDE

    def files(self) -> list:
        out = []
        for pattern in self.inscope:
            for p in sorted(self.root.glob(pattern)):
                rel = str(p.relative_to(self.root))
                if rel not in self.exclude:
                    out.append(rel)
        return out

    def _resolve(self, path: str) -> pathlib.Path:
        p = (self.root / path).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"path escapes corpus root: {path}")
        return p

    def read(self, path: str, start: int = None, end: int = None) -> str:
        lines = self._resolve(path).read_text().splitlines()
        s = max(1, start or 1)
        e = min(len(lines), end or len(lines))
        return "\n".join(f"{i:5d}\t{lines[i - 1]}" for i in range(s, e + 1))

    def search(self, pattern: str) -> list:
        rx = re.compile(pattern)
        matches = []
        for rel in self.files():
            for i, line in enumerate(self._resolve(rel).read_text().splitlines(), 1):
                if rx.search(line):
                    matches.append({"file": rel, "line": i, "text": line.strip()})
        return matches

    def task_prompt(self) -> str:
        files = "\n".join(f"  - {f}" for f in self.files())
        return (
            "You are auditing the source code of a web application for security "
            "vulnerabilities.\nThe in-scope source files (paths relative to the app "
            f"root) are:\n{files}\n\n"
            "Report every distinct vulnerability you find. For each, give: the file, "
            "the line number, a short vulnerability type (with a CWE id if you know it), "
            "and a one-sentence description."
        )

    def ground_truth(self) -> list:
        data = yaml.safe_load((self.root / "ground_truth.yaml").read_text())
        return [Vuln(**v) for v in data["vulns"]]

    def score(self, findings):
        return scorer.score(findings, self.ground_truth())
