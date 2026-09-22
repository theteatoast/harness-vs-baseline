# ARCHITECTURE.md — The Harness

The harness is a `Planner → Worker → Verifier` loop over a **Corpus** (a vulnerable
codebase + its ground truth + a scorer) and a model-agnostic **LLM gateway**. Everything is
built by us; no agent framework. Design goal: make the **marginal contribution of the
harness measurable** against a single-shot baseline on the *same model*.

```
   ┌─────────────────────────────┐          ┌──────────────────────────────┐
   │   BASELINE arm (to beat)     │          │        HARNESS arm            │
   │   one prompt: "find all      │          │   Orchestrator (budgets)      │
   │   vulns in this code" ───────┼───┐      │   Planner → Worker → Verifier │
   └─────────────────────────────┘   │      └───────────────┬──────────────┘
                                      │                      │
                            findings[]│                      │findings[]
                                      ▼                      ▼
                        ┌───────────────────────────────────────────────┐
                        │   Corpus.score(findings)  ==  GROUND TRUTH      │
                        │   match to ground_truth.yaml → recall/precision │
                        └───────────────────────────────────────────────┘

   Harness internals:
     Planner  ── routes source files into audit regions; replans on low coverage
     Worker   ── ReAct loop: read_file / list_files / search_code → report_finding
     Verifier ── re-reads each reported finding, confirms it's real, dedupes;
                 checks coverage ("audited all high-risk files?") → triggers replan
     Gateway  ── OpenRouter: chat(messages, tools) → text + tool_calls + usage + cost
```

Both arms use the **same model** and the **same Corpus/scorer**. The only difference is the
harness. That is the whole experiment.

## Interfaces (sketch — implement in Phase 0–3)

### Corpus — `corpus/base.py`
Source-of-truth for the code, the ground truth, and grading. The harness never decides
ground truth itself.

```python
class Corpus:
    def load(self, target_id: str) -> None: ...       # ensure vendored source is present
    def files(self) -> list[str]: ...                  # in-scope source files
    def read(self, path, start=None, end=None) -> str: ...
    def search(self, pattern: str) -> list[Match]: ...
    def task_prompt(self) -> str: ...                  # what the agent is told about the target
    def ground_truth(self) -> list[Vuln]: ...          # from ground_truth.yaml
    def score(self, findings: list[Finding]) -> ScoreResult: ...
```
- `Vuln = {id, file, line_start, line_end, cwe, desc, keywords[]}`
- `Finding = {file, line, vuln_type, cwe_guess, description, confidence}`
- `ScoreResult = {matched[], missed[], false_positives[], recall, precision, f1}`

### Scorer / matcher — `corpus/scorer.py`  ← the crux
Maps free-text agent findings onto the fixed ground-truth list, objectively:
- **File** must match, **AND**
- **location** overlaps the vuln's line range (±K lines tolerance), **AND**
- **type** is compatible — map the finding's `vuln_type`/`cwe_guess` to a CWE family via a
  keyword table; a match requires the same family.
- Rule-based first (deterministic, free). An optional *cheap* single LLM-judge call may
  break genuinely ambiguous ties — logged explicitly, never the default path.
- Each ground-truth vuln can be matched by **at most one** finding (no double-counting);
  extra unmatched findings are false positives.

### LLM Gateway — `llm/client.py`
Model-agnostic. Swapping models is a config change, nothing else.
```python
class LLMClient:
    def __init__(self, model: str, temperature: float = 0.2): ...
    def chat(self, messages, tools=None) -> LLMResponse: ...
# LLMResponse = {text, tool_calls[], usage{prompt_tokens, completion_tokens}, cost_usd}
```
Cost from `llm/models.py`. Unknown model → cost recorded `null`, never guessed.

### Tools — `tools/code.py` (all read-only)
`{name, json_schema, fn(args, corpus) -> str}`. No shell, no network — static analysis only.
- `list_files()` / `read_file(path, start?, end?)` / `search_code(pattern)`
- `report_finding(file, line, vuln_type, description, confidence)` — appends to findings.
- `done(summary)` — agent declares coverage complete.

### Planner — `agents/planner.py`
```python
def plan(task, files) -> Plan            # order/group files into audit regions
def replan(task, history, coverage) -> Plan
```
Ablation `planner=off` → Worker gets the whole file list, no routing.

### Worker — `agents/worker.py`
ReAct loop over one region: read/search → reason → `report_finding`. Never ablated off.

### Verifier — `agents/verifier.py`
```python
def confirm(finding, corpus) -> Belief   # re-read; REAL & EXPLOITABLE? {keep, attack_vector, confidence, why}
def coverage(history, files) -> Gap       # any high-risk files unaudited? -> replan
```
**Exploitability gate (core, not optional).** A finding is kept only if the verifier can name
a concrete attack vector — attacker-controlled input reaching an impactful, *reachable* sink.
Theoretical code smells with no realistic vector are dropped. This is the harness's *second*
edge over single-shot (which dumps unranked noise): higher **precision**, not just higher
recall. Deepening this (reachability tracing, severity, variant sweeps) is in `ROADMAP.md`.

Two tiers, kept separate:
- **Ground truth** = `Corpus.score()` (objective; recall/precision vs `ground_truth.yaml`).
- **Self-verification** = the verifier's `keep/drop` and coverage judgments.
The orchestrator logs both, so we can report how well the agent's own confidence tracks
reality — the "does it know when it's actually done?" question from the JD. Ablation
`verifier=off` → every reported finding is kept as-is (expect lower precision).

### Orchestrator — `agents/orchestrator.py`
Drives P/W/V under budgets (`max_steps`, `max_tokens`, `wall_clock_s`), handles replan
triggers, writes the trajectory. Reads ablation flags from config.

## Trajectory schema — `trajectory.py`
One JSONL per (arm, model, config):
```
target_id, arm(baseline|harness), model, config{planner,verifier},
steps: [ {i, role, thought, tool, args, observation_truncated, tokens, cost_usd} ],
findings: [ {file, line, vuln_type, cwe_guess, description, confidence, kept_by_verifier} ],
score: { recall, precision, f1, matched, missed, false_positives },
final: { total_tokens, total_cost_usd, wall_clock_s, stop_reason }
```
Every metric in `BENCHMARKING.md` is computed from this. Get it right early.
