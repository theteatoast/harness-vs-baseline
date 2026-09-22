# BENCHMARKING.md — Evaluation Method

This project cares about *honest* benchmarking, not big numbers. This is the method we
commit to **before** seeing results, so we can't rationalize afterward.

## The experiment

**Differential, same-model.** Hold the model fixed; compare two arms on the same corpus:

| Arm | What it is |
|---|---|
| **baseline** | one prompt: "here is the code, list every vulnerability with file + line" |
| **harness** | the same model driven through Planner → Worker → Verifier |

The headline result is the **recall gap**: how many *known* vulnerabilities each arm finds
in the same code. This isolates the harness, the one variable that matters, from model
strength, and it's cheap because both arms share one model.

**Two axes, not one.** The ground truth is a curated set of *genuinely exploitable* vulns, so
the harness's advantage shows up two ways: **recall** — the planner forces coverage, so it
finds real vulns single-shot missed; and **precision** — the verifier's exploitability gate
drops theoretical smells / non-exploitable noise that a naive single-shot dump reports as
false positives. Report both. The precision gap is the "real attack vector vs static noise"
story (see `ROADMAP.md` for deepening the exploitability triage and white-box context signals).

## The corpus

A **real, deliberately-vulnerable web app**, vendored locally under `targets/<app>/`, plus a
hand-built `ground_truth.yaml`. Selection criteria (finalize the exact app in Phase 0):
- Vulns embedded in **ordinary-looking code**, *not* signposted by filename — otherwise the
  baseline finds everything and there's no story. (This rules DVWA down a notch; favors
  NodeGoat / OWASP Juice Shop / a compact vulnerable Flask app.)
- A **documented vuln inventory** we can turn into ground truth.
- **Small enough to be cheap** — whole source fits in a single baseline prompt so the
  comparison is fair (baseline sees everything; if it still misses vulns, that's real).

### `ground_truth.yaml` (the spine)
One entry per known vuln:
```yaml
- id: sqli-login
  file: routes/session.js
  line_start: 42
  line_end: 55
  cwe: CWE-89
  desc: "SQL injection in login via unparameterized query"
  keywords: [sql, injection, query, sanitiz]
```
Provenance (which tutorial/advisory each entry came from) goes in a comment or a sidecar
`ground_truth.sources.md`. This is an eval artifact — document it like one.

## Scoring (objective, cheap) — see `corpus/scorer.py`

A finding matches a ground-truth vuln iff: **same file** AND **line overlaps ±K** AND
**CWE family matches** (free-text type → CWE via a keyword table). One vuln ↦ at most one
finding. Rule-based and deterministic; an optional cheap LLM-judge only breaks logged ties.

## Metrics (all from the trajectory JSONL)

| Metric | Definition |
|---|---|
| **Recall** | matched ÷ total known vulns — *the headline* |
| **Precision** | matched ÷ total findings reported (real vs noise) |
| **F1** | harmonic mean |
| Missed | which known vulns each arm failed to find (name them) |
| False positives | reported findings that match nothing |
| **Tokens / $** | per run, per arm — the cost of the recall gain |
| Verifier calibration | for the harness: do `kept` findings correlate with real ones? |

## Experiments, in priority order

1. **Baseline vs harness** (same model). The core result. Do this first and completely.
2. **Ablation** (harness only, same model): `verifier=off` (expect precision drop) and, if
   time, `planner=off` (expect recall/coverage drop). Shows what each component *buys*.
3. **Bonus, if budget allows:** run the harness on a second model (one open, one frontier
   via OpenRouter) — report recall **and** `$`/run. "Where is open-source close enough, and
   at what cost." Confirm exact slugs + pricing before running. Skip if it risks the budget.

## Results table format (`RESULTS.md`)

```
Target: <app>   n_vulns = <N>   model = <fixed>   date: <fill>

Core (same model):
  arm       | recall | precision |  f1  | tokens | $/run | vulns missed
  baseline  |  4/12  |    ...     | ...  |  ...   |  ...  | [ids...]
  harness   | 10/12  |    ...     | ...  |  ...   |  ...  | [ids...]

Ablation (harness):
  config        | recall | precision | $/run
  full          | 10/12  |    ...     |  ...
  verifier=off  | 10/12  |    ...     |  ...     <- precision should fall
```

## Honesty rules

- Report `n` (vuln count) and the *missed* vulns beside every recall number.
- The **trajectories are the evidence** — no number that a committed trajectory can't
  reproduce.
- If the harness *doesn't* clearly beat the baseline, that's the finding — fix the harness,
  don't fudge the corpus. The `ground_truth.yaml` is frozen once chosen.
- If open-source tool-calling is flaky, report it; it's a real result, not an embarrassment.
