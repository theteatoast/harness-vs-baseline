"""Build the comparison table from saved trajectories, grouped by model.

Every number is recomputed from committed results/*.json — no hand-entry.
"""
import json

from ..config import ROOT


def _load():
    out = []
    for p in sorted((ROOT / "results").glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except (ValueError, OSError):
            pass
    return out


def _label(r):
    if r["arm"] == "baseline":
        return "baseline (single-shot)"
    abl = (r.get("config") or {}).get("ablation") or {}
    return f"harness P{int(abl.get('planner', True))}V{int(abl.get('verifier', True))}"


def _short(model):
    return model.split("/")[-1]


def _row(r):
    s, u = r["score"], r["usage"]
    matched = len(s["matched"])
    total = matched + len(s["missed"])
    toks = u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)
    cost = u.get("cost_usd")
    cost_s = f"${cost:.4f}" if cost is not None else "n/a"
    return (f"| {_short(r['model'])} | {_label(r)} | {len(r['findings'])} | "
            f"{s['recall']:.2f} ({matched}/{total}) | {s['precision']:.2f} | {s['f1']:.2f} | "
            f"{u.get('calls', 1)} | {toks} | {cost_s} |")


def main():
    results = _load()
    if not results:
        print("no results yet")
        return

    order = {"baseline (single-shot)": 0, "harness P1V0": 1, "harness P0V1": 2, "harness P1V1": 3}
    results.sort(key=lambda r: (_short(r["model"]), order.get(_label(r), 9)))

    print("| model | config | findings | recall | precision | f1 | calls | tokens | cost |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        print(_row(r))

    for model in sorted({r["model"] for r in results}):
        rs = [r for r in results if r["model"] == model]
        base = next((r for r in rs if r["arm"] == "baseline"), None)
        full = next((r for r in rs if _label(r) == "harness P1V1"), None)
        if not (base and full):
            continue
        bs, fs = base["score"], full["score"]
        print(f"\n### {_short(model)}")
        print(f"- recall: {bs['recall']:.2f} -> {fs['recall']:.2f}   "
              f"precision: {bs['precision']:.2f} -> {fs['precision']:.2f}   "
              f"f1: {bs['f1']:.2f} -> {fs['f1']:.2f}")
        recovered = sorted(set(bs["missed"]) & {m[2] for m in fs["matched"]})
        if recovered:
            print(f"- vulns the harness recovered that single-shot missed ({len(recovered)}): "
                  f"{recovered}")


if __name__ == "__main__":
    main()
