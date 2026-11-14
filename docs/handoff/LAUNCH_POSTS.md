# Launch posts: final copy (v0.9.0)

Every claim below is measured and in the repo (README, bench/RESULTS.md). Don't post any text that isn't approved here. Never name the flagged papers.

---

## 1. Hacker News: Show HN

**Title** (80 chars max):
`Show HN: Warrant – a referee that reads every paper your AI agent cites`

**URL:** https://github.com/ItsShreyamHere/warrant

**First comment** (post immediately):

> Hi HN. I built warrant because AI research agents are fluent liars about numbers. They report accuracies no run produced, cite DOIs that don't exist, and write "significantly better" on one seed.
>
> warrant puts plain code, not a second model, between the agent and you:
>
> - **Live checks** (Claude Code, Codex, OpenCode hooks). Every decimal in the agent's reply must trace to a command that actually ran: exact within rounding, a mean of logged values, or a difference of traced numbers. Citations are resolved against doi.org, arXiv, OpenAlex and Crossref, and reported p-values are recomputed. A failing reply is sent back once, with the exact list.
> - **`warrant review <paper>`**. It reads the cited papers' full text and checks that numbers attributed to a source exist in it. For judgment calls it hands the model short evidence cards: 13× less text than the cited papers on the Transformer paper. Every verdict must quote the source verbatim, and code rejects quotes that aren't there.
> - **`warrant watch runs/`**. Zero-token sentinels on live training logs: NaN, divergence, overfitting, near-perfect held-out scores (leakage), crashes, dead runs. A model only hears about it when something breaks, as one ~40-token line.
>
> I recomputed 2,063 p-values from 851 open-access psychology papers with a from-scratch statcheck (incomplete beta/gamma in stdlib Python). In 6 papers, the paper's own test statistic contradicts its significance claim, e.g. t(1350) = 0.150 reported as p = .04 (it's .88). I hand-checked every one and won't name them: most are probably typos. I also ran it on 366 recent arXiv papers and found 0 errors, after fixing the scanner's own false positives (scientific-notation p-values, Bonferroni-adjusted ones). Precision over recall is the core rule.
>
> Zero dependencies, MIT. Happy to hear where it misfires; false positives are the bugs I care most about.

---

## 2. X / Twitter thread

1/ AI research agents will happily report an accuracy no experiment produced, cite a DOI that doesn't exist, and call one seed "significant".

I built warrant: a referee that checks every number and citation against the source. With code, not another model. 🧵

[review.gif]

2/ In Claude Code, Codex or OpenCode, every decimal in the agent's reply must trace to a command that actually ran. Invent a number → the reply comes back with the exact list.

[demo.gif]

3/ `warrant review <paper>` reads the papers you cite. Numbers attributed to a source must exist in that source. The model judges short evidence cards (13× less reading), and every verdict must quote the paper verbatim, or code rejects it.

4/ I recomputed 2,063 p-values across 851 open-access psychology papers. In 6, the paper's own statistics contradict its conclusion.

t(1350) = 0.150 → reported p = .04. Actual p = .88.

Hand-verified, anonymised. Most are likely typos.

5/ New: `warrant watch runs/`. Zero-token sentinels on live training logs: NaN, divergence, overfitting, leakage, crashes, dead runs. Your agent only hears about it when something breaks.

[watch.gif]

6/ Stdlib Python, MIT, works with Claude Code, Codex and OpenCode.

github.com/ItsShreyamHere/warrant

---

## 3. Reddit

**r/MachineLearning** (title must start with `[P]`; link post or text post per the current rules, check the sidebar first):

`[P] warrant: code-verified citations, statistics and live-run checks for AI research agents (statcheck re-implemented, 2,063 p-values recomputed)`

Body: the HN first comment, minus the "Hi HN" line.

**r/ClaudeAI** (Showcase flair): `I built a plugin that blocks Claude from reporting numbers no command produced, and checks every citation it makes`. Body: X thread posts 1–3 and 5, plus the install command `/plugin marketplace add ItsShreyamHere/warrant`.

**r/PhD / r/academia** (only if the subreddit allows tools; lead with the reviewer use case): `Free tool: check a paper's references and recompute its p-values before you submit (or review)`. Body: `warrant review` / `warrant stats` / `warrant audit` with one example each; no AI-agent framing.

---

## 4. Bluesky / Mastodon (science)

> Recomputed 2,063 p-values from 851 open-access psychology papers with a from-scratch statcheck. 6 papers' own test statistics contradict their significance claims (e.g. t(1350)=0.150 reported p=.04; it's .88). Hand-verified, anonymised. The tool is open source and also checks citations against the cited papers: github.com/ItsShreyamHere/warrant

---

## 5. Awesome-lists / directories (PRs from the owner's GitHub)

One line, adapted to each list's format:

`- [warrant](https://github.com/ItsShreyamHere/warrant) - Code-verified research for agents: numbers must trace to real runs, citations resolved and quote-checked, p-values recomputed (statcheck), zero-token sentinels on live experiments.`

Targets: find the current top awesome-claude-code / awesome-agent-skills / awesome-codex / awesome-opencode lists on GitHub, sorted by stars. Read each list's CONTRIBUTING first.
