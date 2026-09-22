# ROADMAP.md — Beyond the Two-Day Build

The two-day build proves the core thesis cheaply: *same model, the harness finds more real
vulns and reports less noise than a single-shot baseline.* This file records the
enhancements that turn it into a **realistic white-box security harness**, deliberately
deferred so we ship the core first. Order: ship core → (1) → (2) → (3) → (4).

## Guiding principle: exploitable, not theoretical

A finding only counts if a **real attacker has a real, reachable attack vector to it**.
Static "code smells" with no reachable, impactful exploit are noise. The harness's value is
as much about **suppressing noise (precision)** as **finding more (recall)**.

> This principle is ALREADY in scope for the Verifier's exploitability gate
> (see `ARCHITECTURE.md`). The items below *deepen* it.

## 1. Exploitability-first triage (deepen the verifier)
- For each candidate, force a concrete chain: **entry point → attacker-controlled input →
  reachable sink → impact.** No chain ⇒ drop or downgrade.
- **Reachability:** is the sink actually reachable from an exposed route/handler with
  attacker data? Trace call paths, don't just pattern-match.
- **Severity/impact scoring** so findings are ranked, not just listed.

## 2. White-box historical / context signals (what a real auditor actually uses)
- **Recent commits & comments** — mine `git log`, `TODO`/`FIXME`/`HACK`/`temp` comments;
  recent churn and developer asides concentrate bugs.
- **Recent fixes / diffs → variant analysis** — a fix in one spot usually means the same
  pattern exists unfixed elsewhere; sweep for siblings.
- **This product's own past CVEs** — prime the hunt for regressions / incomplete fixes.
- **CVEs in similar products / same stack** — known vuln classes for the framework, ORM,
  template engine, and dependencies tell you where to look.
- **Pattern mining** — once one instance of a class is found, sweep the whole codebase for
  the same pattern.

## 3. The offense loop (find → prove → fix)
- **Prove:** swap an execution sandbox into the corpus layer so a confirmed finding is
  *demonstrated* with a working PoC, not just asserted (the CVE-Bench-style exploitation
  extension). The harness code is unchanged; only the environment layer gains execution.
- **Fix:** generate a patch, re-run the PoC to confirm it's closed, human-in-the-loop.
  Completes Sarvam's find→prove→fix loop.

## 4. Scale & rigor
- Larger / public labeled corpora and real CVE datasets for statistically meaningful `n`.
- Multi-model matrix (frontier vs open) reporting **accuracy per dollar**.
- Zero-day vs one-day settings (info given vs black-box discovery).

## Sequencing
Each item is independently demoable. Ship the core recall+precision result on NodeGoat first;
everything here is an increment on a working, measured baseline — never a rewrite.
