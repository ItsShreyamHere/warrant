---
name: warrant
description: Use during any research session (ML/CS experiments, science, data analysis, mathematics) to keep claims honest. Set the research question, pre-register what would refute a claim before running experiments, attach evidence, and let code decide verdicts. Use when the user starts a research question, plans or runs an experiment, reports results, cites papers, or writes up findings.
---

# warrant

warrant supervises research sessions. Once a project has a `.warrant/` folder (`warrant init`), hooks run on their own:

- **Every tool output is captured.** Command output, files read and the user's prompts become the evidence pool, with a hash for each.
- **Before you finish a reply, the Stop hook checks it.** Each decimal or percentage in your final reply must trace to something that actually ran or was read, within rounding. It may also be a difference, ratio or mean of traced values. DOIs, arXiv ids and quoted paper titles are looked up in Crossref, arXiv and OpenAlex. Untraced numbers and fake citations block the reply once, and you must fix them.
- **The question stays in view.** It is shown each turn, and refuted ideas are shown at session start.

Text you write with Write or Edit is never evidence. Neither is a file you wrote and then read back.

If `warrant` is not on PATH, use `python "<plugin root>/bin/warrant.py"`.

## Workflow

1. **Set the question** at the start of a research task:
   `warrant question "Does label smoothing help on our 5k-example setup?" --hypothesis "smoothing 0.1 improves val acc"`
2. **Pre-register before running.** Record the claim and what would refute it, before you see results:
   ```
   warrant claim "label smoothing 0.1 improves val acc over baseline"      # -> claim #N
   warrant predict N '{"metric":"val_acc","op":"le","of":"baseline"}'
   ```
3. **Run the experiment for real**, then record the result. Code decides supported / refuted / inconclusive. Refuted ideas go to the graveyard.
   `warrant result N --observed val_acc=0.812 --baseline val_acc=0.809`
4. **Attach evidence to important claims.** Logs are hashed, and metrics must appear in them.
   `warrant evidence N --type run --log runs/seeds.log --metric val_acc=0.812 --seeds 3 --std 0.011`
   `warrant evidence N --type cite --ref 1706.03762 --quote "exact sentence"`
5. **Before writing up**, run `warrant status`. Fix every `XX`. Then check the draft:
   `warrant trace draft.md`, `warrant cites draft.md` (or `refs.bib`), `warrant report --html`.

## Rules

- **Never report a number you did not get from a run, a file, or the user.** If it is an estimate, write `~` before it.
- **Wording must match evidence.**
  - "significant" needs >=3 seeds and p<0.05.
  - "outperforms" or "improves" needs >=3 seeds or a supported pre-registered predicate.
  - "proves" needs proof evidence.
  - Weak evidence gets plain wording. Strong evidence must not be hedged away.
- **Do not re-propose a graveyard idea** without pre-registering what new result would justify it.
- **Work that does not serve the recorded question is a tangent.** Say so and ask before pursuing it.
- **Never edit `.warrant/` or logs attached as evidence.** Hashes detect it, and the claim turns red.
