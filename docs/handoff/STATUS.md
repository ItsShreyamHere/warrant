# Status (v0.8.0, 2026-11-12)

`python -m pytest -q`: **44 passed** (offline; network paths are mocked).

## Works and was verified

- **Live Claude Code headless run**: the Stop hook blocked a from-memory number; Claude then re-sent it marked with `~`. The run exposed two bugs, both fixed: a backtick glued to a DOI, and arXiv DOIs (10.48550) being DataCite-registered (existence is now checked via the doi.org handle API, not Crossref).
- **`warrant audit`** on real papers: ResNet (50 refs) and Transformer (40 refs) with 0 false flags; AlphaFold Nature DOI: 84 refs, 75 verified, 0 flagged, 41 s; planted fake references were caught. The precision rules came from an early scan where 3/3 flags were parser bugs (LaTeX-wrapped DOI, page numbers read as arXiv ids, ACL `.bbl` titles).
- **`warrant review`** on arXiv 1706.03762: 9 evidence cards = 2,224 words vs 28,916 words of cited full text (13x less). Quote verification accepted 3 real quotes and rejected 1 invented one.
- **statcheck benchmark** (`bench/RESULTS.md`): 851 Europe PMC psychology papers, 215 with tests, 2,063 tests, 74 recognised as adjusted; 6 hand-verified papers whose stats contradict a significance decision (2.8% of papers with tests). arXiv scan: 366 papers, 22 with tests, 91 tests, 0 inconsistencies after fixing scientific-notation and Bonferroni false positives (both have regression tests).
- **Codex**: `codex plugin add` installed the plugin from the repo (needs `--enable plugins`; the user's Codex has plugins off). The installed hook command, fed Codex-style stdin, blocks an invented number + fake DOI and emits `{}` otherwise.
- **OpenCode 1.18.32**: plugin installed at `~/.config/opencode/plugin/warrant.js`; loaded in Node and exercised against a mock client (passes a traced number, blocks an invented one).

## NOT verified

- Codex in a live session (needs `/hooks` trust; whether Codex expands `${CLAUDE_PLUGIN_ROOT}` in `hooks/hooks.json` is unconfirmed live).
- OpenCode in a live session. The V2 `setup()` path has never run against OpenCode 2; `lastAssistantText` guesses several message shapes.
- The GitHub Action has never run on GitHub. There is no `.github/` directory, so the repo has no CI of its own either.
- Lean proof checking (Lean not installed). The `.py` assert path is tested.
- GRIM on real papers (not in the benchmarks). The PMC 2.8% figure counts only the 6 hand-checked decision flips.
- macOS/Linux: `bin/` launchers are POSIX sh but were only exercised on Windows.

## Known limitations and risks

- **Repo is private and not on PyPI.** `bench/results/scan-v0-buggy.jsonl` (an early scan whose flags were parser bugs, naming papers falsely) is in git history though now untracked. Rewrite history or recreate the repo before going public.
- README demo GIF and hero image show the older number-tracing feature, not `review`.
- Drift detection only parses Claude Code transcripts; it is a silent no-op on Codex/OpenCode.
- `review` reads full text only for arXiv-hosted cited papers (LaTeX source); others get no cards and no attributed-number check. About 1.5 min per paper because of arXiv/OpenAlex rate limits.
- Whole numbers are not traced unless `WARRANT_STRICT=1`; "15 seeds" or invented counts are not blocked by default.
- Number tracing is permissive by design (tolerance windows, means of consecutive values, derived differences/ratios): an invented number can match by accident, and a real number misattributed in prose is not caught.
- The Stop-hook citation policy is stricter than `audit`: a non-existent DOI in the agent's own reply is red (blocks), whereas `audit` never flags a dead identifier alone. Intentional (agent text vs. parsed bibliography), but easy to trip over.
- statcheck: regex APA extraction only; PDFs and tables are out of scope; one-tailed handling only when the paper says so; GRIM assumes integer data.
- Public APIs throttle; `_get` retries with backoff and failures become yellow. Stop hook timeout is 60 s (`hooks/hooks.json`); up to 12 lookups with retries could approach it on a bad network.
- Code smells: `stats.statcheck` has a dead expression `(p_rep == alpha and False)` in `rep_sig`; `cites.UA` still says `warrant/0.1`.

## Open TODOs, ranked by value

1. Clean git history (drop `scan-v0-buggy.jsonl`), then make the repo public.
2. Live-test Codex (trust hooks, confirm path variable expansion, Stop JSON) and OpenCode (V1 and V2); fix adapter shapes.
3. Re-record the demo GIF/hero around `review` and lead the README with it.
4. Publish to PyPI as `warrant-research`.
5. Add `.github/workflows` running pytest; run the Action on a real repo once.
6. Extend `review` full-text coverage beyond arXiv (Europe PMC / PMC OA XML, publisher OA); reduce latency with caching.
7. Drift detection for Codex/OpenCode (store reply history in the record instead of parsing transcripts).
8. Install Lean and test proof receipts; add a regression fixture.
9. Run GRIM and `review` at benchmark scale and hand-verify, as was done for statcheck.
10. Cleanup: dead `rep_sig` expression, stale User-Agent string.
