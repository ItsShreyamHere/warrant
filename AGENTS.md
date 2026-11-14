# AGENTS.md — warrant

Operating manual for coding agents (Codex, Claude Code, OpenCode). Deeper docs: `docs/handoff/ARCHITECTURE.md` (how it works) and `docs/handoff/STATUS.md` (what is verified, what is not, TODOs). Read STATUS.md before claiming anything works.

## What this is

`warrant` (PyPI name `warrant-research`, not yet published; v0.8.0; private repo `ItsShreyamHere/warrant`) is a Python **stdlib-only** package and agent plugin that keeps research with an AI agent honest, using plain code instead of a model:

- hooks record every tool output, then block a final reply once if it contains a number nothing produced, a p-value that does not follow from its test statistic, or a citation that does not resolve;
- `warrant review` is a referee report on a paper (arXiv id, DOI, LaTeX folder): reference existence, attributed numbers vs. cited full text, statcheck/GRIM, BM25 evidence cards, quote-verified verdicts;
- `warrant audit`, `stats`, `cites`, plus a claim/predict/result ledger with a graveyard of refuted ideas.

It ships as a plugin for Claude Code, Codex and OpenCode. Origin: replaces an older private project, ROS (`../ros-cli-v1`); only its falsify verdict logic and the ledger hash-chain idea were ported.

## Layout

```
warrant/            the package (cli.py entry; hooks.py, record.py, provenance.py, checks.py,
                    cites.py, audit.py, review.py, paper.py, stats.py, falsify.py, proofs.py,
                    report.py, dashboard.py)
bin/                warrant (CLI launcher), warrant-hook (hook launcher), warrant.py (no-install entry)
hooks/hooks.json    Claude Code / Codex hook wiring -> `bin/warrant-hook <session|prompt|post|stop>`
skills/warrant/     SKILL.md: the instructions the agent reads
integrations/opencode/  plugin/index.js (V1 server() + V2 setup()) and commands/*.md
scripts/install.sh  installs into OpenCode / Codex from a checkout
plugin.json, .claude-plugin/{plugin,marketplace}.json, .agents/plugins/marketplace.json  manifests
action.yml          GitHub Action (reference audit)
bench/              reproducible scans + RESULTS.md (bench/results/ is gitignored)
tests/test_warrant.py   all tests (44)
docs/               README assets; docs/handoff/ = this handoff
```

## Run

```bash
python -m pytest -q                      # from repo root; expect 44 passed, ~2 s, no network
python bin/warrant.py --help             # run the CLI from the checkout (or `pip install -e .` then `warrant`)
python bin/warrant.py stats paper.md     # offline
python bin/warrant.py audit 1706.03762   # network: doi.org, arXiv, OpenAlex, Crossref
python bin/warrant.py review 1706.03762  # network, ~1.5 min/paper
```

Env vars: `WARRANT_DIR` (record dir), `WARRANT_OFFLINE=1` (skip citation lookups), `WARRANT_STRICT=1` (also trace whole numbers >= 10), `WARRANT_CACHE` (review paper cache, default `~/.warrant/cache`), `WARRANT_ROOT` (OpenCode plugin checkout path).

Hooks are silent no-ops in any project without a `.warrant/` folder. Test hooks with `python bin/warrant.py hook stop < payload.json` inside a dir where `warrant init` was run.

## Conventions (do not break)

1. **Stdlib only.** No runtime dependencies. `pytest` is the only dev dependency. Python >= 3.10.
2. **Precision over recall.** Never flag something as fake, wrong or inconsistent unless certain. A false accusation is worse than a miss. Parser doubt means skip (see `statcheck`: `p > 1` as parsed is skipped; `audit`: a dead identifier alone is never "red").
3. **Unreachable network = "unchecked" (yellow), never "red".** Never cache a yellow result.
4. **Hooks must never break a session.** `hooks.run` catches every exception and exits 0; launchers exit 0 if Python is missing; Stop blocks at most once (`stop_hook_active`); Stop always prints `{}` when not blocking (Codex needs JSON).
5. **Code decides, models don't.** Verdicts, traces, p-values come from code. A model may only judge evidence cards, and every verdict needs a quote that code finds verbatim.
6. **Every new check needs a regression test** in `tests/test_warrant.py`, ideally from the real false positive that motivated it. Parser fixes get a test with the exact offending string.
7. The record is append-only and hash-chained; never UPDATE/DELETE events. New event kinds go in `record.KINDS`.
8. Hook payloads differ per agent (Claude transcript vs. Codex/OpenCode `last_assistant_message`; tool names `Write` vs. `apply_patch` vs. `write`). Extend `hooks._WRITERS` / handlers rather than forking.
9. Keep LF line endings (`.gitattributes`); the `bin/` launchers are POSIX sh.
10. Do not publish paper identifiers from benchmark runs; inconsistencies are usually typos. `bench/results/` stays untracked.

## Release

1. Bump the version in **all five**, they must match: `pyproject.toml`, `warrant/__init__.py`, `plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.
2. `python -m pytest -q` passes. Commit, tag `vX.Y.Z`, push.
3. PyPI (never done yet): `python -m build && twine upload dist/*`.
4. **Before making the repo public**: history contains `bench/results/scan-v0-buggy.jsonl` (an early scan with false findings naming papers). Rewrite history or recreate the repo first. See STATUS.md.

## Update installed plugins (after pushing)

```bash
# Claude Code
claude plugin marketplace update warrant && claude plugin update warrant@warrant
# Codex (plugins feature may be off in the user's config, so pass --enable plugins)
codex plugin marketplace add ./ --enable plugins && codex plugin add warrant@warrant --enable plugins
# OpenCode (copies skill, commands, plugin/warrant.js into ~/.config/opencode)
./scripts/install.sh --opencode
```

Codex hooks need one-time trust via `/hooks` in Codex. **Do not run `opencode plugin list`**: on OpenCode 1.18 it installs an npm package named "list".

## Pointers

- Architecture, data flow, math, every command: `docs/handoff/ARCHITECTURE.md`
- Verified vs. unverified, risks, ranked TODOs: `docs/handoff/STATUS.md`
- Benchmark numbers and how to reproduce: `bench/RESULTS.md`
- User-facing docs: `README.md`; agent instructions: `skills/warrant/SKILL.md`


## warrant watch (added v0.9.0)

`warrant/watch.py`: `Watch` tails files/folders/globs (log, txt, csv, jsonl, out) from stored offsets, only complete lines. Sentinels in `check_chunk` / `check_series` / `check_overfit` / `check_predicates`; alerts dedupe by id `sentinel:file:key` and are appended to `.warrant/alerts.jsonl`. `pending()` hands undelivered alerts to the prompt/session hooks (`hooks.watch_lines`), one ~40-token `card_text` line each, delivered once. `--wake` runs a command with the card on stdin, for red alerts only, under `--max-wakes`/hour. Watched chunks are `rec.observe`d, so they count as evidence for number tracing. Tests: `test_watch_*`. Known shortcut: `pending()` rewrites alerts.jsonl while a watcher may append (a rare lost update is possible; switch to SQLite if this matters).
