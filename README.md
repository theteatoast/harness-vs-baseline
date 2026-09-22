# harness-vs-baseline

A differential benchmark for a from-scratch security agent. It answers one question with numbers:

> Holding the **model fixed**, does driving it through a `Planner -> Worker -> Verifier` harness
> find more real vulnerabilities (and less noise) than a single-shot prompt that just says
> "here is the code, list every vulnerability"?

This is an **experiment and a benchmark**, not a production tool. The point is to study harness
design and honest evaluation firsthand, on a low budget, over about two days.

## What we built

Two runners race on the same code, graded by the same objective scorer. The **only** variable
is the harness.

| | |
|---|---|
| **Baseline** | One prompt, whole codebase in, one list of findings out. |
| **Harness** | `Planner` splits the audit into per-file subtasks, a `Worker` audits each file in focus, a `Verifier` keeps only findings with a real, named attack vector. |

Everything is written from scratch in Python: no agent framework. Every model call goes through
**OpenRouter**, so swapping the model is a one-line config change. Calls are cached to disk and
priced in dollars, which is why the whole study cost cents.

## What we found

The harness helps in two distinct situations, and knowing which one you are in is the actual result.

**1. Weak model: the harness recovers vulnerabilities the single-shot pass misses.**
On `llama-3.1-8b`, recall went from **0.16 to 0.45** and precision from **0.06 to 0.49**,
recovering **35** vulnerabilities the naive pass never reported. This is the "make a small,
cheap model perform closer to a strong one" story, measured.

**2. Strong model on noisy code: the harness removes false alarms.**
On `glm-5.3-flash`, the single-shot pass already found essentially everything, but flagged a lot
of non-exploitable noise. The verifier's exploitability gate rejected **all 75** decoys, taking
precision from **0.81 to 1.00**.

**The honest flip side:** a strong model auditing clean code finds it all in one shot, so there
the harness adds no recall and just costs more (about 2.3x). Deploying it selectively is the
judgment call, and the benchmark is what tells you when.

### Numbers

| model | config | recall | precision | f1 | cost |
|---|---|---|---|---|---|
| glm-5.3-flash | baseline (single-shot) | 1.00 | 0.81 | 0.90 | $0.0112 |
| glm-5.3-flash | harness (full) | 0.96 | **1.00** | **0.98** | $0.0256 |
| llama-3.1-8b | baseline (single-shot) | 0.16 | 0.06 | 0.09 | $0.0036 |
| llama-3.1-8b | harness (full) | **0.45** | **0.49** | **0.47** | $0.0082 |

**Ablation (glm, on the decoy corpus)** shows each stage earns its place:

| config | recall | precision | decoys wrongly flagged |
|---|---|---|---|
| baseline | 1.00 | 0.81 | 23 |
| + per-file planner/worker | 0.98 | 0.90 | 11 |
| + verifier gate | 0.96 | **1.00** | **0** |

Precision rises at every step. Recall dips gently (1.00 to 0.96) as filtering tightens, a
quantified tradeoff rather than a free win. Full write-up with every caveat:
[results/RESULTS.md](./results/RESULTS.md). Whole benchmark, including development, cost under
about $0.15.

## How the corpus works

Real famous apps (we first tried OWASP NodeGoat) are memorized by the models, so single-shot
recall saturates and there is nothing to measure. So `targets/synthapp` is **generated**: 50
files, roughly 4,100 lines, **99 planted exploitable vulnerabilities** (36 of them subtle and
bypass-style) plus **75 non-exploitable decoys** that look suspicious but have no attack vector.
Ground-truth lines are correct by construction. The scorer (`secagent/corpus/scorer.py`) is
purely objective: a finding counts only if it lands on the right file, within 8 lines, with a
matching vulnerability class. No model grades the results.

## Layout

```
secagent/
  llm/            OpenRouter client (cached, cost-tracked) + model registry
  corpus/         Corpus interface, synthetic/real loaders, objective scorer
  tools/          read-only code tools (list, read, search, report_finding, done)
  agents/         planner, worker, verifier, orchestrator
  baseline.py     single-shot arm
  eval/           runner (both arms) + report (comparison table)
targets/
  synthapp/       generated corpus + ground truth (_generate.py)
  nodegoat/       vendored real app + ground truth (kept for reference)
configs/          default.yaml, weak.yaml, noverif.yaml, models.yaml
results/          trajectories (*.json) + RESULTS.md
tests/            scorer test (no API calls)
```

## Reproduce

```bash
python targets/synthapp/_generate.py                          # regenerate corpus + ground truth
python -m secagent.eval.runner --arm baseline --config default.yaml
python -m secagent.eval.runner --arm harness  --config default.yaml   # full harness
python -m secagent.eval.runner --arm harness  --config noverif.yaml   # ablation: verifier off
python -m secagent.eval.runner --arm baseline --config weak.yaml      # weak model
python -m secagent.eval.runner --arm harness  --config weak.yaml
python -m secagent.eval.report                                        # rebuild the table
```

Needs an OpenRouter key in `.env` as `OPENROUTER_API_KEY` (gitignored, never printed). Cached
runs re-score for free.

## Documentation

- **Design:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Eval method:** [BENCHMARKING.md](./BENCHMARKING.md)
- **Two-day plan:** [PLAN.md](./PLAN.md)
- **Future work:** [ROADMAP.md](./ROADMAP.md)
- **Instructions for Claude Code:** [CLAUDE.md](./CLAUDE.md)

## Safety

The agent performs **read-only static analysis** of a deliberately-vulnerable app's source,
vendored locally. It does not execute the target and makes no network requests to it. Only point
it at code you are authorized to review.

## Status

Working pilot, complete end to end and benchmarked. It is a study of harness design and
evaluation, not production security tooling. Known limits (synthetic corpus, a verifier that
slightly over-rejects, a weak-model verifier that is itself weak) are documented in
[results/RESULTS.md](./results/RESULTS.md), and next steps are in [ROADMAP.md](./ROADMAP.md).
