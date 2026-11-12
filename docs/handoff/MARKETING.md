# warrant: launch marketing plan

For: the Codex agent and the human owner taking over. Date written: 2026-11-12.
Companion file: `STARS_1000.md` (day-by-day schedule). This file is the "what to say, where, and to whom."

Rules for everything below:
- No fake engagement: no bought stars, no sockpuppets, no asking friends to upvote on HN, no vote-swapping groups.
- Precision over hype. Every number in a post must come from `README.md` or `bench/RESULTS.md`. Do not round up, do not invent new stats.
- Never name or link a paper flagged by the benchmark. Inconsistencies are usually typos, not misconduct.
- Sources cited in this file were checked on 2026-11-12. Community rules change; re-read them before each post (links in the Sources section).

---

## 1. Positioning

**Category claim:** warrant is the referee, not another assistant. Code, not a model, checks research claims.

**Headline (already in README):** "The referee that reads every paper you cite."

**The one-sentence story:** AI research agents write fluent numbers and citations that nobody ran or published; warrant puts a plain-code check between the model and the reader, and where judgment is needed it forces the model to quote the source verbatim or be rejected.

**Why now (all from the owner's brief; verify wording before quoting):**
- Fabricated references in published papers are a live public concern.
- 2026 preprints (BAITBENCH; "Reward Hacking Challenges Oversight of Autonomous Research Agents") report research agents gaming evaluations. Cite them by title only, and only after re-reading them. The README's phrase "a large share of research tasks" is soft; before using it in a post, check the exact figure in the paper and quote that, or drop the phrase.
- A second model checking the first has the same failure mode. warrant removes the verdict from the model.

**What makes it different from the crowd of skill repos:**
- Measured, not vibes: 13x less reading (2,224 vs 28,916 words, arXiv:1706.03762), 84 refs / 75 verified / 0 false flags / 41 s on the AlphaFold Nature paper, 2,063 p-values over 851 papers.
- Honest about limits (README "Limits, stated plainly"). This is a feature to advertise: "we report our own false positives."
- Zero dependencies, stdlib Python, works in Claude Code, Codex and OpenCode.

**Do not claim:**
- "Detects fraud", "catches misconduct", "proves a paper is wrong." It flags inconsistencies; humans decide.
- "0 errors on arXiv" without the context: 366 recent papers, 22 with APA-style tests, 91 tests, 0 inconsistencies, after fixing 20 false positives that were parser artifacts. State this plainly; it shows the tool is conservative, and also that the arXiv sample was small.
- "6 papers have errors" without: 6 of 215 papers reporting tests (2.8%), hand-verified, significance decision contradicts own statistics, likely typos.
- Anything about star counts of competitors beyond the owner's brief without re-checking.

---

## 2. One-liners by audience

Use these as bios, subject lines, and the first sentence of any pitch.

| Audience | One-liner | Proof point to follow with |
|---|---|---|
| ML researchers | "Your agent's results table, checked: every number traced to a command that ran, every citation resolved live, every p-value recomputed." | Before/after table; hook block message from the README. |
| Psych / biomed | "statcheck-style recomputation of every p-value, plus GRIM, inside the AI tool you already write with." | 2,063 p-values, 851 papers, 6 decision-flipping inconsistencies (hand-verified). |
| PhD students | "Run it on your draft before your reviewer does: `warrant review draft.tex`." | `warrant audit` on a .bib: 84 refs in 41 s. "Free, local, MIT." |
| Reviewers / editors | "A first-pass referee checklist where every comment is labelled verified-by-code, quote-verified, or reviewer judgment." | The three labels; the rejected-invented-quote example (3 accepted, 1 rejected). |
| Journal / conference organisers | "Reference existence and statistics consistency as a CI step on submissions: `warrant audit refs.bib`, GitHub Action, status badge." | The Action snippet and badge. Offer a pilot, not a mandate. |
| AI-agent builders | "Hooks that make an agent's final reply fail closed: untraced numbers and unresolvable citations are sent back once with the reason." | The Stop-hook flowchart; "hooks add 0 tokens"; Claude Code / Codex / OpenCode parity table. |

Short tagline variants for A/B testing in post titles (pick one per channel, do not spam all):
1. "The referee that reads every paper you cite."
2. "Claude invented a number and a DOI. Code caught both."
3. "I recomputed 2,063 p-values from 851 open-access psychology papers."
4. "A citation checker that makes the AI quote its source or be rejected."

---

## 3. Core story and proof points

Narrative arc for long-form (blog post, video, HN comment):
1. **Problem.** An AI write-up says "accuracy improves to 0.874 (vs 0.809), consistent with Müller et al. (doi 10.48550/arXiv.1906.99999)". The number was never produced; the DOI does not exist. Both look fine.
2. **Insight.** Research agents grade their own homework. Another model checking the model has the same bias. So take the verdict away from models wherever arithmetic or lookup can decide.
3. **Mechanism.** Hooks capture every command output and file read; the final reply is checked; failing replies bounce once with the exact list. For papers: `warrant review` reads cited papers' full text; BM25 evidence cards cut reading ~13x; every model verdict must contain a quote that exists verbatim in the source or code rejects it.
4. **Proof.** Table below.
5. **Honesty.** Limits, false positives we fixed, what it can't do (echo 0.93 produces a 0.93; tamper-evident, not tamper-proof).
6. **Call to action.** `pip install warrant-research` (once published), run `warrant audit refs.bib` on your own paper.

Proof points (copy exactly; all from repo):

| Claim | Number | Source |
|---|---|---|
| Reading reduction | 2,224 vs 28,916 words (about 13x) on arXiv:1706.03762 | README |
| Quote verification | real run: 3 verdicts accepted, 1 invented quote rejected | README |
| Reference audit | AlphaFold Nature paper: 84 refs, 75 verified, 0 false flags, 41 s | README / owner brief |
| Statistics benchmark | 2,063 p-values recomputed, 851 open-access psychology papers (Europe PMC, 2026-11-11), 215 reporting APA-style tests | `bench/RESULTS.md` |
| Decision-flipping inconsistencies | 6 papers, 2.8% of papers reporting tests, hand-verified, anonymised | `bench/RESULTS.md` |
| Example | t(1350) = 0.150, p = .04 (recomputed .88) | `bench/RESULTS.md` |
| arXiv scan | 366 papers, 22 with APA-style tests, 91 tests, 0 inconsistencies after fixing 20 parser-artifact false positives | `bench/RESULTS.md` |
| Footprint | 0 dependencies; hooks add 0 tokens; skill about 100 tokens/session | README |

A subtlety for the benchmark: "2.8%" is 6 of 215 papers that report tests, not 6 of 851 and not 2.8% of tests. Always say "of papers reporting tests." Also, 74 tests were recognised as multiple-comparison-adjusted and not counted as errors; mention this when someone asks about false positives.

---

## 4. Assets to produce (in priority order)

Owner and agent should produce these before launch day. Each has an acceptance test.

1. **Social preview image (1280x640 PNG).** Use `docs/hero.svg` crop: green-highlighted numbers vs red untraced numbers, plus the headline. Acceptance: legible at 400 px wide, on both light and dark Twitter/Slack previews. Upload at GitHub repo Settings, Social preview.
2. **Demo GIF of `warrant review` (new; `docs/demo.gif` currently shows the live hook block, not review).** Script: `warrant review 1706.03762` runs, the report appears, the `--verify` step prints 3 OK and 1 XX rejected quote. Under 20 seconds, under 8 MB, 820 px wide, readable terminal font. Acceptance: someone with no context can say what happened after one viewing. Keep both GIFs: hook demo as the hero, review demo as second.
3. **Before/after card (static PNG).** The README table as a clean 1200x675 image. This is the most shareable single image: the invented 0.874 and the fake DOI vs the traced version.
4. **Benchmark chart/thread images.** (a) Funnel: 851 papers, 215 reporting tests, 2,063 p-values, 6 decision-flipping. (b) A single "typo-grade" example: t(1350)=0.150, p=.04 vs recomputed .88. No paper identifiers anywhere, including in image metadata, filenames, and screenshot browser tabs.
5. **Short video (60-90 s, vertical and horizontal cuts).** Screen recording with voiceover or captions: problem (10 s), hook blocks fake number and DOI (15 s), `warrant review` on a famous paper (25 s), benchmark line (10 s), install command (10 s). Captions burned in; most viewers watch muted.
6. **Docs site / GitHub Pages demo.** One static page: hero, install tabs, before/after, a sample `report.md` rendered from a real run, and a "paste a DOI, see the audit" static example output (pre-generated, not live, to avoid load). Acceptance: loads under 2 s on mobile.
7. **Sample report gallery.** Commit 3 real `warrant review` / `warrant audit` outputs on famous, widely-cited, correct papers (for example the Transformer paper and AlphaFold, both already used). Choose papers that come out clean or with trivial findings. Never publish a report on a paper with a real finding without the authors being contacted first.
8. **Launch blog post (1,200-1,800 words)** on the repo docs or a personal blog: "I recomputed 2,063 p-values so your AI doesn't have to," built from section 3. Used as the canonical link for newsletters and the HN first comment.
9. **Press kit folder** `docs/press/`: logo, hero, 3 screenshots, 100-word and 300-word descriptions, benchmark one-pager, contact. Makes newsletter inclusion zero-effort.

---

## 5. Channel playbook with drafts

General: post from the owner's real account. Disclose "I built this." Reply to every substantive comment in the first 4 hours. Do not cross-post the identical text to several subreddits at once; space them and tailor them.

### 5.1 Hacker News (Show HN)

Rules checked (news.ycombinator.com/showhn.html and newsguidelines.html, fetched 2026-11-12): Show HN must be something people can try, non-trivial, built by the poster, with the poster around to discuss it. No asking friends to upvote or comment; "do not solicit upvotes, comments, or submissions." Easy to try without sign-up is encouraged. This means: the repo must be public and installable before posting, and no star or upvote asks in the post or in DMs.

Timing: US weekday morning, Tuesday to Thursday, about 8:00 to 10:00 US Eastern (this is common practitioner advice, not an HN rule; see STARS_1000.md). Submit the GitHub URL (not the blog post) as the link, so that the page itself is tryable.

**Title options** (limit 80 chars; no emoji, no all-caps, no "Show HN: I made" fluff):
1. `Show HN: Warrant – code that checks the numbers and citations in AI research`
2. `Show HN: Warrant – a referee that reads every paper you cite (stdlib Python)`
3. `Show HN: I recomputed 2,063 p-values from 851 papers and built a checker for it`

Recommended: option 1 (plain, accurate, tryable). Keep option 3 as the follow-up post angle.

**First comment (post immediately after submitting; HN convention is for the author to add context):**

```
Hi HN, I built warrant because AI agents that help with research keep producing
two kinds of errors that read fine: numbers that no experiment produced, and
citations that don't exist or point at a different paper. Asking another model to
check the first one has the same blind spot, so warrant uses plain code wherever
code can decide.

What it does:

1. Live, inside Claude Code / Codex / OpenCode via hooks: every number in the AI's
   reply must trace to a command that actually ran (within rounding, a mean of
   seeds, or a difference/ratio of traced numbers). DOIs, arXiv ids and quoted
   titles are resolved against doi.org, arXiv, OpenAlex and Crossref. Reported
   p-values are recomputed from their test statistic. A failing reply is sent back
   once with the exact reason.

2. `warrant review <arXiv id | LaTeX folder>`: a referee report. It reads the cited
   papers' full text, checks that numbers attributed to a cited paper exist in it,
   recomputes p-values (statcheck method, incomplete beta/gamma written from
   scratch), runs GRIM on means, and builds small BM25 evidence cards so the model
   judges ~13x fewer words (measured: 2,224 vs 28,916 on arXiv:1706.03762). Every
   model verdict must include a quote that exists verbatim in the cited paper, or
   code rejects it. In one real run, 3 verdicts were accepted and 1 invented quote
   was rejected.

3. `warrant audit <DOI | arXiv id | .bib>`: does every reference exist? On the
   AlphaFold Nature paper: 84 refs, 75 verified, 0 false flags, 41 s. It only calls
   a reference "not found" if no registry has ever heard of the title; a broken DOI
   on a real paper comes back "unchecked".

Benchmark: I recomputed 2,063 p-values across 851 open-access psychology papers
(Europe PMC). 215 reported APA-style tests; in 6 of them (2.8%) a significance
decision contradicts the paper's own statistic, e.g. t(1350)=0.150 reported as
p=.04 (really .88). I checked all 6 by hand. I'm deliberately not publishing the
paper IDs: these are most likely typos, not misconduct. On 366 recent arXiv papers
(22 with APA-style tests, 91 tests) it found 0 inconsistencies, after I fixed 20
false positives that turned out to be parser bugs (scientific-notation p-values,
Bonferroni-adjusted values).

Limits: tracing proves a number was produced, not that the code is right; `echo
0.93` produces a 0.93 (the trail records it, but it's tamper-evident, not
tamper-proof). Quote checks against cited papers need full text, available for
arXiv. statcheck needs APA-style reporting. Details in the README.

Stdlib-only Python 3.10+, MIT. `pip install warrant-research` then
`warrant audit refs.bib` on your own bibliography; no keys needed. I'd love
feedback on false positives especially: if it flags something wrong, please open an
issue with the input and I'll add a regression test.
```

Replies to expect and prepared answers:
- "Isn't this just statcheck?" Credit statcheck and GRIM by name; the new part is running them (plus reference existence and number provenance) as a live gate on an agent's output and as a quote-verified review loop.
- "echo 0.93 defeats it." Agree; README states it; hash-chained audit trail makes it visible, not impossible.
- "2.8% is low / high compared to the literature." Say the sample is open-access psychology papers matching a specific query, only APA-style reporting was parsed, and it is not a prevalence estimate for the field. Do not compare to other studies' numbers unless you have re-read them.
- "Why not an LLM judge?" See the "why code" paragraph; where judgment is needed an LLM is used, but constrained by verbatim quote verification.
- "Won't this hammer Crossref/OpenAlex?" Be honest about caching and rate limits; see risks section.

### 5.2 X / Twitter thread

Post Tuesday-Thursday, US morning. Attach media to tweet 1 (before/after card) and tweet 4 (review GIF). Pin it.

```
1/ Claude wrote: "accuracy improves to 0.874 (vs 0.809), consistent with Müller et al.
(doi 10.48550/arXiv.1906.99999)."

The 0.874 was never produced. The DOI doesn't exist. Both look fine.

I built warrant: code, not a model, checks AI research claims. [before/after image]

2/ Live, inside Claude Code, Codex and OpenCode: every number in the reply must trace
to a command that actually ran. DOIs and arXiv ids are resolved against doi.org,
arXiv, OpenAlex, Crossref. Reported p-values are recomputed. A failing reply goes back
once with the exact reason.

3/ Why not "ask another model to check"? Same blind spot. Research agents grading their
own homework is the problem, so wherever code can decide, code decides.

4/ `warrant review 1706.03762` writes a referee report. It reads the cited papers' full
text, so the model doesn't have to: 2,224 words of evidence cards vs 28,916 words of
papers (13x less) on the Transformer paper. [review GIF]

5/ The key rule: every model verdict must quote the cited paper verbatim. If the quote
isn't in the paper, code rejects the verdict. In one real run: 3 accepted, 1 invented
quote rejected.

6/ Reference audit for any DOI: `warrant audit 10.1038/s41586-021-03819-2`. AlphaFold's
Nature paper: 84 refs, 75 verified, 0 false flags, 41 s. It only says "not found" when
no registry has ever heard of the title.

7/ Benchmark: I recomputed 2,063 p-values across 851 open-access psychology papers. In
6 papers (2.8% of the 215 reporting tests) a significance decision contradicts the
paper's own statistic, e.g. t(1350)=0.150, p=.04 (really .88). All hand-verified. [funnel image]

8/ I am not publishing the paper IDs. These are most likely typos, not misconduct. The
point is that a machine should check before a reviewer has to.

9/ Honest limits: it proves a number was produced, not that the code was right. `echo
0.93` fools it (tamper-evident, not tamper-proof). On 366 recent arXiv papers it found 0
errors, after I fixed 20 false positives that were my parser's fault.

10/ Stdlib Python, zero dependencies, MIT. `pip install warrant-research` then run
`warrant audit refs.bib` on your own paper before your reviewer does.
github.com/ItsShreyamHere/warrant
If it catches something, tell me. If it flags something wrong, tell me faster.
```

Do not ask for retweets in tweet 1. One soft "if useful, share" at the end of the thread is fine.

### 5.3 Reddit

Rules checked (secondhand only; the official rules page did not surface in search): r/MachineLearning reportedly confines direct self-promotion to a periodic self-promotion thread and uses flairs including [P] for projects. Read the live sidebar and rules on each subreddit before posting; if a rule conflicts with a draft, the rule wins. Reddit also has a site-wide norm against only posting your own content; participate in the subs before launch day (comment helpfully for 1-2 weeks beforehand). Do not post the same text in multiple subs on the same day.

**r/MachineLearning** (use [P] flair if self-posts of projects are permitted, otherwise the self-promotion thread):

Title: `[P] warrant: code (not an LLM) checks the numbers, citations and p-values in AI research output; 13x less reading for paper review`

```
I built an open-source tool for a problem I kept hitting with research agents:
write-ups with numbers no run produced and citations that don't exist.

Design choice: wherever code can decide, code decides.
- Numbers in an agent's reply must trace to captured command output (within
  rounding; means over seeds; differences/ratios of traced numbers).
- DOIs/arXiv ids/quoted titles resolve live against doi.org, arXiv, OpenAlex, Crossref.
- Reported p-values are recomputed from t/F/chi2/r/z (statcheck method, no scipy).
- For `warrant review <arXiv id>`: BM25 evidence cards from the cited papers' full
  text (2,224 vs 28,916 words on arXiv:1706.03762), the model judges only those, and
  every verdict needs a quote that exists verbatim in the cited paper or it's rejected.

Evaluation, with its limits: 2,063 p-values over 851 open-access psychology papers;
6 papers (2.8% of the 215 reporting APA-style tests) have a significance decision
their own statistic contradicts, hand-verified (likely typos). On 366 recent arXiv
papers: 0 errors after fixing 20 parser false positives. The arXiv sample had only 22
papers with APA-style tests, so this says little about arXiv ML papers' statistics.
Method and results: bench/RESULTS.md.

Known gaps: tracing proves a number was produced, not that the code is right; quote
checks need full text (arXiv); `review` for non-arXiv cited papers checks existence
only. Works as hooks in Claude Code / Codex / OpenCode, and as a stdlib-only CLI.

Repo: github.com/ItsShreyamHere/warrant. Feedback on false positives especially welcome.
```

**r/academia** (focus on reference checking, not AI hype; confirm that tool posts are allowed first, else ask mods by modmail):

Title: `Free tool to check that every reference in your paper or bibliography actually exists (DOI, arXiv, OpenAlex, Crossref)`

```
Fabricated or mangled references are a growing worry now that people draft with AI
tools. I wrote a free, open-source (MIT) command-line checker you can run on your own
bibliography before submission:

  warrant audit refs.bib
  warrant audit 10.1038/s41586-021-03819-2   # reads the publisher-deposited reference list

It checks each reference against doi.org, arXiv, OpenAlex and Crossref. It only calls a
reference "not found" if no registry has heard of the title; a broken DOI on a real
paper is reported as "unchecked", not fake. On the AlphaFold Nature paper it verified
75 of 84 references with 0 false flags in 41 seconds. A "not found" result is a lead to
check by hand, not proof of anything.

It also recomputes reported p-values from test statistics (statcheck method) and runs
GRIM on means. Everything runs locally; no accounts, no uploads except lookups of
titles/DOIs to the public registries.

I'm the author. Happy to hear where it gets something wrong.
```

**r/PhD** (peer tone, "I built this for myself" if true, concrete value):

Title: `I made a free checker that audits your .bib and recomputes your p-values before your reviewers do`

```
Reviewer 2 finding a bad reference or an inconsistent p-value is the worst. I built an
open-source tool that does the boring check ahead of time:

- warrant audit refs.bib: does every reference exist (doi.org, arXiv, OpenAlex, Crossref)?
- warrant stats draft.md: recompute every p-value from t/F/chi2/r/z, and GRIM-check means.
- warrant review <arXiv id or your LaTeX folder>: a referee-style report; numbers you
  attribute to a cited paper are checked against that paper's full text.

Stdlib Python, runs locally, MIT. It's not a replacement for reading; it's the spell-check
for evidence. Limits are in the README (e.g. statcheck needs APA-style reporting; GRIM
only applies to integer-valued data). If you try it on your own draft I'd love to hear
what it got wrong.
```

**r/ClaudeAI** (usually friendly to plugins; check for a "Built with Claude" or promotion flair):

Title: `Built a Claude Code plugin that blocks replies containing numbers no command produced or citations that don't exist`

```
Claude Code plugin, hooks-based, MIT, zero dependencies:

- PostToolUse hook captures every command output and file read.
- Stop hook checks the final reply: every decimal/percentage must trace to captured
  output (within rounding, mean of seeds, or difference/ratio), DOIs/arXiv ids/quoted
  titles must resolve, reported p-values must follow from their test statistic.
- If not, the reply is sent back once with the exact list. Silent in projects without
  `warrant init`. Hooks add 0 tokens; the skill is about 100 tokens/session.

Install:
  /plugin marketplace add ItsShreyamHere/warrant
  /plugin install warrant@warrant

Also `/warrant-review` style workflow: `warrant review <arXiv id>` writes a referee report
where the model must quote the cited paper verbatim (or the verdict is rejected).
Demo GIF and benchmark in the repo. I built it with Claude Code; feedback on the hook UX welcome.
```

**Codex / OpenAI community** (r/OpenAI, r/codex or whichever Codex-specific community exists; verify it exists and its rules first; OpenAI developer forum is another option):

Title: `Codex plugin: hooks that send back replies with untraced numbers or fake citations`

```
Open-source (MIT) plugin for Codex that runs the same checks as the Claude Code version.
Codex hooks capture tool outputs; when the reply finishes, each number must trace to a
command that ran, citations are resolved live (doi.org/arXiv/OpenAlex/Crossref), and
reported p-values are recomputed. A failing reply is sent back once with the reason.

  codex plugin marketplace add ItsShreyamHere/warrant --enable plugins
  codex plugin add warrant@warrant --enable plugins

You need to review and trust the hooks once in /hooks. Also ships a CLI:
`warrant review <arXiv id>`, `warrant audit refs.bib`. Zero dependencies, Python 3.10+.
Looking for feedback from people running longer Codex research/analysis tasks.
```

Also post a variant in r/LocalLLaMA only if there is an honest angle (local-first, no keys, no tokens for the checks); otherwise skip.

### 5.4 LinkedIn

Audience: PIs, research engineers, journal staff. Longer, narrative, no hashtags beyond 3. Post as the owner, with the before/after card.

```
An AI research assistant told me accuracy improved to 0.874 and cited a DOI.
Neither the 0.874 nor the DOI existed.

That is the failure mode that worries me most about AI in research: not obvious nonsense,
but fluent, checkable-looking claims nobody checked.

So I built warrant (open source, MIT): a referee that uses code, not another model, to
check research claims.

- Every number in an AI's reply must trace to a command that actually ran.
- Citations are resolved live against doi.org, arXiv, OpenAlex and Crossref.
- Reported p-values are recomputed from their test statistics.
- `warrant review` reads the cited papers' full text and builds short evidence cards
  (about 13x less reading); the model has to quote the source verbatim or the verdict is rejected.

I also ran the statistics check on 851 open-access psychology papers: 2,063 p-values
recomputed. In 6 papers (2.8% of the 215 reporting tests), the paper's own statistic
contradicts a reported significance decision. Hand-verified, and I am not publishing the
papers: these are most likely typos, not misconduct. The point is that a machine should
catch them before a reviewer has to.

If you edit a journal, organise a conference, supervise students or just write papers:
`warrant audit refs.bib` takes under a minute. I'd value your feedback.
github.com/ItsShreyamHere/warrant
#research #openscience #AI
```

### 5.5 Mastodon / Bluesky (science and metascience communities)

Tone: methods-first, less promotional. Tag only people who work on this topic, and only after reading their work. One post, one thread reply with the benchmark.

```
Built an open-source tool in the statcheck/GRIM tradition, packaged for AI-assisted
writing: recompute p-values from t/F/chi2/r/z, GRIM-check means, and verify that every
reference exists (doi.org, arXiv, OpenAlex, Crossref). 2,063 p-values over 851 open-access
psychology papers; 6 papers (2.8% of those reporting tests) have a significance decision
their own statistic contradicts, hand-verified, IDs withheld (likely typos).
Method + limits: github.com/ItsShreyamHere/warrant (bench/RESULTS.md)
#metascience #openscience #reproducibility
```

Follow-up reply: "Credit: the statistics check follows the statcheck method (Nuijten et al.) and GRIM (Brown & Heathers). Corrections welcome."

### 5.6 Discords and forums

Join and contribute before posting. Post only in a designated showcase/projects channel, one message, no DMs asking for stars.
- Claude Code community Discords / Anthropic developer community: #showcase.
- OpenCode community (Discord/GitHub Discussions).
- Codex community channels.
- ML/AI-for-science Discords (e.g. Eleuther-adjacent or Hugging Face science channels): check rules; many forbid promotion outside a projects channel.
- Open Science / Reproducibility groups (Slack or Discord of local ReproducibiliTea chapters, UK Reproducibility Network). These are a better fit for the metascience angle than for "star the repo".
- GitHub Discussions on the repo itself: open a "Show your results" thread to collect real-world catches (with permission to quote).

Template:

```
Showcase: warrant, an open-source plugin/CLI that checks the numbers, citations and
p-values in AI research output with code instead of a model. Works in [Claude Code /
Codex / OpenCode]. Install: [one line]. Benchmark and limits in the README. I'm the
author; would love feedback from people who write papers with agents.
```

---

## 6. Outreach list (types, not spam)

Send individual, personal, short emails; never mass-mail; one follow-up at most. Lead with something useful for them (a reproducible result, a method question), not "please star."

| Who | Why | What to send | Notes |
|---|---|---|---|
| statcheck / GRIM / SPRITE / research-integrity community (authors of statcheck, GRIM; Nuijten, Brown, Heathers are the public names of those methods) | Our checks implement their methods; their review is the best credibility available | Method note + `bench/RESULTS.md`, ask for a correctness review of the implementation | Offer to credit and to fix any divergence from statcheck. Do not ask for endorsement; ask for criticism. Verify names/affiliations before emailing. |
| Metascience and meta-research groups (e.g. university meta-research centres, the Society for Improving Psychological Science, UK Reproducibility Network, ReproducibiliTea chapters) | Audience for the benchmark | Short pitch + offer to run on their own corpus | Share methods, not offender lists. |
| Journal editors and managing editors, especially those that already run statcheck-style or reference checks | Potential adopters of the GitHub Action | Pilot offer: run `warrant audit` on a submissions batch locally | Be explicit it flags leads, not verdicts. |
| Conference organisers (ML venues, reproducibility tracks and checklist teams) | Fabricated-reference worries are live there | Offer: reference-existence check as a CI step | Lead with the Action and badge. |
| AI-for-science newsletters and blogs (search for current ones; e.g. general ML newsletters, Import AI-style, Last Week in AI, science-communication blogs, Retraction Watch readers' adjacent outlets) | Reach beyond GitHub | Press kit + 3 bullets + one quotable stat | Verify each newsletter's submission form; some take submissions publicly, others do not. Only claim "featured" when it happens. |
| Awesome-lists (see 6.1) | Persistent discovery | One PR each, following their template | Follow each CONTRIBUTING exactly. |
| Plugin marketplaces and directories (see 6.2) | One-command install discoverability | Listing/PR | Check each one's review rules. |
| Creators of adjacent tools (K-Dense-AI/claude-scientific-skills, `falsify`, `epistemic-skills`, citation-checker repos) | Cross-link, avoid appearing hostile | A friendly issue/discussion: "we adapted the comment structure of your peer-review skill with credit; here's an integration idea" | Credit is already in SKILL.md; keep it in the README too. Do not disparage. |
| Researchers who tweet about AI hallucinated citations | They have the problem | Reply with a useful tool result, once | No cold DMs of "check my project." |

### 6.1 Awesome-lists (verify each list's current rules in its CONTRIBUTING.md before opening a PR)

Search result on 2026-11-12 confirmed these exist; exact submission steps were not retrieved and must be read from the repos:
- `hesreallyhim/awesome-claude-code` (its contributing guide says the list works on community recommendation against quality standards, the first being relevance to Claude Code).
- `VoltAgent/awesome-agent-skills` (has a CONTRIBUTING.md; describes 1000+ agent skills).
- `ComposioHQ/awesome-claude-skills`, `BehiSecc/awesome-claude-skills`, `jqueryscript/awesome-claude-code`, `Chat2AnyLLM/awesome-claude-skills`.
- Codex and OpenCode equivalents: search GitHub for `awesome-codex`, `awesome-opencode` at submission time.
- Research tooling lists: awesome-reproducible-research, awesome-open-science, awesome-research-integrity (if any; search), awesome-scientific-writing, awesome-citation-managers. Verify they exist and are maintained.

PR template for any list:

```
Add warrant: checks research claims with code

warrant is a plugin (Claude Code / Codex / OpenCode) and stdlib-only Python CLI that
verifies that numbers in an agent's reply trace to commands that ran, resolves citations
live (doi.org/arXiv/OpenAlex/Crossref), recomputes reported p-values, and produces a
referee-style review where every model verdict must quote the source verbatim.
Link: https://github.com/ItsShreyamHere/warrant. MIT, v1.0.0, tests in CI.
```

Some lists require a minimum repo age, a release, or a number of stars; check, and do not submit before they are satisfied rather than arguing with maintainers.

### 6.2 Plugin marketplaces / directories

- Claude Code marketplace: the repo is already a marketplace (`/plugin marketplace add ItsShreyamHere/warrant`). Also check whether Anthropic has an official plugin directory with a submission process at launch time (search; do not assume).
- Codex plugin marketplace: same, already structured; check for an official listing path.
- OpenCode plugin listings and the skills.sh / agentskills-style directories; MCP/skill directories such as mcp.directory (the search surfaced a "Submit a Skill" page there; verify it accepts skills of this type).
- PyPI (`warrant-research`) as a discovery channel in itself: good description, classifiers, project URLs, and keywords (`reproducibility`, `statcheck`, `citation`, `peer-review`, `research-integrity`, `llm-agents`).
- GitHub topics: `claude-code`, `codex`, `opencode`, `agent-skills`, `research`, `reproducibility`, `statcheck`, `citation-checker`, `peer-review`, `llm`, `hallucination`, `open-science`.

---

## 7. Messaging do and don't

| Do | Don't |
|---|---|
| "Flags inconsistencies for humans to check." | "Catches bad science" / "exposes fraud." |
| "6 of 215 papers reporting tests (2.8%), hand-verified." | "2.8% of papers are wrong." |
| "0 errors on 366 arXiv papers after fixing 20 false positives, small sample (22 with APA-style tests)." | "Zero errors on arXiv." |
| "Not found anywhere is a lead, not proof." | "Detected a fake reference" without a manual check. |
| Credit statcheck, GRIM, K-Dense peer-review comment structure. | Imply the statistics methods are novel. |
| Show the limits (echo 0.93). | Claim tamper-proof. |

---

## 8. Risks and mitigations

| Risk | Detail | Mitigation |
|---|---|---|
| Accusation / defamation | A post or report implies a named author fabricated or erred. | Never name or link benchmark papers; strip IDs from screenshots, filenames, and issue examples; say "typos are the usual cause"; in the tool output keep "lead, not proof"; sample reports only on well-known, clean papers or the owner's own; if an outsider posts a flagged real paper in an issue, ask them to contact the authors/journal first and consider redacting. Get a quick legal/policy read if any institution asks for a pilot. |
| Rate limits under load | HN or X traffic leads thousands of runs hitting doi.org, arXiv, OpenAlex, Crossref, Europe PMC from users' machines (and CI users). | Confirm the CLI caches lookups on disk, backs off on 429/5xx, identifies itself with a polite User-Agent and a mailto where the APIs ask for one (OpenAlex and Crossref polite-pool guidance; verify current docs), and degrades to "unchecked", never "fake", on a failed lookup. Test with a load script before launch. Document in README how to set an email/contact and cache dir. No central server to melt: all calls come from users' machines. |
| False positive goes viral | One screenshot of warrant calling a correct reference fake or a valid p-value wrong. | The "fake" label is only for titles absent from all registries; keep that bar. Add an "Is this a false positive?" issue template and a 24-hour SLA on fixes during launch week. Pre-run `audit` on 20+ famous papers and fix everything before launch. Keep a `bench/FALSE_POSITIVES.md` log; publish fixes quickly, which is good PR. |
| Benchmark challenged | "Your 2.8% is wrong / unrepresentative." | The sample, query and method are in `bench/RESULTS.md`; say it is not a prevalence estimate; invite replication with the scripts (`bench/scan_pmc.py`). Do not argue; thank and fix. |
| "Just a wrapper / just statcheck" | Commenters dismiss it. | Lead with provenance tracing and quote-verified review, which are the new parts; credit statcheck up front. |
| Supply-chain or security worry | Hooks run code on every reply; Python package from a new author. | Zero dependencies; publish PyPI with trusted publishing (OIDC) if possible; SECURITY.md; document exactly what hooks read/write (`.warrant/` only) and what is sent to the network (titles/DOIs to public registries). |
| Hooks break a user's session | Bad hook can block or slow a reply. | Each reply blocked at most once; silent without `warrant init`; add a `WARRANT_OFF=1` kill switch if one doesn't exist; document. |
| Name collision | "warrant" is a common word (legal sense; other packages). | Always use "warrant (research)" in search-facing copy; PyPI name is `warrant-research`; add topics and the tagline in the repo description so search finds it. Check trademark/PyPI/GitHub for conflicts before the big push. |
| README issues at launch | The README contains a stale duplicate compatibility-table fragment right after the "Works with" table (broken Markdown table starting `---\|:---:\|`). | Fix before going public. |
| Star-bait feels pushy | The README has several "star warrant" nudges. | Keep at most two (after the review section and at the bottom); the rest dilutes credibility with researcher audiences and HN readers. |
| Ethics backlash | "AI to police researchers." | Frame as a self-check for authors; offer an opt-in pilot to editors; never publish lists of flagged papers. |

---

## 9. Positioning against competitors (for replies, not for attack posts)

- Skill mega-repos (obra/superpowers, caveman, claude-mem, karpathy/autoresearch, uditgoenka/autoresearch): different category; warrant is a verification layer that sits under any of them. A good line: "autoresearch generates experiments; warrant checks what the agent then claims about them." Do not claim a comparison you haven't tested.
- claude-scientific-skills (K-Dense-AI): has a prompt-only peer-review skill; warrant adapted its comment structure with credit (MIT) and differs by having code do the checking and quote verification. Say "complements."
- Small citation checkers: they check references; warrant also traces numbers, recomputes statistics, and quote-verifies model judgments.
- `falsify` and `epistemic-skills`: do pre-registration; warrant also has pre-registration but decided by code, plus the graveyard.

---

## 10. Sources checked

- Hacker News Show HN rules: https://news.ycombinator.com/showhn.html
- Hacker News guidelines: https://news.ycombinator.com/newsguidelines.html
- r/MachineLearning self-promotion conventions (secondhand; confirm on the live sidebar): https://aiexpert.network/r-machinelearning/ and https://thehiveindex.com/communities/r-machine-learning/
- Awesome-lists located by search (read each CONTRIBUTING.md): https://github.com/hesreallyhim/awesome-claude-code (see https://www.mintlify.com/hesreallyhim/awesome-claude-code/contributing), https://github.com/VoltAgent/awesome-agent-skills, https://github.com/BehiSecc/awesome-claude-skills, https://github.com/ComposioHQ/awesome-claude-skills, https://github.com/jqueryscript/awesome-claude-code
- mcp.directory skill submission page (surfaced by search, not verified): https://mcp.directory/submit-skill

Not verified (do before use): the official rules of r/academia, r/PhD, r/ClaudeAI, any Codex community; marketplace review policies; newsletter submission processes; exact text of the 2026 preprints on agents gaming evaluations; competitor star counts (taken from the owner's brief).
