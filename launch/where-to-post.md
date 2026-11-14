# Where to list or submit warrant (non-social-media)

Researched 2026-11-14. "Verified: yes" = I fetched the primary page or GitHub API in this session and the place is live. "unverified" = found only via search snippets, or existence not confirmed; do not rely on it without checking. Star counts are GitHub API values on 2026-11-14.

Important context: the warrant repo was created 2026-11-10 and has 8 stars (GitHub API). Many lists gate on age or stars, so timing matters. Gates are noted per row. Do not submit to a list before it clears its gate; most auto-close or reject.

Self-promo rule of thumb that holds almost everywhere: write a neutral description of what the tool does, not a sales pitch.

---

## 1. Agent plugin / skill marketplaces and directories

| Name | Link / how to submit | Fit | Rules / notes | Verified |
|---|---|---|---|---|
| Anthropic plugin directory (official) | Developer portal https://claude.ai/directory/manage -> Submit new -> Plugin bundle. Source = GitHub repo URL; click Validate; fill listing details, data-handling questions, 4 acknowledgements; Submit for review. Docs: https://claude.com/docs/plugins/submit.md | High | Needs a paid Claude plan/role that can submit (see https://claude.com/docs/directory/publish.md). Repo may be private while validating, must be public before go-live. Run `claude plugin validate ./<folder>` first. Security scan plus possible human review; reviewer publishes the first version by default. Max 10 submissions per org per 24h. PRs to anthropics/claude-plugins-official (47,259 stars) are NOT monitored. Review time not stated in docs. Must comply with Anthropic Software Directory Policy/Terms. | yes |
| OpenAI plugin directory (ChatGPT and Codex share one catalog) | https://platform.openai.com/plugins -> "Upload new or existing plugin" (ZIP). Docs: https://developers.openai.com/plugins/deploy/submission ; guidelines https://developers.openai.com/plugins/plugin-guidelines | Medium-High | Org owner or member with "Apps Management Write"; publisher identity must be verified (individual or business). Skills-only plugins use the same flow without MCP test cases; docs do not explicitly say skills-only plugins get listed publicly, so confirm. Plugins with `apps`/`.app.json` or lifecycle hooks cannot be submitted currently (warrant ships `hooks/`: check this blocks it). Review by email feedback; time not stated. Browse in the Plugins tab of ChatGPT. | yes (flow); acceptance of skills-only unverified |
| Codex via git marketplace (no review) | Users run `codex plugin marketplace add <repo>`; repo carries `.agents/plugins/marketplace.json` (warrant repo already has `.agents/`) | High | Self-distribution, no gatekeeper. Source: third-party blog, not OpenAI docs. | unverified (mechanism); `.agents/` dir exists in repo |
| claudepluginhub.com | https://www.claudepluginhub.com/tools/submit-plugin ; auto-discovers GitHub repos with `.claude-plugin/plugin.json`; claim ownership via GitHub sign-in at /tools/claim | High | Free as far as shown. Site says new repos can take days to appear; submitting the URL is faster. Claims 117,772 indexed plugins (their figure, unverified). | yes |
| claudemarketplaces.com | Crawl-based (GitHub marketplace schema, skills.sh, MCP registries). Editor reviews borderline listings. Contact hi@claudemarketplaces.com. Site nav has a "Submit" link (form details not seen). | High | Independent, not Anthropic. Needs a valid `marketplace.json` in a public repo to be crawled. | yes (site); submit form unverified |
| skills.sh (Vercel) | No submit form. Listing is driven by installs of `npx skills add <owner/repo>`; source https://github.com/vercel-labs/skills | High | Leaderboard by install count (All Time / Trending 24h / Hot). Share the install command; installs get it onto the board. Mechanics of counting not documented. | yes (site); mechanics unverified |
| Tessl registry | https://tessl.io/registry ; web "Optimize it with Tessl" flow: point at GitHub repo or paste skill; evals run and score you | Medium | Cost not stated on page. CLI examples shown are install/search only. | yes (page); cost unverified |
| aitmpl.com (Claude Code Templates) | PR to https://github.com/davila7/claude-code-templates ; docs https://docs.aitmpl.com | Medium | Site says components are open-source, PR-contributed. Details not read. | partly (docs not read) |
| ClaudSkills.com | https://claudskills.com ("Submit" -> homepage `#submit`) | Low-Med | Open SKILL.md registry; intake rules not seen. | unverified (form) |
| skillsmp.com | https://skillsmp.com | Low-Med | Returned 403 to my fetch; surfaced in search as a skills index. Indexing rules unknown. | unverified |
| OpenCode official ecosystem page | PR per https://opencode.ai/docs/ecosystem/ ("Submit a PR") to github.com/anomalyco/opencode docs | High | Page says submit a PR for OpenCode-related projects. | yes |
| opencode.cafe | Linked from the official ecosystem page as a community aggregator | Medium | Submission method not checked. | unverified |
| awesome-opencode registry (see Section 2) | PR with one YAML file | High | See below. | yes |
| MCP registry (modelcontextprotocol/registry, 7,465 stars) | https://github.com/modelcontextprotocol/registry | Low | Only relevant if warrant exposes an MCP server. It is a CLI and plugin; skip unless an MCP server exists. | yes (exists) |
| punkpeye/awesome-mcp-servers (97,691 stars) | PR to README | Low | Only for MCP servers with public repo. Skip unless MCP server shipped. | yes |

---

## 2. GitHub awesome-lists

| Name (stars on 2026-11-14) | How to submit | Fit | Gate / rules | Verified |
|---|---|---|---|---|
| hesreallyhim/awesome-claude-code (57,975; pushed today) | Issue form ONLY: https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml . No PRs, not via `gh` CLI; must be filled by a human in web UI. | High | Resource must be >=14 days since first commit on default branch AND show continued commits, OR have >=100 stars. One resource at a time per person. One-line neutral description, no emojis, no sales tone, no addressing the reader. Needs recognised LICENSE file. Best effort review, no response guaranteed. Maintainer says get users first. Warrant repo created 2026-11-10 so earliest clean date is about 2026-11-24 (first-commit date not checked). | yes |
| awesome-opencode/awesome-opencode (10,984; pushed yesterday) | PR adding one YAML file under `data/plugins/` or `data/projects/` (fields: name, repo, tagline <=120 chars, description, optional min_version). Do not edit README. https://github.com/awesome-opencode/awesome-opencode | High | Rules: OpenCode must be a real documented target with setup docs, repo >=25 stars, >=30 days old, commit in last 90 days, not a duplicate. State supported OpenCode major versions (V1/V2) in the description. PR failing any rule is closed. Warrant is not eligible until about 2026-12-10 and needs 25 stars. | yes |
| VoltAgent/awesome-agent-skills (37,172) | PR: one README line `- **[author/skill-name](url)** - <=10-word description` under a Community Skills subcategory (e.g. "AI and Data" or "Other"); PR title `Add skill: author/skill-name` | Medium-High | Needs real community usage; brand-new skills not accepted. Short description. Likely too early for warrant. | yes |
| hashgraph-online/awesome-codex-plugins (1,574; pushed today) | PR adding one line to README; a generator mirrors the plugin bundle from your repo. Centralised HOL plugin scanner runs on each submission (min score 75 shown in their sample CI). https://github.com/hashgraph-online/awesome-codex-plugins | High | Read full CONTRIBUTING.md first. Active. Gate on stars/age not seen. | yes |
| composio-community/awesome-claude-plugins (1,994) and quemsah/awesome-claude-plugins (1,609) | PR (no CONTRIBUTING file found via API) | Medium | Small, active; rules unknown. | partly (exist, active; rules unverified) |
| ComposioHQ/awesome-claude-skills (79,472; last push 2026-09-18) | PR with a skill folder + SKILL.md per CONTRIBUTING | Medium | Biggest by stars but last push was two months ago; check it still merges. Must be a real use case, tested, with examples. | yes (rules); activity stale-ish |
| sickn33/agentic-awesome-skills (49,688) | PR with focused skill, gap vs existing skills, one usable example | Low-Med | Skill repository, not a pure link list. | yes |
| heilcheng/awesome-agent-skills (6,389) | PR (per README; CONTRIBUTING not read) | Medium | | unverified (rules) |
| travisvn/awesome-claude-skills (15,816; last push 2026-04-28) | PR | Low | Appears dormant since April. | yes (stale) |
| kael-odin/awesome-academic-research-skills (210; pushed today) | Issue template "recommend repo" (Chinese-language CONTRIBUTING) at https://github.com/kael-odin/awesome-academic-research-skills | High (topic fit) | Requires >=100 stars by default; no forks/archived; must serve academic/research/paper/peer-review use and show Skill/Claude Code/Codex/OpenCode signals. Not eligible at 8 stars. | yes |
| LimHyungTae/awesome-claudecode-paper-proofreading (438; pushed 2026-10-20) | Open an issue or PR (no CONTRIBUTING found) | High (topic) | Paper-proofreading oriented; warrant's referee/citation check fits. Rules unverified. | partly |
| webfuse-com/awesome-autoresearch (2,591), yibie/awesome-autoresearch (795), WecoAI/awesome-autoresearch (1,077) | PR per their CONTRIBUTING | Low-Med | Scope is Karpathy-autoresearch-style loops; only add if warrant explicitly cites autoresearch. Do not pad. | yes (rules); fit conditional |
| leipzig/awesome-reproducible-research (414; pushed yesterday) | PR (no CONTRIBUTING file via API); also indexed by FORRT | Med-High | Case studies, projects, tools for reproducible research. Warrant's "every number traces to a run" fits. | yes (exists/active); rules unverified |
| INRIA / ASSERT-KTH awesome-open-science-software (164; pushed 2026-10-29) | PR | Low-Med | Focus on software that supports open science. | yes (exists) |
| vinta/awesome-python (334,670; pushed yesterday) | PR per CONTRIBUTING | Low now | Requires production-ready (not alpha/beta), >=1 month old, active, documented; use-case caps of 5 per subcategory with displacement rule. v0.9.0 and a 4-day-old repo will likely fail the "stable" and "established" tests. Revisit after v1.0. | yes |
| josephmisiti/awesome-machine-learning (74,822) | PR | Low | No CONTRIBUTING fetched; pure ML libraries list. | unverified (rules) |
| punkpeye/awesome-mcp-servers (97,691) | see Section 1 | Low | MCP only | yes |
| awesome-metascience | No substantive list exists. Search found pawljmlo/awesome-metascience: 1 star, last push 2024-04-02 (dead). | n/a | Do not bother. Option: propose entry to FORRT curated resources instead (see Section 5). | yes (absence) |
| awesome-research-integrity / citation-integrity lists | Only 0-2 star repos surfaced. | n/a | Ignore. | yes (absence) |
| KarelDO/awesome-codex (206; last push 2023) | dead | n/a | Skip. | yes |

---

## 3. Launch / product directories

| Name | Link / how to submit | Fit | Rules / notes | Verified |
|---|---|---|---|---|
| Product Hunt | https://www.producthunt.com ; launch guide https://help.producthunt.com/en/collections/19793093-launch-guide | Medium | Open-source dev tools are common there but audience skews consumer/maker; the guide's actual rules (eligibility, scheduling, what to avoid) were not readable in my fetch. hello@producthunt.com for questions. This is a personal-account launch so overlaps the owner's own posting; list for completeness. | yes (exists); rules unverified |
| DevHunt | https://devhunt.org ("Submit", login first) | High | Dev-tool launchpad, weekly voting; shows 7,556 tools and 47,313 developers (site's own stats). Submission free status not stated; paid ad slots exist ($199/$99 per week). Active on 2026-11-14. | yes |
| Uneed | https://uneed.best ("Submit a product") | Low-Med | Free launch goes through a queue and needs launch-day upvotes to keep its backlink; paid fast-track exists. Generic product site. | yes |
| AlternativeTo | https://alternativeto.net (sign in with GitHub/Google/Apple, then add software) | Low-Med | Needs a named incumbent to be "alternative to" (e.g. statcheck, GRIM tools). Weak fit; submission steps not shown. | yes (login page); fit/steps unverified |
| There's An AI For That | https://theresanaiforthat.com/submit/ | Low | 403 to my fetch; paid/queue model likely. Audience is consumer AI tools. | unverified |
| Futurepedia | futurepedia.io | Low | Not checked. Consumer AI tool directory. | unverified |
| Lobsters | https://lobste.rs/about | Medium | Invite only. New accounts (first 70 days) cannot submit self-promo; self-promo should be under about a quarter of your stories/comments over the last year. Need an invite from an established member. | yes |
| Changelog News | https://changelog.com/news/submit (signed-in; URL + title + "What's interesting about it?") | Medium-High | Own work allowed. Excludes tutorials and commercial products. Explain why it is newsworthy. | yes |

---

## 4. Newsletters that accept submissions

| Name | Submission method | Fit | Rules / notes | Verified |
|---|---|---|---|---|
| PyCoder's Weekly | https://pycoders.com/submit (Google Form behind "Submit Your Link") | Medium-High | Accepts projects, articles, conferences. No guarantee of inclusion. No other rules shown. | yes |
| Python Bytes (podcast + newsletter) | Email contact@pythonbytes.fm with the item. Episode #504 dated 2026-11-10, so active. | Medium | Informal; send a 2-3 line pitch with link. | yes |
| Changelog News | see Section 3 | Med-High | | yes |
| Last Week in AI | contact@lastweekinai.com (also hello@gladstone.ai); no form | Low-Med | Address is for "questions and feedback"; news-tip use not stated. Covers major AI news; a v0.9 research tool is unlikely to fit. | yes (email); fit low |
| TLDR (AI / Dev) | No editorial submission found; only advertise.tldr.tech (paid). | Low | Paid only as far as I could find. | yes (no free route found) |
| Python Weekly (pythonweekly.com) | No submission path found on the site | Low | Maybe by replying to the newsletter email; unverified. | unverified |
| Console.dev | Reviews devtools; no submission method found on homepage; check https://console.dev/about | Medium | Unknown. | unverified |
| Retraction Watch (Weekend Reads / tips) | Contact via site; tip link is inside Weekend Reads posts; editor email obfuscated on the About page | Medium (audience) | They cover misconduct stories, not tools. Do not pitch accusations from your 6-paper benchmark; at most pitch the method after the preprint exists. | partly |
| Import AI, Ahead of AI, The Batch, Latent Space | No public submission path found (Import AI page showed nothing) | Low | Single-author editorial; cold email only. | unverified |

---

## 5. Research / academic communities (non-social)

| Name | Link / method | Fit | Rules / notes | Verified |
|---|---|---|---|---|
| JOSS (Journal of Open Source Software) | https://joss.readthedocs.io/en/latest/submitting.html | High (credibility) | Free. Repo must be public >6 months with sustained commits (not a few days); OSI license; evidence of research use; thin wrappers rejected; AI-use disclosure statement mandatory. Warrant cannot qualify before about May 2027. Plan toward it. | yes |
| pyOpenSci peer review | https://github.com/pyopensci/software-submission ; intro https://www.pyopensci.org/software-peer-review/about/intro.html | Medium | Volunteer review for scientific Python packages; scope page not read. Warrant is a plugin+CLI so scope fit uncertain. | yes (exists); scope unverified |
| FORRT curated resources | https://forrt.org/curated_resources/ (contribution page 404 on /contribute/) ; find the current route via forrt.org | Medium-High | Indexes reproducibility resources (it lists leipzig awesome-reproducible-research). Submission route not confirmed. | partly |
| ReproducibiliTea | Email reproducibilitea@gmail.com ; https://reproducibilitea.org ; Speaker Swaps and Resources pages exist | Medium-High | Site active, "Conference 2026" page exists. Email for a talk/resource listing; local journal clubs could use warrant for a session. | yes |
| COS / OSF | contact@cos.io ; OSF Preprints / registrations (hosting a methods write-up or MetaArXiv preprint is free) | Medium | No tool-submission process on COS contact page. Best use: post a methods preprint on OSF/MetaArXiv and link the repo. | yes (contacts); preprint route standard but unchecked |
| PubPeer | https://pubpeer.com ; policies page lists rules for comments, plugin, API and "automated or tool-generated comments" | Low (do not post) | A PubPeer policy exists on automated/tool-generated comments and accusations; read it before any use. Do NOT post warrant output about named papers. Use only as a reader. Policy text not retrieved. | yes (exists); policy text unverified |
| SIPS (Society for Improvement of Psychological Science) | Annual conference with hackathon/unconference format; site not fetched | Medium | Next-conference call and dates unverified. | unverified |
| Metascience conference / community | metascience.org did not resolve in my fetch | Medium | Check the 2026/2027 call for posters/demos. | unverified |
| Hugging Face Spaces (demo) | https://huggingface.co/spaces -> Create new Space | Medium-High | Static Spaces are free for everyone. Gradio and Docker Spaces need a paid plan (PRO) except 2 free ZeroGPU Gradio Spaces on free accounts. A static HTML demo (pasted-report viewer) is free. Can request a community GPU grant. | yes |
| Papers with Code | Not checked; I found no confirmation of its status in 2026. | n/a | Do not rely. Use HF Papers/Spaces instead. | unverified |
| Kaggle | not checked | Low | A Kaggle notebook demo is possible but low value. | unverified |

---

## 6. Developer communities / forums

| Name | Link / method | Fit | Rules / notes | Verified |
|---|---|---|---|---|
| Claude Developers Discord | https://discord.com/invite/6PPFFzqPDZ (linked from https://www.claude.com/community) | High | Official page describes it as real-time help and project sharing. Check channel rules on joining; self-promo rules unverified. | yes (listed on official page); rules unverified |
| Claude "Submit your build" form | Typeform https://form.typeform.com/to/VIUAjxNi ; terms https://support.claude.com/en/articles/15485501-submit-your-build-how-it-works-and-what-you-re-agreeing-to | Medium-High | Official; submission makes a project eligible for a feature on Claude's social or marketing channels. Read the terms (what you agree to) first. | yes |
| r/ClaudeAI project showcases | https://www.reddit.com/r/ClaudeAI/ | n/a | Reddit: owner posts himself, listed only because the official page points to it. | yes |
| Claude Community events | https://luma.com/claudecommunity ; Ambassadors program https://www.anthropic.com/community/ambassadors | Medium | Local meetups; possible lightning demo slot. Not verified that demos are accepted. | yes (exists) |
| OpenAI developer community forum | https://community.openai.com ; categories Codex (/c/codex/37, 1,456 topics) and Community (/c/community/21, 5,020 topics, description invites sharing your own projects) | Medium | No dedicated showcase; post in Community. Recency of activity not confirmed. | yes (exists) |
| OpenCode: GitHub Discussions and Discord | GitHub https://github.com/anomalyco/opencode ; ecosystem page lists the community | Medium | A third-party mirror says the ecosystem page lists a Discord; the official page text I read did not. Check Discussions tab for a Show and tell category. | unverified |
| discuss.python.org | https://discuss.python.org/categories | Low | There is NO show-and-tell category (categories: Python Help, Ideas, Packaging, Developer Tools, etc.). Do not post promos in Packaging/Ideas. | yes (absence) |
| dev.to | https://dev.to , tag #showdev | Medium | Guidelines URL 404ed in my fetch. #showdev is the normal tag for project posts; rules unverified. | unverified |
| Hashnode | https://hashnode.com | Low-Med | Not checked. | unverified |
| Towards Data Science | https://towardsdatascience.com/submission-guidelines/ (403 to my fetch). Search snippets: submit via site form, editors review usually within a week, authors paid via program. | Medium | Requires an original practitioner article, not a product announcement. Snippet-sourced. | unverified |
| Medium publications | n/a | Low | Not checked. | unverified |

---

## 7. Other high-leverage ideas

| Item | How | Fit | Notes | Verified |
|---|---|---|---|---|
| GitHub topics + Zenodo DOI + CITATION.cff | Warrant repo already has topics: agent-skills, claude-code, codex, opencode, metascience, peer-review, reproducibility, statcheck, etc. Add Zenodo release archive (DOI) and a `CITATION.cff` | High | Makes it citeable by researchers and strengthens later JOSS case. Topics verified via API; Zenodo/CITATION.cff not checked in repo. | topics yes; rest unverified |
| Package registries | Publish to PyPI (and a GitHub Action in Marketplace; repo has `action.yml`) | Med-High | `action.yml` exists, so GitHub Actions Marketplace listing is possible. Not verified whether already published. | partly |
| Python Bytes / Changelog (podcasts) | See Sections 3-4 | Medium | Python Bytes email route verified. Talk Python: no guest-pitch path visible on the guests page. | yes / unverified |
| University research-software groups | Email research-software engineering groups or journal-club organisers (e.g. ReproducibiliTea clubs) | Medium | No specific group verified; build a list by hand. | unverified |

---

## Timing constraints summary (from verified rules)

- awesome-claude-code: 14 days since first commit plus ongoing commits (or 100 stars). Earliest about 2026-11-24 (repo created 2026-11-10).
- awesome-opencode: 25 stars and 30 days: about 2026-12-10 and needs stars.
- awesome-academic-research-skills: 100 stars.
- VoltAgent awesome-agent-skills: needs proven community usage.
- awesome-python: not alpha/beta, 1 month old; revisit after 1.0.
- JOSS: more than 6 months of public development: about May 2027.
- Anthropic directory: no age gate stated; needs paid plan. Do this first.

---

## Top 15, in order

1. Anthropic plugin directory (claude.ai/directory/manage): official, no age gate stated, reaches Claude Code and Claude users directly.
2. claudepluginhub.com submit page: free, works from the existing `.claude-plugin/plugin.json`, listed within days.
3. claudemarketplaces.com / skills.sh: crawl-based; get listed by having a valid marketplace file and sharing the `npx skills add ItsShreyamHere/warrant` install line (verify the exact skill path first).
4. OpenAI Codex/ChatGPT directory (platform.openai.com/plugins): the only official Codex listing path; confirm the hooks restriction first.
5. hashgraph-online/awesome-codex-plugins: active (pushed today), single-line PR, Codex-specific.
6. awesome-claude-code (issue form, from about 2026-11-24): biggest Claude Code list (57,975 stars), strict rules but a clear path.
7. OpenCode official ecosystem page (PR to anomalyco/opencode docs): no stars gate stated, direct to OpenCode users.
8. Claude Developers Discord plus "Submit your build" form: official channels for project sharing and possible feature.
9. awesome-opencode (about 2026-12-10, 25 stars): 10,984 stars, well-defined YAML PR.
10. Changelog News: accepts own work, developers, one form; needs a "why newsworthy" angle (the 6-contradictions benchmark).
11. PyCoder's Weekly: one form, Python audience, no cost.
12. Hugging Face static Space demo: free hosting for a try-it-without-installing demo that every other listing can link to.
13. DevHunt: active dev-tool launchpad, submit after the demo exists.
14. ReproducibiliTea (email) and FORRT: reach the reproducibility community that cares about statcheck/GRIM-style checks.
15. awesome-reproducible-research (leipzig) plus kael-odin/awesome-academic-research-skills and awesome-claudecode-paper-proofreading: topical fit; the latter needs 100 stars. Longer horizon: JOSS (about May 2027) and Zenodo DOI.

---

## Ready-to-paste descriptions (accurate claims only)

One-line (about 150 chars):

> warrant: open-source (MIT, Python stdlib) plugin and CLI for Claude Code, Codex and OpenCode that checks every reported number, citation and p-value against real runs and sources.

Alternative one-line (shorter, 115 chars):

> The referee that reads every paper you cite: code-verified numbers, citations and statistics for AI research agents.

Three-line:

> warrant is an MIT-licensed, Python-stdlib plugin for Claude Code, OpenAI Codex and OpenCode, plus a CLI, that keeps AI-assisted research honest: every number an agent reports must trace to a real run, and citations are resolved against doi.org, arXiv, OpenAlex and Crossref and quote-checked against the cited paper's full text.
> `warrant review` produces referee reports; built-in statcheck recomputes p-values and GRIM tests reported means; `warrant watch` runs zero-token sentinels on live ML training logs for NaN, divergence, overfitting and leakage.
> Benchmark: 2,063 p-values across 851 open-access psychology papers, finding 6 papers whose own statistics contradict their significance claims (hand-verified, anonymised). Repo: https://github.com/ItsShreyamHere/warrant (v0.9.0).

Short tagline for tag-limited forms: "Code-verified research for AI agents: numbers traced to runs, citations quote-checked, statistics recomputed."

Caution on claims: do not say "stable", "widely used" or give star counts; repo is 4 days old with 8 stars. Do not name any of the 6 papers. If a directory asks for supported agents, list Claude Code, Codex, OpenCode only.
