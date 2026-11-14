# Show HN

**Submit at:** https://news.ycombinator.com/submit, logged in.
**When:** Tuesday to Thursday, 8–10 am US Eastern. Stay at the keyboard for 3 hours after posting to answer comments.
**Rules:** Show HN is for things people can try. Don't ask anyone to upvote, and don't share the direct link and ask for votes (HN penalises voting rings). Friends can comment if they have something real to say.

---

**Title** (≤ 80 characters):

```
Show HN: Warrant – a referee that reads every paper your AI agent cites
```

Alternatives:
- `Show HN: Warrant – your AI agent can't report numbers no experiment produced`
- `Show HN: I re-implemented statcheck and recomputed 2,063 p-values from 851 papers`

**URL:** `https://github.com/ItsShreyamHere/warrant`

**First comment** (post it yourself, right after submitting):

```
Hi HN. I built warrant because AI research agents are fluent liars about numbers: they report accuracies no run produced, cite DOIs that don't exist, and write "significantly better" on one seed.

warrant puts plain code, not a second model, between the agent and you:

- Live checks (Claude Code, Codex, OpenCode hooks): every decimal in the agent's reply must trace to a command that actually ran (exact within rounding, a mean of logged values, or a difference of traced numbers). Citations are resolved against doi.org, arXiv, OpenAlex and Crossref; reported p-values are recomputed. A failing reply is sent back once with the exact list.

- `warrant review <paper>`: reads the cited papers' full text, checks that numbers attributed to a source exist in it, and hands the model short evidence cards for the judgment calls (13x less text than the cited papers on the Transformer paper). Every verdict must quote the source verbatim; code rejects quotes that aren't there.

- `warrant watch runs/`: zero-token sentinels on live training logs (NaN, divergence, overfitting, near-perfect held-out scores, crashes, dead runs). A model only hears about it when something breaks, as one ~40-token line.

I recomputed 2,063 p-values from 851 open-access psychology papers with a from-scratch statcheck (incomplete beta/gamma in stdlib Python). In 6 papers the paper's own test statistic contradicts its significance claim, e.g. t(1350) = 0.150 reported as p = .04 (it's .88). I hand-checked every one and won't name them; most are probably typos. On 366 recent arXiv papers it found 0 errors, after I fixed the scanner's own false positives (scientific-notation and Bonferroni-adjusted p-values). Precision over recall is the core rule.

Zero dependencies, MIT. I'd love to hear where it misfires; false positives are the bugs I care most about.
```

---

## Likely questions, with honest answers

- **"Isn't this just a citation checker?"** No. Existence is the easy part. warrant checks that the cited paper actually contains what's attributed to it: numbers by code, claims by quote-verified cards. It also traces the agent's own numbers to real runs and watches live experiments.
- **"Why not have another LLM check the first?"** It has the same failure mode. 2026 work on research agents found they game their own evaluations, and instructions don't reliably stop them. warrant's verdicts come from code; the model only judges short cards and must quote.
- **"Can an agent cheat with `echo 0.93`?"** It produces a 0.93, so it traces, but the command is in the audit trail. That makes warrant tamper-evident, not tamper-proof, and the README says so.
- **"Which papers had the errors?"** Not published, on purpose: they're likely typos, and naming them helps no one. The method and anonymised cases are in `bench/RESULTS.md`; the scan is reproducible with `bench/scan_pmc.py`.
- **"Token cost?"** The skill is about 100 tokens per session, and the hooks add 0. `watch` uses 0 tokens until something breaks. `review` cards are about 13× smaller than reading the cited papers.
- **"Only arXiv?"** Full-text reading of cited papers is arXiv only for now. Reference existence works for any DOI that has a Crossref reference list (most major publishers).
