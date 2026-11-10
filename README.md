# warrant

**Keep research with Claude honest.** warrant is a Claude Code plugin that supervises research sessions:

1. **Holds the question.** Your research question stays in front of Claude every turn. Tangents get named instead of silently eating the session.
2. **Makes Claude show its evidence.** Every claim is bound to evidence: a run log, a citation, a proof. Plain code checks it, never a model. Wording has to match the evidence: "significantly better" on one seed gets flagged.
3. **Keeps a graveyard.** Ideas refuted by their own pre-registered predicate are buried. Claude is warned when it tries to bring one back.

Every claim ends up **green** (verified by code), **yellow** (unverified), or **red** (contradicted, tampered, or overstated).

## What a session looks like

```
$ warrant question "Does label smoothing help on our 5k-example setup?"
$ warrant claim "label smoothing significantly improves val acc"
claim #1
$ warrant evidence 1 --log runs/s0.log --metric val_acc=0.812
claim #1: red
  - says 'significant' but evidence has 1 seed(s), p=None

$ warrant claim "smoothing 0.1 beats baseline"
$ warrant predict 2 '{"metric":"val_acc","op":"le","of":"baseline"}'   # before running
$ warrant result 2 --observed val_acc=0.806 --baseline val_acc=0.809
claim #2: refuted                                                      # buried in the graveyard
```

When Claude finishes a reply containing numbers that no recorded run produced, the Stop hook blocks it:

```
[warrant] These numbers in your reply do not trace to any recorded evidence: 0.835.
```

## Why code, not a model

Research agents grade their own homework. 2026 studies of autonomous research agents found they game their own evaluations on a large share of research tasks, and telling them the rules does not reliably stop them. warrant takes the verdict away from the model:

- **Pre-registration.** A refutation predicate is committed before results exist. A missing metric is `inconclusive`, never a silent pass.
- **Hashed evidence.** Logs are hashed when attached. Editing a log afterwards turns the claim red. Reported metrics must literally appear in the log.
- **Append-only record.** `.warrant/record.db` is a hash chain. Rewriting history is detected.
- **Zero dependencies.** Python stdlib only. No API key, no network.

## Install

As a Claude Code plugin:

```
/plugin marketplace add <owner>/warrant
/plugin install warrant@warrant
```

The CLI, for using it by hand or in CI:

```
pip install warrant-research
```

Hooks do nothing until you run `warrant question` in a project. It is quiet by default.

## Commands

| command | does |
|---|---|
| `warrant question TEXT [--hypothesis H]` | set the research question |
| `warrant claim TEXT` | record a claim (warns if it resembles a dead idea) |
| `warrant evidence N --log F --metric k=v [--seeds S --p P --std D]` | attach run evidence |
| `warrant evidence N --type cite --ref DOI --quote "..."` | attach a citation (checker coming) |
| `warrant predict N JSON` | pre-register a refutation predicate |
| `warrant result N --observed k=v [--baseline k=v]` | code decides supported / refuted / inconclusive |
| `warrant kill IDEA --why W` / `warrant retract N` | bury an idea / withdraw a claim |
| `warrant status` / `warrant report -o REPORT.md` | every claim with its status and reasons |
| `warrant trace DRAFT.md` | list numbers in a draft that no evidence accounts for |

## Roadmap

- Citation checker: resolve DOI/arXiv and match the quote in the source text.
- Proof receipts: Lean 4 / SymPy.
- Drift detection beyond the question anchor.
- HTML report and dashboard.

## License

MIT
