# warrant: plan to ~1,000 GitHub stars in 1-2 weeks

For: the Codex agent and the human owner. Companion: `MARKETING.md` (all post drafts, assets, risks). Written 2026-11-12.

Ground rules: no bought stars, no sockpuppets or alt accounts, no star-for-star swaps, no asking friends to upvote HN posts (HN Show HN rules forbid it; https://news.ycombinator.com/showhn.html). Seeding from the owner's real network by asking people who would genuinely use the tool to try it, and star it if they like it, is fine on GitHub, not on HN.

---

## 0. Realistic expectations (read first)

- 1,000 stars in 1-2 weeks is an upside outcome, not the median. I found no reliable published base-rate for launch outcomes, so the scenarios below are planning assumptions from judgment, not statistics. Treat them as bands to steer by, not forecasts.
- Planning bands for the first 14 days (assumptions):
  - Quiet: under 150. No front-page hit; only the owner's network and a few shares.
  - Solid: 150-500. Good traction in one or two channels (a decent HN run, or one strong X thread, plus list inclusions).
  - Breakout: 500-1,500+. Show HN reaches the front page for several hours and a second channel (X, newsletter, Reddit) amplifies.
- Stars are driven by a few spikes, not steady growth. Most of the total typically arrives in the first 48 hours after a hit. So plan for one big shot (Show HN) with the best possible preparation, and a series of smaller shots afterwards. The plan below makes the big shot count: a tryable repo, a clean README, working install, replies in minutes.
- The reputational goal ("household name among researchers") is a months-long goal. Stars are a lagging indicator of usefulness; installs, issues from real users, and a mention by a research-integrity person are better signals. Do not trade credibility for stars.
- Competitors in the brief have six-figure stars largely as general-purpose coding-agent tools. warrant is a niche (research integrity). A niche tool reaching 1,000 in two weeks needs the HN/X crossover audience (AI-tool people curious about research) as well as researchers.

---

## 1. Pre-launch checklist (target: complete by T-3 days; T = launch day)

Owner decisions are marked **[OWNER]**; the rest an agent can do.

### 1.1 Repo hygiene and privacy
- [ ] **[OWNER]** Decide the public name and GitHub org/user. Check name collisions ("warrant" is a common word): GitHub search, PyPI (`warrant-research`), npm. Put the research context in the repo description so search finds it.
- [ ] History cleanup before going public: scan all history for secrets and personal data (`git log -p | grep` for tokens/keys/emails, or run gitleaks/trufflehog locally); check `bench/` for paper IDs or any cached full texts of flagged papers (benchmark IDs must not be published, including in git history, caches, notebooks, or logs). If anything is in history, rewrite with `git filter-repo` on a fresh clone and verify with a second scan. **[OWNER]** approves any history rewrite and the force-push (this is destructive; do it on a fresh mirror clone, keep a private backup).
- [ ] Confirm `.warrant/`, `warrant-review/`, local config and `.env` are in `.gitignore`.
- [ ] Remove unrelated or internal files (e.g. anything from the parent "ROS" projects) from the repo.
- [ ] LICENSE (MIT) present; add `SECURITY.md` stating what hooks read/write and what leaves the machine (titles/DOIs to public registries).
- [ ] Fix the README: delete the stale duplicate table fragment after the "Works with" table (starts with `---|:---:|:---:|:---:|`), reduce star-nudges to two, make sure every number matches `bench/RESULTS.md`, and make install commands match reality (PyPI name, marketplace names).
- [ ] Add a README "Is this a false positive?" link and a "Not found anywhere is a lead, not proof" line near `audit`.

### 1.2 Packaging and release
- [ ] **[OWNER]** Create PyPI account/project; publish `warrant-research` (use TestPyPI first; then PyPI, ideally via GitHub Actions trusted publishing). Verify in a clean venv and on Windows, macOS, Linux: `pip install warrant-research && warrant --help && warrant audit refs.bib`.
- [ ] Tag and release **v1.0.0** with a changelog and release notes (copy the README highlights). The GitHub Action currently references `@v0`; publish both `v1` and keep `v0` working, or update the README to `@v1`.
- [ ] Verify the three install paths on a clean machine: Claude Code (`/plugin marketplace add ...`), Codex (`codex plugin marketplace add ...`), OpenCode (`scripts/install.sh --opencode`). Record any failure and fix before launch. A broken install on launch day is the single most expensive mistake.
- [ ] CI: tests pass on 3 OSes and Python 3.10-3.13; add a CI badge to the README.
- [ ] Load/politeness test: run `warrant audit` on a 200-reference .bib with a cold cache, then warm; confirm caching, backoff on 429/5xx, polite User-Agent, and "unchecked" (never "fake") on failure. See MARKETING.md risks.
- [ ] Pre-flight false-positive sweep: run `audit` and `review` on at least 25 famous, well-cited papers (Transformer, AlphaFold, ResNet, BERT, a CONSORT trial, a psychology classic with APA stats, etc.). Fix every wrong flag; log in `bench/FALSE_POSITIVES.md`. Reuse the clean ones as sample reports.

### 1.3 Repo presentation (GitHub is the landing page)
- [ ] Social preview image uploaded (1280x640).
- [ ] Repo description (one line, under 120 chars) plus website link (docs site). Suggested: `The referee that reads every paper you cite. Code (not a model) checks numbers, citations and p-values in AI research.`
- [ ] Topics: `claude-code`, `codex`, `opencode`, `agent-skills`, `research`, `reproducibility`, `statcheck`, `citation-checker`, `peer-review`, `llm`, `hallucination`, `open-science`.
- [ ] README top-of-fold test: in 5 seconds a stranger sees hero, headline, stat cards, demo GIF. The review demo GIF (new) is added right under the hook demo.
- [ ] `CONTRIBUTING.md` (how to run tests, how to add a statcheck regression test, how to report a false positive), `CODE_OF_CONDUCT.md`.
- [ ] Issue templates: Bug, **False positive**, Feature request, "Show your results" (with consent to quote). PR template. Enable Discussions (categories: Show and tell, Q&A, Ideas).
- [ ] 10 labelled `good first issue` / `help wanted` issues (real ones: new reporting formats for statcheck, BibTeX edge cases, more registries, docs, translations). Newcomers who contribute become advocates.
- [ ] Docs site on GitHub Pages: hero, install tabs, before/after, a sample `report.md`, benchmark page, FAQ (including "isn't this statcheck?" and "echo 0.93"). Fast, mobile-friendly.

### 1.4 Assets (see MARKETING.md section 4 for specs)
- [ ] Review demo GIF, before/after card, benchmark funnel image, 60-90 s video, launch blog post, press kit folder.
- [ ] All drafts proof-read against `README.md` and `bench/RESULTS.md`. No benchmark paper IDs anywhere.

### 1.5 Seeding from the network, honestly (T-14 to T-1)
- [ ] **[OWNER]** Make a list of 20-50 people who really have the problem: labmates, supervisors, collaborators, classmates, colleagues, friends who write papers or use agents. Send each a personal message: what it is, a one-line install, and "I'd value your feedback; if it's useful, a star helps others find it." Do not mass-post, do not ask them to vote on HN, and do not offer anything for stars.
- [ ] Ask 3-5 of them to try it on their own paper/bib and reply with what happened (real feedback > stars). Fix what breaks.
- [ ] Ask 2-3 people with relevant credibility for a pre-launch technical review (statcheck/GRIM-aware researcher, a Claude Code/Codex plugin author, a journal-adjacent person). Do not ask them to promote it.
- [ ] Honest expectation: this yields roughly the 20-50 early stars the brief targets, so the repo does not look empty on launch day, and more importantly it yields bug reports.
- [ ] Warm up accounts you will post from: the owner comments genuinely in relevant subreddits/HN threads for 1-2 weeks before posting (Reddit communities often discount first-time self-promoters; this is participation, not astroturf).
- [ ] Contact the plugin ecosystems: open a friendly issue or discussion with adjacent projects (K-Dense claude-scientific-skills; credit is in SKILL.md) after the repo is public.

### 1.6 Make the repo public
- [ ] **[OWNER]** Flip visibility to public at T-2 days (not on launch day), after final secrets and benchmark-ID scan. This lets list PRs, directory crawlers and early testers see it, and exposes any problem before the big post.
- [ ] Re-run install tests against the public repo URL from a clean machine.

### 1.7 Metrics set-up (T-2)
- [ ] GitHub Insights: Traffic (visitors, views, referrers, popular content) is only retained 14 days; export numbers daily into a spreadsheet.
- [ ] Star history: record the count at the same time each day (a cron or manual sheet). Optional: star-history.com chart for the retrospective.
- [ ] UTM-tag every link used in posts: `?utm_source=hn|x|reddit-ml|...` on the docs site link (GitHub itself does not honour UTMs, so use the docs site or a link shortener for attribution; GitHub Traffic referrers covers the rest).
- [ ] PyPI downloads: pypistats.org (or BigQuery) for installs, note it includes mirrors and bots.
- [ ] Spreadsheet columns: date, stars total, stars delta, unique visitors, views, top referrer, clones, PyPI downloads, issues opened, issues closed, posts published, notable mentions.

---

## 2. Launch timing: choose the day

- Best window (practitioner convention, not a rule): Tuesday, Wednesday or Thursday, submit to HN about 8:00-10:00 US Eastern (13:00-15:00 UTC; 18:30-20:30 India time). The owner's availability matters more: pick a day where both owner and agent can reply for 8+ hours straight.
- Avoid: US holidays, Fridays through Sunday, big AI-company launch days (check news that morning), the week of a major conference deadline cluster if it can be avoided.
- Suggested calendar: if the repo is public on Sunday/Monday, launch Tuesday. (Today is 2026-11-12, a Thursday; the earliest realistic launch is Tuesday 2026-11-17 or 2026-11-18 if the checklist is ready. Do not rush: a stale README or broken install is more costly than a 3-day delay. US Thanksgiving is 2026-11-26; prefer a launch before 11-24 or after 11-30.)
- Time zones: owner and agent split the monitoring shifts so that someone answers comments within ~15 minutes for the first 6 hours.

---

## 3. Launch day (T) hour by hour

All times US Eastern unless noted; adapt to the chosen day. "Agent" = Codex agent; "Owner" = human.

| Time | Action | Who |
|---|---|---|
| T-1 evening | Final smoke test of all three install paths from a clean environment. Check PyPI page renders. Draft all posts open in tabs. Sleep. | Both |
| 07:30 | Re-check: `pip install warrant-research` works; repo public; release v1.0.0 visible; docs site up; GitHub Traffic baseline recorded; star count recorded. | Agent |
| 08:00 | **Submit Show HN** (link = GitHub repo). Title: `Show HN: Warrant – code that checks the numbers and citations in AI research`. Post the first comment immediately (full draft in MARKETING.md 5.1). Do not share the HN link with anyone asking for upvotes. Sharing the link in a neutral announcement with no voting ask is a grey area that HN moderators scrutinise; the safe route is to just tell people the project exists via the other channels and the repo, not to circulate the HN URL for upvoting. | Owner |
| 08:00-12:00 | Reply to every HN comment within minutes. Be factual, thank critics, concede valid points, fix bugs live and say "fixed in commit X". Open an issue for every false-positive report. | Owner (HN), Agent (fixes) |
| 08:15 | X thread (MARKETING.md 5.2), pinned, with images. | Owner |
| 09:00 | If HN has not moved (no points by about 1 hour), do not repost immediately and do not ask for upvotes. See decision points section 6. If it is climbing, keep replying; do not post to Reddit yet (avoid splitting attention). | Owner |
| 10:30 | r/ClaudeAI post (MARKETING.md 5.3), only after reading its current rules. | Owner |
| 12:00 | LinkedIn post. Mastodon/Bluesky posts. | Owner |
| 13:00 | Discord showcase posts (Claude Code / OpenCode / Codex communities). | Owner |
| 14:00 | Review all issues and comments; triage: bugs, false positives, feature requests. Ship hotfix release v1.0.1 if install or false-positive problems appear. | Agent |
| 15:00 | r/MachineLearning [P] post (or the self-promotion thread) if rules allow; r/codex-style community. | Owner |
| 17:00 | Update README with any quick fixes; add a "Launch day: thanks and what we fixed" discussion post. | Agent |
| Evening | Record stars, visitors, referrers. Write a short log of what people asked; seed the FAQ. | Agent |
| Late | Reply to remaining comments; plan Day 2 content from the top questions. | Both |

Launch-day rules:
- Reply to every comment; be concise; never defensive.
- Never ask for stars in comments. The README is where the nudge lives.
- If someone finds a real bug, fix it the same day and say so publicly; visible responsiveness is the best conversion driver after the hook.
- Do not delete critical comments or argue about the benchmark: link `bench/RESULTS.md`, accept sample limits.
- Do not cross-post identical text; do not post the same day in r/academia/r/PhD (they are Day 2-4 posts).

---

## 4. Days 2-14: day-by-day

Each day: morning triage of issues (agent), record metrics, one primary content action, one outreach/list action, reply to all comments. Days 1-3 are the highest-traffic days; keep shipping fast fixes.

| Day | Primary content | Outreach / integrations | Notes |
|---|---|---|---|
| **T+1** | Post "what we learned from launch day" on X (honest: top bugs, one-line fixes, number of installs if you have it). Reddit r/PhD post. | Submit PRs to the two or three most relevant awesome-lists: awesome-claude-code, awesome-agent-skills (VoltAgent), and one research-tools list. Read each CONTRIBUTING first. | Fix any docs gaps from launch questions. Release v1.0.1 if needed. |
| **T+2** | Publish launch blog post on the docs site (canonical link for newsletters). | Email 5 personal outreach messages (statcheck/GRIM-aware researchers, 2 metascience groups, 2 newsletters) with the press kit. | Start the second-wave data job (below) in the background. |
| **T+3** | r/academia post (if allowed). Mastodon/Bluesky science posts with the benchmark funnel. | PRs to the remaining awesome-lists; submit to plugin directories/marketplaces that accept submissions. | |
| **T+4** | **Second-wave content #1: "We audited the references of N famous papers" (see 4.1).** X thread + blog. Use papers that are widely cited, and report only: reference counts, verified/unchecked, false flags found and fixed. | Share with AI-for-science newsletters and the people in the thread. | Only publish findings on well-known papers that come out clean, or where "not found" items turn out to be tool/registry gaps; say so. |
| **T+5** | Short video cut (60-90 s) on X, LinkedIn, YouTube Shorts/TikTok-style channels if the owner uses them. | Reply threads to people complaining about AI-hallucinated citations: offer the tool, once. | |
| **T+6** | Respond to every benchmark critique with a published methods note (`bench/METHODS.md`) if questions piled up. | Offer a pilot to 2 journal/conference contacts. | |
| **T+7** | **Weekly benchmark post #1:** a new small benchmark (e.g. "arXiv q-bio/stat papers: statcheck 2nd sample", or "reference existence in N random bib files from open GitHub repos" (owner-published only, no names)). Include false positives found. | Retro: compute stars/day by channel; decide on week-2 focus (section 6). | |
| **T+8** | Tutorial: "Add warrant to your paper's CI in 3 minutes" (GitHub Action + badge). Post on X/LinkedIn/dev.to. | Open PRs on a few **willing** open-source research repos to add the reference badge, only where maintainers invited or after opening an issue first. No unsolicited bulk PRs. | |
| **T+9** | "Codex/OpenCode users: how warrant works there" post for those communities. | Cross-link with adjacent project maintainers. | |
| **T+10** | Contributor spotlight: thank everyone who filed an issue/PR; merge 3-5 good-first-issues. | Update awesome-list PRs after maintainer feedback. | |
| **T+11** | Weekly benchmark post #2 or a "false positives we fixed this week" changelog thread (credibility content). | Newsletter follow-ups (one nudge each, max). | |
| **T+12** | Guest/podcast/livestream pitches: research-methods, open-science, AI-engineering podcasts; offer a live demo. | | Expect low yield; pitching costs little. |
| **T+13** | v1.1.0 release with the best requested features; short "what's new" post. | Re-submit to places that asked for a release or more maturity. | A second Show HN is not allowed to repost the same project in the short term (HN says minor releases generally don't qualify); only consider one later for a major new capability. |
| **T+14** | Retrospective: numbers, what worked, what to drop; plan weeks 3-8 (conference/journal outreach, workshops, paper). | | |

### 4.1 Second-wave content: "We audited N famous papers' references"
- Pick 15-30 famous, open, well-cited papers across ML, biomed and math where reference lists are available via Crossref/arXiv source.
- Run `warrant audit` and publish a table of: paper (well-known, no flagged errors in them), refs, verified, unchecked, not found, false flags. Manually check every "not found" and report what it was (tool bug, book chapter, preprint server gap, or genuinely unresolvable).
- Message to maintain: "references that exist, checked in under a minute each; here is where registries have gaps." Do not frame as "errors in famous papers" unless a real, hand-confirmed error exists, in which case notify the authors first and do not name them in the launch thread.
- Weekly benchmark posts after that use the same format: one dataset, one reproducible script, honest false positives.

### 4.2 Ongoing channel actions through day 14
- Reply within 24 hours to every issue and PR; label and close quickly; show merges publicly.
- Pin an issue "Share what warrant caught (and what it got wrong)". Real user stories, with consent, become social proof ("cited by", "used by") for the README.
- Add social proof to the README only when true: "#N on Hacker News" only if it happened; "used by X" only with permission.
- Weekly `v1.x` releases with changelogs keep the repo visibly alive.

---

## 5. Metrics to track (daily, in the spreadsheet)

| Metric | Where | Why |
|---|---|---|
| Stars total and delta/day | GitHub; star-history | Headline outcome. |
| Unique visitors and views | GitHub Traffic (14-day window; export daily) | Denominator for conversion. |
| Referrers (top 10) | GitHub Traffic, Referring sites | Which channels matter. Note: HN often shows as news.ycombinator.com, Reddit as reddit.com, X as t.co. |
| Visitor-to-star conversion | stars delta / unique visitors for that day | Quality of the README. A conversion in the low single-digit percent is plausible for a well-targeted audience; I have no sourced benchmark, so use your own day-to-day trend rather than an external target. |
| Clones and unique cloners | GitHub Traffic | Install interest (CI and bots inflate). |
| PyPI downloads | pypistats.org | Real installs (mirrors inflate). |
| Plugin installs | Marketplace stats if available | Real adoption. |
| Issues opened/closed; time to first response | GitHub | Health and credibility. |
| False-positive reports | issue label | The quality metric for the core claim. |
| Mentions and quotes | search X, HN, Reddit, Bluesky, newsletters daily | Social proof, outreach targets. |
| Contributors (first PRs) | GitHub | Community starts. |

Weekly review: for each channel compute posts, visitors, stars attributable, and effort hours. Double down on top 2 channels; stop the bottom 2.

Leading indicators on launch day: HN points and comments in the first hour; GitHub star velocity per hour; time-on-page can't be measured on GitHub, so use docs-site analytics (privacy-friendly: GoatCounter, Plausible, or none) if added.

---

## 6. Decision points if stalled

Checkpoints and what to do (decisions by the owner with the agent's data):

1. **T + 90 minutes on HN: no traction (few points, not on the Show HN list's visible part).**
   - Do: check the post is not marked dead or flagged (log out and look at /show), double-check the title and link are right. Reply to comments. Do not ask people to upvote and do not resubmit the same URL immediately.
   - Consider: the HN FAQ-style norm is that a post that did not get attention may be reposted after a while or with significant changes; check the current guidance at news.ycombinator.com/newsfaq.html before doing anything. Alternatively, accept the miss and move the energy to X, Reddit and the second-wave content, then try a different angle (the benchmark story) on another day. A different, substantive post is OK; a duplicate is not.
2. **End of T+1: under ~50 stars total.**
   - Diagnose: look at traffic and conversion. Low visitors = distribution problem (posts not reaching people). High visitors, low conversion = README/product problem (value not obvious or install friction). Fix the right one.
   - README fixes: tighten top fold, put the "before/after" higher, shorten the install, make the demo GIF load first.
3. **End of T+3: stars/day flat and under about 15/day with no growth.**
   - Switch to the second-wave content early (references audit of famous papers); the story "we checked X" travels better than "here is a tool."
   - Pitch the benchmark to metascience and research-integrity communities (the credibility audience), and to two or three newsletters with a custom note.
   - Ask 5 existing users for a one-sentence quote or a short testimonial with consent; add real social proof.
4. **End of T+7: under ~200 total.** Stop chasing the 1,000 target in the original window; re-plan. Realistic path: slower compounding via awesome-lists, PyPI discovery, GitHub Action badge adoption, conference/journal pilots, a short paper/preprint describing the method and benchmark (an arXiv/OSF preprint is a durable credibility asset), and a talk at a reproducibility meetup. Decide whether to keep a 30-day horizon.
5. **A false positive goes viral or an author objects.** Pause promotion, respond within hours, fix, publish the fix and a regression test, and thank the reporter. If an author of a paper is named by anyone, ask the namer to remove it and apologise publicly if warrant's output was misleading. Never defend a wrong flag.
6. **Rate limit or registry issue under load.** Post a status note in the README and Discussions; ship a patch increasing caching and backoff; contact the registry operator if their policy asks for it.
7. **A big breakout (e.g. over 300 stars in 24 hours).** Immediately: pin a "Start here" issue, triple-check install on clean machines, keep releases small, prepare to answer 5x more issues, post a thank-you with real numbers after 48 hours (not before), and line up the second-wave content a day earlier.

---

## 7. Do-not list (credibility guards)

- No bought stars or "growth service" stars; no fake accounts; no star-exchange groups; no asking people to upvote on HN or to mass-star in a group chat.
- No misleading screenshots, no cherry-picked outputs without saying so, no invented user counts or "trusted by" claims.
- No paper IDs from the benchmark, ever. No "name and shame" content.
- No unsolicited bulk PRs/issues to other repos.
- No overclaiming: "inconsistencies", not "errors/fraud"; "lead, not proof"; "2.8% of papers reporting tests", not "of papers".
- Every number in any post must appear in README.md or bench/RESULTS.md, or be freshly generated by a documented script committed to the repo.

---

## 8. Roles

- **Owner (human):** decisions marked [OWNER]; posting from personal accounts (HN, X, Reddit, LinkedIn); network seeding messages; talking to editors/researchers; legal/ethical calls; PyPI account; history-rewrite approval.
- **Agent (Codex):** README/doc fixes, packaging, tests, release notes, CI, asset scripts (GIFs via `docs/make_demo_gif.py` pattern), false-positive sweeps, metrics logging, issue triage and fixes, drafting posts from the templates (owner posts), second-wave benchmark jobs.
- Agent must not post on the owner's behalf to public channels, send emails, or publish to PyPI without the owner's explicit go-ahead on that action.

---

## 9. Sources

- Show HN rules: https://news.ycombinator.com/showhn.html
- HN guidelines (no soliciting upvotes/comments): https://news.ycombinator.com/newsguidelines.html
- HN FAQ (check before any resubmission): https://news.ycombinator.com/newsfaq.html (not fetched; read before use)
- Awesome-lists named in MARKETING.md section 6.1; read each CONTRIBUTING.md.
- Not verified: HN timing conventions, GitHub traffic retention of 14 days (stated from general knowledge of GitHub Insights; confirm in the UI), Thanksgiving date, conversion benchmarks (none cited on purpose).
