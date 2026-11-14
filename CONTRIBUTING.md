# Contributing

Thanks for helping make research with AI trustworthy.

- **Setup:** `git clone`, then `python -m pytest -q`. Standard library only, Python 3.10+.
- **The one rule: precision over recall.** A check that wrongly accuses a paper or a researcher does more harm than a missed error. Anything code can't decide is "unchecked", never "wrong". An unreachable registry is never a failure.
- **Every new check ships with tests:** one it must catch and, more importantly, the near-misses it must not flag. False-positive fixes get a regression test named after the case.
- **Hooks must never break a session.** Any exception is swallowed and logged to stderr.
- **Never publish identities** of papers or people flagged by a benchmark. Report aggregates, and keep identifiers local.
- Architecture and module map: `docs/handoff/ARCHITECTURE.md`. Release steps: `AGENTS.md`.
