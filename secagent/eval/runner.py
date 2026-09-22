"""Run one arm over the corpus, score it, save the trajectory, print a summary."""
import argparse
import time

from ..config import ROOT, load_yaml
from ..corpus.app_corpus import AppCorpus
from ..llm.client import LLMClient
from ..trajectory import save_run
from .. import baseline as baseline_mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["baseline", "harness"], default="baseline")
    ap.add_argument("--config", default="default.yaml")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    corpus = AppCorpus(ROOT / "targets" / cfg["target"])
    client = LLMClient(cfg["model"], temperature=cfg.get("temperature", 0.2),
                       cache=cfg.get("cache", True), dry_run=cfg.get("dry_run", False))

    t0 = time.time()
    if args.arm == "baseline":
        findings, resp = baseline_mod.run_baseline(corpus, client,
                                                    reasoning=cfg.get("reasoning"))
        usage = {"prompt_tokens": resp.prompt_tokens,
                 "completion_tokens": resp.completion_tokens,
                 "cost_usd": resp.cost_usd, "cached": resp.cached}
    else:
        from ..agents.orchestrator import run_harness
        findings, usage = run_harness(corpus, client, cfg.get("ablation") or {},
                                      reasoning=cfg.get("reasoning"))
    usage["wall_clock_s"] = round(time.time() - t0, 2)

    score = corpus.score(findings)
    n = len(corpus.ground_truth())
    out = save_run(args.arm, cfg["model"], {"ablation": cfg.get("ablation")},
                   findings, score, usage)

    print(f"arm={args.arm}  model={cfg['model']}  cached={usage['cached']}")
    print(f"findings reported: {len(findings)}")
    print(f"recall={score.recall:.2f} ({len(score.matched)}/{n})  "
          f"precision={score.precision:.2f}  f1={score.f1:.2f}")
    print(f"tokens: in={usage['prompt_tokens']} out={usage['completion_tokens']}  "
          f"cost=${usage['cost_usd']}")
    print(f"MISSED ({len(score.missed)}): {[v.id for v in score.missed]}")
    print(f"false positives ({len(score.false_positives)}): "
          f"{[(f.file, f.line) for f in score.false_positives]}")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
