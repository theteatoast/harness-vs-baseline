# CLAUDE.md — Project Instructions

Project-specific guidance for Claude Code. This sits **below** the global
`~/.claude/CLAUDE.md` (Karpathy guidelines), which remain fully in force.

## What this project is

A model-agnostic **offensive-security agent harness** — `Planner → Worker → Verifier` —
that finds vulnerabilities in a codebase, and a **differential benchmark** proving the
harness beats a naive baseline. The core experiment, holding the **model fixed**:

> single-shot baseline ("here's the code, list every vulnerability") **vs.** the same model
> driven through our harness — measured by how many *known* vulnerabilities each finds.

Built from scratch — no agent framework. The point is to speak firsthand to **harness
design** and **benchmarking**, the two things the Sarvam Cyber Team role cares about.

Scope note: this benchmarks vulnerability **discovery** (static code audit), not
**exploitation**. That is deliberate — it's the cheapest-to-verify stage of find→prove→fix,
and it isolates the harness's contribution. Exploitation is the same harness with an
execution sandbox swapped into the corpus layer (a documented future extension, not in the
two-day scope).

See `ARCHITECTURE.md` (design), `PLAN.md` (schedule), `BENCHMARKING.md` (eval method).

## Hard constraints: ~2 days, low budget

- Bias hard to the minimum real thing (Karpathy #2). The **harness** is the star, not
  corpus size.
- **Cost:** one cheap open model does the whole primary experiment. Both arms (baseline +
  harness) run on the *same* model, so a full pass is cents. A second/frontier model is an
  optional bonus, not required. Enforce token/step budgets in the orchestrator.

## Stack

- Python 3.11+
- **OpenRouter** for every model call (config-driven model swap).
- **No Docker** for the core experiment — this is read-only static analysis over a locally
  vendored copy of a vulnerable app's source. (Docker only returns if we ever add the
  exploitation extension.)
- Minimal deps: `httpx`, `pydantic`, `pyyaml`, optionally `rich` for reports. **No agent
  framework.**

## Layout (target)

```
secagent/
  config.py             # load configs/*.yaml (models, budgets, ablation flags)
  llm/client.py         # OpenRouter model-agnostic client (chat + tool-calling + usage/cost)
  llm/models.py         # model registry + $/token for cost accounting
  agents/planner.py     # route the codebase into audit regions + replan
  agents/worker.py      # ReAct loop: read/search code, report findings
  agents/verifier.py    # confirm each finding is real (re-read + reason), dedupe, coverage check
  agents/orchestrator.py# run P/W/V under step/token budgets
  tools/registry.py     # tool schemas + dispatch
  tools/code.py         # read_file, list_files, search_code, report_finding, done
  corpus/base.py        # Corpus interface (source access + ground truth + scorer)
  corpus/app_corpus.py  # loads a vendored vulnerable app + its ground_truth.yaml
  corpus/scorer.py      # match findings -> ground truth; recall / precision / F1
  baseline.py           # single-shot baseline runner (the arm we beat)
  eval/runner.py        # run both arms over the corpus
  eval/report.py        # baseline-vs-harness markdown table
  trajectory.py         # structured per-run JSONL schema
targets/<app>/          # vendored vulnerable-app source + ground_truth.yaml
configs/{default.yaml,models.yaml}
results/                # trajectories + reports (git-ignored except final RESULTS.md)
tests/
```

## How to run (filled during coding)

- Smoke test the gateway: `python -m secagent.llm.client --smoke`
- Baseline arm: `python -m secagent.eval.runner --arm baseline --config configs/default.yaml`
- Harness arm:  `python -m secagent.eval.runner --arm harness  --config configs/default.yaml`
- Report:       `python -m secagent.eval.report`

## Safety

- The agent performs **read-only static analysis** of a deliberately-vulnerable app's source
  that we vendored locally. It does not execute the target and makes no network requests to
  any target. This is about as low-risk as offensive tooling gets — keep it that way.
- Only point it at code we're authorized to review (our vendored, intentionally-vulnerable
  target). Do not repurpose it against arbitrary third-party code.

## Working conventions

- **Invoke the `karpathy-guidelines` skill before any coding session.** (Global rule,
  restated so it isn't missed.)
- Surgical changes; match existing style; no speculative abstraction or config.
- Every phase in `PLAN.md` has a verify step — run it before moving on (Karpathy #4).
- Structured logs over prints: every run writes a trajectory JSONL under `results/`.
- **Cost accounting is first-class** — record tokens + `$` per run, both arms.
- The `ground_truth.yaml` and the scorer's matching rule are the spine of every number.
  Get them right early; no metric is valid that a committed trajectory can't reproduce.
- Don't invent OpenRouter model slugs, prices, or the target app's vuln list — confirm
  against the source before hardcoding.
