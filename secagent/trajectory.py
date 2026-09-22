"""Persist a run: findings + score + usage. Every metric is recomputable from these."""
import json
from dataclasses import asdict

from .config import ROOT


def save_run(arm: str, model: str, config: dict, findings, score, usage: dict) -> str:
    record = {
        "arm": arm,
        "model": model,
        "config": config,
        "findings": [asdict(f) for f in findings],
        "score": {
            "recall": round(score.recall, 4),
            "precision": round(score.precision, 4),
            "f1": round(score.f1, 4),
            "matched": [[f.file, f.line, v.id] for f, v in score.matched],
            "missed": [v.id for v in score.missed],
            "false_positives": [[f.file, f.line, f.vuln_type] for f in score.false_positives],
        },
        "usage": usage,
    }
    tag = model.replace("/", "_")
    if arm == "harness":
        abl = config.get("ablation") or {}
        suffix = f"_P{int(abl.get('planner', True))}V{int(abl.get('verifier', True))}"
    else:
        suffix = ""
    out = ROOT / "results" / f"{arm}{suffix}__{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2))
    return str(out)
