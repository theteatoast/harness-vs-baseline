# PLAN.md — Two-Day Execution Plan

Each phase has a **verify step** (Karpathy #4). Don't advance until it passes. Times are
budgets; if a phase overruns, cut scope — never skip the verify.

**Definition of done:** a `Planner/Worker/Verifier` harness + a single-shot baseline, both
on the *same model* over one vulnerable app, with a `RESULTS.md` showing the **recall gap**
(harness finds vulns the baseline misses) + one ablation.

**Floor (if late):** baseline + harness both run and score on the corpus, with an honest
recall table — even a modest gap. Still a real "I built a harness and benchmarked it" story.

No Docker. No exploitation. Read-only static analysis over a vendored source tree.

---

## Day 1 — build the pieces

### Phase 0 — Scaffold + target + gateway  (~2h)  ⟵ invoke `karpathy-guidelines` first
- Python env, repo skeleton per `ARCHITECTURE.md`, `configs/`, `.gitignore` (ignore
  `results/` except `RESULTS.md`; ignore `.env`).
- `.env` with `OPENROUTER_API_KEY`; `llm/client.py` does one real chat call + one tool-call
  round-trip.
- **Pick and vendor the target app** into `targets/<app>/` (criteria in `BENCHMARKING.md` —
  vulns not signposted by filename; small enough for one prompt; documented vuln list).
- Start `ground_truth.yaml` — first pass, ~8–12 entries with `{file, line, cwe, desc}`.
- **Verify:** smoke test prints a model reply + a parsed tool call; `ground_truth.yaml`
  parses; we can `read`/`list` the vendored source.

### Phase 1 — Corpus + tools + scorer  (~2–3h)
- `corpus/base.py` + `corpus/app_corpus.py` (`load/files/read/search/ground_truth/score`).
- Tools `tools/code.py`: `list_files`, `read_file`, `search_code`, `report_finding`, `done`.
- `corpus/scorer.py`: file + line-overlap + CWE-family matching → recall/precision.
- **Verify:** feed a *hand-written* findings list (deliberately partial) to `score()` and
  confirm it correctly reports matched / missed / false-positive against the ground truth.
  (This proves the scorer before any model touches it — the scorer is the spine.)

### Phase 2 — Baseline arm  (~1.5–2h)
- `baseline.py` + `eval/runner.py --arm baseline`: whole source → one prompt → parse
  findings → score → trajectory JSONL.
- **Verify:** baseline produces a scored findings file with a real recall number and a
  cost/token count. Note which vulns it *misses* — that list is your target for the harness.

### Phase 3 — Harness arm  (~3h)
- `agents/{planner,worker,verifier,orchestrator}.py` wired with ablation flags + budgets.
- Run `--arm harness` on the corpus.
- **Verify:** harness runs unattended, respects budgets, writes a full trajectory with
  `findings` + `score`, and **recall ≥ baseline** on the corpus (ideally strictly greater —
  it recovers vulns the baseline missed). If not, tune the planner routing / worker prompt
  *before* Day 2.

---

## Day 2 — benchmark, ablate, write up

### Phase 4 — Metrics + report  (~2h)
- `eval/report.py`: baseline-vs-harness markdown table (recall, precision, f1, tokens,
  `$`/run, vulns missed).
- Harden the scorer against real findings (fix any obvious mis-matches; keep the rule
  deterministic).
- **Verify:** one command regenerates the full table from committed trajectories, reproducibly.

### Phase 5 — Ablation (+ optional 2nd model)  (~2–3h)
- **Ablation:** harness `verifier=off` (precision should fall); if time, `planner=off`
  (recall/coverage should fall). Same model throughout — cheap.
- **Optional, only if budget is comfortable:** re-run the harness on a second model (one
  open, one frontier) via OpenRouter — recall **and** `$`/run. Confirm slugs/pricing first.
- **Verify:** ablation table shows each component's marginal effect with real numbers.

### Phase 6 — Writeups (~2h)
- `RESULTS.md`: the numbers honestly — `n`, the *missed* vulns per arm, cost per arm, and
  what failed. Trajectories are the proof, not screenshots.
- Rehearse the narrative:
  1. **The recall gap** — same model, harness found the vulns single-shot missed, and *why*
     (planner forces coverage of every region; single-shot's attention drops vulns in long
     context).
  2. **Verifier calibration** — precision, and whether "kept" findings track real ones —
     i.e. does the agent know when a finding is real / when it's done (the JD's hard problem).
  3. **Ablation** — what the planner and verifier each bought.
  4. **Cost** — recall per dollar; and (if run) where open-source lands vs frontier.
  5. **Roadmap** — this is the *find* stage; exploitation = same harness + an execution
     sandbox in the corpus layer. Say it before they ask.

---

## Risk register
- **Weak recall gap** (baseline already finds most): pick a target with vulns buried in
  ordinary code, and/or a slightly larger source so single-shot attention drops some.
  Mitigated by the Phase-3 verify gate.
- **Scorer mis-matches** inflate/deflate numbers: build + test the scorer on a hand-written
  findings list in Phase 1, before any model output.
- **Budget:** same-model core costs cents; the optional 2nd model is the only real spend —
  gate it on `budget comfortable`.
- **Ground-truth quality:** ~8–12 well-localized, well-known vulns beats 40 sloppy ones.
  Frozen once chosen; document provenance.
