# Architecture

Python 3.10+, stdlib only, ~2,700 lines in `warrant/`. Everything flows through `warrant/cli.py` (argparse, one `cmd_*` per subcommand) or `warrant/hooks.py` (hook entry, via `warrant hook <name>`).

## Modules

| Module | Role |
|---|---|
| `cli.py` | All subcommands. Entry `main()`; `python -m warrant`, `bin/warrant.py`, console script `warrant`. |
| `hooks.py` | Four handlers (`session`, `prompt`, `post`, `stop`) in `HANDLERS`; `run()` reads JSON on stdin, prints hook JSON, swallows all errors. Also `final_reply()` (last assistant text from a Claude Code transcript), `anchor()`, `drift_note()`. |
| `record.py` | `Record`: append-only, hash-chained SQLite log (`.warrant/record.db`) + `obs/<seq>.txt` files + number index tables. `state()` folds events into question/claims/graveyard. `verify_chain()`. |
| `provenance.py` | Number extraction from prose (`extract`, `scrub`), source-number extraction, tolerance windows, `trace_all` (exact / percent / mean / derived), `keyed_values` (`acc=0.81`), `window_means`. |
| `checks.py` | `evaluate(claim)` -> green/yellow/red with reasons; wording rules; `trace_text` / `untraced_numbers` (used by the Stop hook); `graveyard_match`; `judge` (wraps `falsify`). |
| `falsify.py` | Pre-registered refutation predicates: ops lt/le/gt/ge/eq/ne, `of` baseline/absolute, margin, `any`/`all` mode; returns supported / refuted / inconclusive (missing metric = inconclusive). Ported from ROS. |
| `cites.py` | Citation lookup: `resolve_doi`, `resolve_arxiv`, `search_title`, `check_text` (draft text), `check_bib`, `check_quote`, `clean_doi`, `title_similarity`, on-disk cache `.warrant/cites.json`. `_get` retries 429/5xx with backoff. `WARRANT_OFFLINE=1` disables. Max 12 lookups per text. |
| `audit.py` | Reference-list audit: parse `.bib`/`.bbl`/arXiv LaTeX source (`fetch_arxiv_source`, in memory) or a DOI's reference list (`refs_from_doi`, Crossref); `check_ref`, `audit` (4 threads). |
| `review.py` | The referee pipeline (`run`, `verify`, `markdown`); cited-paper cache under `~/.warrant/cache/papers`. |
| `paper.py` | LaTeX to text, cite-key marking, sentence split, BM25 passage retrieval (`best_passages`), verbatim quote test (`quote_in`). |
| `stats.py` | Special functions, p-values, `statcheck`, `grim`. |
| `proofs.py` | `check_proof`: `.lean` (Lean 4 / `lake env lean`; `sorry`/`admit` = red) or `.py` with `assert`s. No checker installed = yellow. |
| `report.py` | Markdown/HTML report, annotated draft view (`draft_html`), SVG badge (`badge_svg`). |
| `dashboard.py` | Local `http.server` page refreshing every 3 s. |

## Data flow (hooks)

```
SessionStart      -> anchor (question, hypothesis, claim counts, graveyard) injected as context
UserPromptSubmit  -> prompt text stored as observation "user" (its numbers are legitimate sources);
                     anchor + drift note injected as context
PostToolUse (*)   -> tool input+output flattened to text -> Record.observe():
                       event(kind=observe, sha256) + obs/<seq>.txt (<= 2 MB)
                       tables obs_nums(value,obs), obs_keys(key,value,obs), obs_means(label,value,obs)
                     File-writing tools (Write/Edit/MultiEdit/NotebookEdit/apply_patch/write/edit/patch)
                       only log a "wrote" event with the path: text the agent wrote is NOT evidence;
                       reading a written file back indexes integers only.
Stop              -> reply = last_assistant_message (Codex/OpenCode) or transcript tail (Claude Code)
                     three checks; any problem => {"decision":"block","reason":...} once
                     (stop_hook_active => never block again). No problem => prints {}.
```

Stop checks, all code-only:
1. **Number provenance** (`checks.untraced_numbers`): each reported number must match a number in the record (question, metrics, logs, predicates), an observation (`obs_nums`, within rounding tolerance, also as percent/fraction), a mean (`obs_keys` per observation and across runs; `window_means` of consecutive values), or be derived (difference/ratio/relative change of two already-traced numbers in the same reply). Ignored: code blocks, dates, versions, section numbers, `~`/approx/estimated numbers, labelled ids. Whole numbers are ignored unless `WARRANT_STRICT=1` (then >= 10 and not a year).
2. **Statcheck** on the reply: inconsistent p-values.
3. **Citations** (`cites.check_text`): DOI / arXiv ids looked up; a quoted title near the id must match (similarity >= 0.6) else red; quoted titles with a cue (year or "et al.") searched in OpenAlex. Only `red` blocks.

GRIM is not run in the Stop hook (CLI and `review` only).

Drift (`drift_note`, in the prompt hook): after 3 consecutive substantive (>= 300 chars) replies sharing no topic word with the question/hypothesis/claims, it warns once and resets. State in `.warrant/drift.json`. It parses Claude Code transcripts only (`transcript_path`), so on Codex/OpenCode it does nothing.

### Record schema

`events(seq, ts, kind, body JSON, prev, hash)`; `hash = sha256(prev \n kind \n body)`. Kinds: `question claim evidence predict result kill retract observe wrote`. Claims are numbered 1..n by order. `verify_chain()` checks the chain and each `obs/<seq>.txt` against its stored sha. Index tables are derived data. Claim status = `checks.evaluate` over folded state.

## `review` pipeline

`review.run(files)`:
1. `paper.parse_tex`: per `.tex` file keep text from `\begin{document}` to the bibliography; extract abstract; replace `\cite*{...}` with markers; `tex_to_text`; split sentences. Sentences with cite keys become `(sentence, [keys])`.
2. Code checks: abstract numbers absent from the body (yellow); "significant" without p/CI/+- nearby in own-result sentences containing numbers (yellow); `stat_findings` = statcheck (red if decision flips at .05, else yellow) + GRIM (yellow); reference existence via `audit` (red = found nowhere).
3. Sources: cited keys ranked by citation count; top `--max-sources`*2 tried. arXiv id from the bib entry, else `find_arxiv` (OpenAlex by DOI or title, similarity >= 0.85). Full text only for arXiv-hosted papers: `source_text` fetches LaTeX source, parses, caches `{abstract, body}` (needs body >= 500 chars). 4 threads.
4. Attributed numbers: a citing sentence with exactly one source, numbers, and no "we/our/this paper" -> each number must appear in that source's text, else red.
5. Evidence cards: skip tool/dataset credits (`_TOOL_CREDIT`) and citation lists (> 2 keys); rank by `claim_strength` (numbers + claim words); for each, the 2 best ~110-word passages by BM25 (`paper.best_passages`: 110-word windows, step 70, near-duplicates dropped). Capped at `--max-cards`.
6. Output `warrant-review/<paper>/report.md` + `cards.json`. A model writes `verdicts.json` items `{"card","verdict","quote"}` (`supports|partial|contradicts|not_found`); `review --verify` accepts a verdict only if `paper.quote_in` finds the quote verbatim (case/punctuation/spacing normalised, >= 15 chars) in the cited paper's cached text. `not_found` needs no quote. Exit 1 if any rejected.

## stats.py math

- `betainc`: regularised incomplete beta via Lentz continued fraction (`_betacf`). `gammaincc`: series for x < s+1, continued fraction otherwise. `p_t`, `p_f`, `p_chi2`, `p_z` (erfc), `p_r` (via t). All two-tailed. Checked against reference values in `test_stats_math_matches_reference_values`.
- Extraction: `t(df)=`, `F(d1,d2)=`, chi-square (`χ²`, `chi2`, optional `N=`), `r(df)=`, `z=`, each followed by `p <,=,>,≤,≥ value`, including scientific notation (`4.7 × 10^-5`, `4.7e-5`). Unicode minus accepted.
- **Rounding range** (`_p_range`): the statistic is only known to its printed precision, so p is computed at stat +- half a unit of its last decimal. The reported p is consistent if it (+- half a unit of its last decimal) overlaps that range. `<`, `≤`, `>` compare against the range ends.
- **Adjusted p**: if the text mentions Bonferroni/Holm/Sidak/Benjamini-Hochberg/FDR/Tukey/"adjusted p"/multiple comparisons and the reported p is above the raw range, it is accepted (`adjusted`).
- **One-tailed**: if the text says one-tailed/one-sided/directional and the test is t/z/r, p/2 is also accepted (`one_tailed`).
- `gross` = inconsistent AND reported and recomputed p fall on opposite sides of alpha (.05): "decision flips". Duplicate strings collapsed. Skipped: `p > 1` as parsed, `|r| > 1`.
- **GRIM**: a mean `M = x.xx` with `n = N` (optional `SD=` between) is impossible if no integer total / n rounds to it; checked only when n < 10^decimals. Meaningful only for integer-valued data; reported yellow with that caveat.

## audit.py

- Input: arXiv id/URL (LaTeX source tarball read in memory, 50 MB cap), DOI/doi.org URL (reference list from Crossref via `refs_from_doi`), or local `.bib`/`.bbl`/`.tex`/`.md`.
- Parsing: `parse_bbl` / `parse_bib`; `_ids` joins `%` line continuations and wrapped DOIs (keeps the longest candidate) and accepts only explicit `arXiv:`/`arxiv.org/abs`/`\eprint` ids (a bare `NNNN.NNNNN` matches page numbers); ACL-style titles via `_title_without_newblock`; LaTeX stripped by `_latex_to_text`.
- `check_ref`: DOI -> `resolve_doi` (existence via `https://doi.org/api/handles/<doi>`, which covers Crossref and DataCite incl. arXiv DOIs 10.48550; title/abstract from Crossref, else DataCite); arXiv id -> arXiv API. Any green = verified. An unreachable registry falls through to title search. A dead identifier alone is never red (usually a typo or wrapped DOI). Title search: OpenAlex (similarity >= 0.85 green), then Crossref `query.bibliographic`. **Red only when** OpenAlex similarity < 0.5, Crossref has no match, the title has >= 4 words, and the raw entry does not look like software/web/report/thesis/preprint/etc. Real title + dead id = yellow.
- Exit code 1 if any red. `--badge` writes an SVG; `--json`; `--all` also lists yellow.

## CLI commands

```
warrant init "<question>"                  # creates .warrant/, turns hooks on
warrant question "<q>" --hypothesis "<h>"
warrant claim "<text>"                     # prints claim #N; warns if it resembles a graveyard idea
warrant predict N '{"metric":"acc","op":"le","of":"baseline","margin":0.0}' [--mode any|all]
warrant result N --observed acc=0.812 --baseline acc=0.809   # code decides; refuted -> graveyard
warrant evidence N --type run --log runs.log --metric acc=0.812 --seeds 3 --std 0.006 --p 0.03
warrant evidence N --type proof --ref thm.lean               # or a .py with asserts
warrant evidence N --type cite --ref 10.48550/arXiv.1706.03762 [--quote "..."]   # also data, note
warrant kill "<idea>" --why "..."          # bury manually
warrant retract N --why "..."
warrant status [--json]
warrant report [-o out.html] [--html] [--draft draft.md]     # --draft: every number marked traced/untraced
warrant trace draft.md [--all]             # untraced numbers in a draft
warrant cites draft.md | refs.bib          # exit 1 if any red
warrant audit <arXiv id|DOI|URL|file> [--all] [--badge b.svg] [--json]
warrant review <arXiv id|DOI|URL|folder|.tex> [--max-sources 25] [--max-cards 40] [--no-refs] [-o dir]
warrant review --verify verdicts.json [--cards cards.json]
warrant stats paper.md|.tex                # statcheck + GRIM, exit 1 on any problem
warrant dashboard [--port 8765] [--no-browser]
warrant hook <session|prompt|post|stop>    # internal, JSON on stdin
```

Claim wording rules (`checks.evaluate`): "significant" needs >= 3 seeds and p < .05 (else red); "proves" needs a green proof receipt (else red); win words ("outperforms", "improves") with a green run but < 3 seeds and no result are red; absolute words add a note; hedged wording on strong evidence adds a "possibly understated" note. Run evidence is re-hashed, so an edited log goes red. Predictions must precede results.

## Agent integrations

| | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Install | `/plugin marketplace add ItsShreyamHere/warrant` (`.claude-plugin/marketplace.json`) | `codex plugin marketplace add` + `codex plugin add warrant@warrant --enable plugins` (`.agents/plugins/marketplace.json`, root `plugin.json`) | `scripts/install.sh --opencode` -> `~/.config/opencode/{skills,commands,plugin/warrant.js}` |
| Hooks | `hooks/hooks.json` (`${CLAUDE_PLUGIN_ROOT}/bin/warrant-hook <name>`) | same file; user must trust it in `/hooks` | `integrations/opencode/plugin/index.js` spawns `python bin/warrant.py hook <name>` |
| Session start | `session` | `session` | none; the anchor from the prompt hook is injected via `experimental.chat.system.transform` (V1) / `session.instructions.entry.put` (V2) |
| Prompt | `prompt` | `prompt` | `chat.message` (V1) / `session.hook("prompt")` (V2) -> `prompt` |
| Tool output | `post` (matcher `*`) | `post` | `tool.execute.after` -> `post` (V1 stashes args from `tool.execute.before`) |
| Stop | `stop`, reply from `transcript_path` | `stop`, reply from `last_assistant_message` | `session.idle` / `experimental.idle` -> fetch last assistant text -> `stop`; on `block`, sends `reason` as a follow-up prompt, at most once per turn (`nudged` set; prompts starting `[warrant]` are ignored as evidence) |
| Skill | `skills/warrant/SKILL.md` | same | copied to `skills/warrant` |
| Commands | via skill | via skill | `/warrant-init`, `-audit`, `-review`, `-stats` (`integrations/opencode/commands/`) |

The OpenCode plugin is one file exporting `server()` (V1, OpenCode 1.18.29+) and a default `{id, server, setup}` (V2). `install.sh` bakes the checkout's absolute path in place of `"__WARRANT_ROOT__"` (Git Bash `/c/...` becomes `C:/...`). It tries `python`, `py`, `python3` on Windows and does nothing if none exists.

## Other

- `action.yml`: composite GitHub Action; runs `bin/warrant.py audit <file> --all [--badge]` per file, writes a job summary, fails on any red unless `fail-on-flag: "false"`.
- `bench/`: `scan_arxiv.py` (reference scan), `scan_stats.py` (arXiv statcheck), `scan_pmc.py` (Europe PMC XML statcheck). Outputs go to gitignored `bench/results/`; summary in `bench/RESULTS.md`.


## warrant watch (added v0.9.0)

`warrant/watch.py`: `Watch` tails files/folders/globs (log, txt, csv, jsonl, out) from stored offsets, only complete lines. Sentinels in `check_chunk` / `check_series` / `check_overfit` / `check_predicates`; alerts dedupe by id `sentinel:file:key` and are appended to `.warrant/alerts.jsonl`. `pending()` hands undelivered alerts to the prompt/session hooks (`hooks.watch_lines`), one ~40-token `card_text` line each, delivered once. `--wake` runs a command with the card on stdin, for red alerts only, under `--max-wakes`/hour. Watched chunks are `rec.observe`d, so they count as evidence for number tracing. Tests: `test_watch_*`. Known shortcut: `pending()` rewrites alerts.jsonl while a watcher may append (a rare lost update is possible; switch to SQLite if this matters).
