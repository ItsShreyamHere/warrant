# warrant

**Claude can't make up numbers or citations in your research anymore.**

## Try it on any paper first: 10 seconds, no setup

```
pip install warrant-research
warrant audit 1706.03762          # any arXiv id or URL, or your own refs.bib / paper.bbl
```

```
XX  [fake1] Recursive Spectral Gating Improves Long-Context Retrieval in Sparse Mixture Transformers
      no work with this title in OpenAlex or Crossref
XX  [fake2] Attention is all you need
      identifier does not exist (the title is real)

3 references: 1 verified, 0 unchecked, 2 not found anywhere
```

That's a real run on a test `.bib` with two planted fakes.

Every reference is checked against doi.org, arXiv, OpenAlex and Crossref. The paper's LaTeX source is read in memory and never unpacked to disk. "Not found" means no registry knows the work: check those by hand before accusing anyone. Run it on your own paper before a reviewer does.

### In CI, for every paper repo

```yaml
# .github/workflows/references.yml
on: [push, pull_request]
jobs:
  references:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: <owner>/warrant@v0
        with:
          files: refs.bib
```

## Then keep it from happening in your own work

warrant is a Claude Code plugin that supervises research sessions. Install it, run `warrant init`, and keep working. From then on:

- **Every number Claude reports must come from something that actually ran.** Hooks capture each command output and file Claude reads. Before a reply finishes, every decimal and percentage in it is traced back to its source, within rounding, or to a difference, ratio or mean of traced values. Untraced numbers block the reply.
- **Every citation is looked up.** DOIs, arXiv ids and quoted paper titles are checked against Crossref, arXiv and OpenAlex. A fake DOI, a real id attached to the wrong paper, or a title that doesn't exist blocks the reply.
- **Your question stays in view.** The research question rides along every turn. Ideas refuted by their own pre-registered test go to a graveyard, and Claude is warned when it tries to bring one back.
- **Claims must match their evidence.** "Significantly better" on one seed is flagged. "Proves" with no proof is flagged. Strong results hedged into mush get a note.

Code does every check, never a model. It has no dependencies and needs no API key.

```
Claude: Smoothing improves validation accuracy to 0.874 (vs 0.809 baseline),
        consistent with Müller et al. (doi 10.48550/arXiv.1906.99999).

[warrant] Your reply has numbers that no command output, file, or record entry
produced: 0.874 and citations that do not resolve or do not match:
doi:10.48550/arXiv.1906.99999 (DOI does not exist). Run the command that produces
each number, fix or remove the citation, or label a number as an estimate with '~'.
```

## Why code, not a model

Research agents grade their own homework. 2026 studies of autonomous research agents found they game their own evaluations on a large share of research tasks. Telling them the rules does not reliably stop them. A second model checking the first has the same problem. warrant takes the verdict away from the model:

- **Provenance, not plausibility.** A number is either in a captured tool output or it isn't. Text Claude writes, or writes and reads back, never counts as evidence.
- **Pre-registration.** A refutation predicate is committed before results exist. A missing metric gives `inconclusive`, never a silent pass.
- **Tamper-evident.** Every captured output and attached log is hashed. `.warrant/record.db` is a hash chain, so editing history or a log afterwards is detected.
- **Quiet by default.** Hooks do nothing until `warrant init`. Code blocks, versions, dates, section numbers and `~estimates` are ignored. Plain whole numbers are only traced with `WARRANT_STRICT=1`. Each reply is blocked at most once.

## Install

As a Claude Code plugin:

```
/plugin marketplace add <owner>/warrant
/plugin install warrant@warrant
```

Then, in a research project:

```
pip install warrant-research     # the CLI; hooks work without it
warrant init "Does label smoothing help on our 5k-example setup?"
```

Needs Python 3.10+. Works on macOS, Linux and Windows.

## Check any draft, even one not written with Claude

```
warrant cites paper.md        # or refs.bib: every DOI / arXiv id / title resolved
warrant trace paper.md --all  # where each number came from, and which came from nowhere
warrant report --html         # every claim, verdict, graveyard, integrity check
```

## Pre-registered experiments

```
$ warrant claim "label smoothing 0.1 improves val acc over baseline"
claim #1
$ warrant predict 1 '{"metric":"val_acc","op":"le","of":"baseline"}'   # before running
$ warrant result 1 --observed val_acc=0.806 --baseline val_acc=0.809
claim #1: refuted                                                      # -> graveyard
```

## Commands

| command | does |
|---|---|
| `warrant init [QUESTION]` | turn warrant on for this project |
| `warrant question TEXT [--hypothesis H]` | set or change the research question |
| `warrant claim TEXT` | record a claim (warns if it resembles a dead idea) |
| `warrant evidence N --log F --metric k=v [--seeds S --p P --std D]` | attach run evidence (hashed) |
| `warrant evidence N --type cite --ref DOI/arXiv/title [--quote Q]` | attach a citation (resolved, quote checked against abstract) |
| `warrant predict N JSON` / `warrant result N --observed k=v` | pre-register, then let code decide |
| `warrant kill IDEA` / `warrant retract N` | bury an idea / withdraw a claim |
| `warrant status` / `warrant report [--html]` | every claim with its status and reasons |
| `warrant trace FILE` / `warrant cites FILE` | check a draft's numbers / citations |

## Limits, stated plainly

- Tracing proves a number was **produced**, not that the code producing it is correct.
- `echo 0.93` produces a 0.93. The audit trail shows the command, but the check does not catch it. warrant is tamper-evident, not tamper-proof.
- Quote checks use the abstract. A quote only in the full text comes back "unverified", never "fake".
- Paraphrased titles may not match. Under 0.5 similarity counts as "not found".

## Roadmap

Lean 4 / SymPy proof receipts · drift detection beyond the question anchor · live dashboard · GitHub Action badge.

## License

MIT
