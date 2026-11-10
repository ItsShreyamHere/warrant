---
name: warrant
description: Use during any research session (ML/CS experiments, science, data analysis, mathematics) to keep claims honest. Record the research question, record each substantive claim, attach the evidence that produced it (run logs, citations, proofs), pre-register refutation predicates before experiments, and let code decide verdicts. Use when the user starts a research question, runs an experiment, reports a result or number, or writes up findings.
---

# warrant

`warrant` keeps a hash-chained record in `.warrant/` of the research question, every claim, its evidence, and refuted ideas (the graveyard). Verdicts and checks are plain code; you never grade your own claims.

If `warrant` is not on PATH, use `python "<plugin root>/bin/warrant.py"` or ask the user to `pip install warrant-research`.

## Workflow

1. **Set the question once** at the start of a research task:
   `warrant question "Does label smoothing help on our 5k-example setup?" --hypothesis "smoothing 0.1 improves val acc"`
2. **Before running an experiment, pre-register** what would refute the claim. Do this before you see results:
   ```
   warrant claim "label smoothing 0.1 improves val acc over baseline"      # -> claim #N
   warrant predict N '{"metric":"val_acc","op":"le","of":"baseline"}'
   ```
3. **After the run, record the result.** Code decides `supported` / `refuted` / `inconclusive`. Refuted ideas go to the graveyard automatically.
   `warrant result N --observed val_acc=0.812 --baseline val_acc=0.809`
4. **Attach evidence for every number you report.** The log is hashed. Metrics must literally appear in it.
   `warrant evidence N --type run --log runs/seed0-2.log --metric val_acc=0.812 --seeds 3 --std 0.011`
   Citations: `--type cite --ref 10.xxxx/yyy --quote "exact sentence"`. Proofs: `--type proof --ref proof.lean`.
5. **Before writing up**, run `warrant status` and fix every `XX` (red) claim. Then run `warrant report -o REPORT.md`.

## Rules

- Never state a number in your reply that is not in recorded evidence. The Stop hook will block you and list the untraced numbers.
- Wording must match evidence. "significant" needs >=3 seeds and p<0.05. "outperforms"/"improves" needs >=3 seeds or a supported pre-registered predicate. "proves" needs proof evidence. If evidence is weak, say so plainly. If evidence is strong, do not hedge it away.
- Do not re-propose a graveyard idea unless you pre-register what new result would justify it. `warrant claim` warns you when an idea resembles a dead one.
- Work that does not serve the recorded question is a tangent. Say so and ask the user before pursuing it, or set a new question.
- Never edit `.warrant/` by hand. The hash chain detects it.
