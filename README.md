# Harness — Offensive-Security Agent Harness

A model-agnostic `Planner → Worker → Verifier` agent harness for offensive security. It
finds vulnerabilities in a codebase, and a **differential benchmark** proves the harness
beats a naive baseline: holding the model fixed, a single-shot prompt misses vulnerabilities
that the same model — driven through the harness — recovers. Built from scratch (no agent
framework) to study **harness design** and **benchmarking** firsthand.

- **Design:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Two-day plan:** [PLAN.md](./PLAN.md)
- **Eval method:** [BENCHMARKING.md](./BENCHMARKING.md)
- **Instructions for Claude Code:** [CLAUDE.md](./CLAUDE.md)

## Safety

The agent performs **read-only static analysis** of a deliberately-vulnerable app's source,
vendored locally. It does not execute the target or make network requests to it. Only point
it at code you're authorized to review.

## Status

Planning complete; coding starts at Phase 0 in `PLAN.md`.
