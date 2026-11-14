# Reddit

**Before each post:** read the subreddit's sidebar rules that day. Rules change, and several subreddits limit self-promotion: some allow it only on certain days or in a megathread. Space posts at least a day apart; posting the same thing in many subreddits on the same day gets flagged as spam. Reply to every comment.

**Attach:** a GIF where images are allowed (`launch/video/warrant-demo-hq.gif`, or `launch/assets/review.gif` / `watch.gif`). Otherwise post text and include the link.

---

## r/MachineLearning: lead with the engineering

**Rules to check:** title must start with `[P]` (project). It's a research subreddit, so keep the post technical, with no marketing tone.

**Title:**
```
[P] warrant: code-verified citations, statistics and live-run checks for AI research agents (statcheck re-implemented in stdlib Python)
```

**Body:**
```
AI research agents report numbers no run produced, cite DOIs that don't exist, and call one seed "significant". warrant checks their output with code instead of another model.

**What it does**
- Hooks for Claude Code / Codex / OpenCode: every decimal in the agent's reply must trace to a captured command output (within rounding, a mean of logged values, or a difference of traced numbers). Failing replies are sent back once with the list.
- `warrant review <arXiv id>`: reads the cited papers' full text. Numbers attributed to a cited paper must exist in it. For "does this passage support this claim", it retrieves the 2 best passages per citing sentence (BM25) so the model reads short cards (13x less text than the cited papers on arXiv:1706.03762), and every verdict must quote the source verbatim or code rejects it.
- `warrant watch runs/`: zero-token sentinels on training logs: NaN/inf, loss divergence, overfitting (val loss up while train loss down), held-out scores >= 0.999 (leakage), crashes/OOM, stalled runs, pre-registered predictions refuted mid-run. The agent gets one ~40-token line per alert.
- statcheck (t, F, χ², r, z) with rounding-aware ranges, and GRIM.

**Benchmark (honest version)**
- 851 open-access psychology papers (Europe PMC): 2,063 p-values recomputed. 6 papers have a significance decision contradicted by their own test statistic (hand-verified; not naming them, likely typos).
- 366 recent arXiv papers: 0 errors. The first pass flagged 20, and all 20 were my scanner's false positives (sci-notation and Bonferroni-adjusted p-values). Fixed, with regression tests.

Stdlib only, MIT: https://github.com/ItsShreyamHere/warrant

Most interested in false positives and in checks you'd want added.
```

---

## r/ClaudeAI: lead with the plugin

**Rules to check:** use the Showcase / "Built with Claude" flair if required.

**Title:**
```
I built a plugin that stops Claude from reporting numbers no command produced, and checks every citation it makes
```

**Body:**
```
If you use Claude Code for research or data work, you've probably seen it confidently report a metric it never computed.

warrant is a plugin (also works in Codex and OpenCode) that adds code checks to Claude's replies:
- every number must trace to a command Claude actually ran, or the reply comes back with the list
- DOIs / arXiv ids / paper titles are resolved live
- reported p-values are recomputed
- `warrant watch runs/` watches your training logs with plain code (0 tokens) and only pings Claude when something breaks: NaN, divergence, overfitting, crashes

Install:
/plugin marketplace add ItsShreyamHere/warrant
/plugin install warrant@warrant
then `warrant init "your research question"` in the project.

https://github.com/ItsShreyamHere/warrant. It's free, and I'd love bug reports on false alarms.
```

---

## r/PhD and r/academia: lead with "check before you submit or review"

**Rules to check:** both are strict about promotion. If the rules forbid it, skip, or ask the mods first. Use no AI-agent framing here.

**Title:**
```
Free tool: recompute every p-value in a paper and check its references before you submit (or review)
```

**Body:**
```
I made a free, open-source command-line tool that catches two boring but embarrassing classes of error:

1. **Statistics that don't add up.** It recomputes each p-value from the reported test statistic (t, F, χ², r, z), like statcheck, and checks means for impossibility (GRIM). When I ran it on 851 open-access psychology papers, 6 had a "significant" result their own numbers contradict, e.g. t(1350) = 0.150 reported as p = .04 (actually .88). Almost certainly typos, but that's the point.
2. **References that don't exist or don't say what you cite them for.** It checks every reference against doi.org, arXiv, OpenAlex and Crossref, and for arXiv papers it checks that numbers you attribute to a paper are actually in it.

`warrant stats draft.md`, `warrant audit refs.bib`, `warrant review <arXiv id>`.

https://github.com/ItsShreyamHere/warrant. It's MIT-licensed and needs no account.
```

---

## r/AcademicPsychology and r/statistics: lead with statcheck

**Title:**
```
I re-implemented statcheck (plus GRIM) in dependency-free Python and recomputed 2,063 p-values from 851 open-access papers
```

**Body:**
```
statcheck is great but lives in R. I needed it in a pipeline, so I wrote the p-value recomputation from scratch: regularized incomplete beta/gamma, rounding-aware ranges for the reported statistic, and the usual false-positive guards. Adjusted p-values are recognised when the paper states a correction, and one-tailed tests when the paper says so.

Run on 851 open-access psychology papers from Europe PMC: 215 report APA-style tests, 2,063 tests recomputed, 74 recognised as adjusted. 6 papers have a significance decision their own statistic contradicts (hand-checked; anonymised in the repo since these are likely typos). Examples: t(1350) = 0.150, p = .04 (actually .88); F(3, 196) = 2.566, p = .046 (actually .056).

Method + reproducible script: https://github.com/ItsShreyamHere/warrant (bench/RESULTS.md, bench/scan_pmc.py)

Very interested in cases where it misreads a reporting style.
```

---

## r/Python: lead with "no dependencies"

**Rules to check:** r/Python usually keeps project showcases to a weekly thread or a specific day, so check before posting.

**Title:**
```
warrant: stdlib-only Python that recomputes p-values (incomplete beta/gamma from scratch), checks citations and watches training logs
```

**Body:** the r/MachineLearning body, opening with the "zero dependencies" angle.

---

## Codex and OpenCode communities

r/ChatGPTCoding, r/OpenAI, and OpenCode's GitHub Discussions or Discord. **Title:** `Plugin for Codex/OpenCode: your agent can't report numbers no command produced`. **Body:** the r/ClaudeAI body, with these installs swapped in:
- Codex: `codex plugin marketplace add ItsShreyamHere/warrant --enable plugins`
- OpenCode: `./scripts/install.sh --opencode`
