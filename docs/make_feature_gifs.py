"""Render docs/watch.gif and docs/review.gif with the same renderer as demo.gif.

Lines replay real results (condensed): watch.gif replays the alerts from the live demo run in
the v0.9.0 commit; review.gif replays `warrant review --verify` on arXiv:1706.03762 and the
statcheck example from bench/RESULTS.md.   python docs/make_feature_gifs.py
"""
from make_demo_gif import AMBER, FG, GREEN, MUT, ORANGE, RED, main

WATCH = [
    ("cap", "Your experiment is training. warrant watch tails its log: plain code, 0 tokens"),
    ("line", "$ warrant watch runs/ &", ORANGE),
    ("line", "warrant watch: 1 file(s), every 1.0s, 0 tokens.", MUT),
    ("blank",),
    ("type", "  step=27 loss=0.5197 val_acc=0.724", MUT),
    ("type", "  step=28 loss=0.4937 val_acc=0.736", MUT),
    ("type", "  step=29 loss=0.4519 val_acc=0.748", MUT),
    ("type", "  step=33 loss=2.9614 val_acc=0.796", MUT),
    ("line", "[RED] diverge: loss = 2.9614, more than 3x its best 0.4519 (train.log)", RED),
    ("pause", 8),
    ("type", "  step=38 loss=nan", MUT),
    ("line", "[RED] nonfinite: loss became nan (train.log)", RED),
    ("line", "[YELLOW] stale: no new output for 3s: the run may have died (train.log)", AMBER),
    ("pause", 12),
    ("cap", "Your agent sees one ~40-token line per alert. No model ever reads the logs."),
    ("blank",),
    ("line", "[warrant watch] red diverge in train.log: loss = 2.9614, more than 3x its best", GREEN),
    ("pause", 30),
]

REVIEW = [
    ("cap", "warrant review reads the papers you cite, so the model doesn't have to"),
    ("line", "$ warrant review 1706.03762", ORANGE),
    ("type", "  reading arXiv:1706.03762 and its cited papers ...", MUT),
    ("type", "  9 evidence cards: 2,224 words instead of 28,916 (13x less to read)", MUT),
    ("pause", 8),
    ("cap", "Every verdict must quote the cited paper verbatim. Code checks the quote."),
    ("line", "$ warrant review --verify verdicts.json", ORANGE),
    ("line", "OK card 1: partial: quote found verbatim in the cited paper", GREEN),
    ("line", "OK card 2: not_found: no supporting passage in the retrieved evidence", GREEN),
    ("line", "OK card 3: supports: quote found verbatim in the cited paper", GREEN),
    ("line", "XX card 3: supports: REJECTED: quote is not in the cited paper", RED),
    ("pause", 14),
    ("cap", "And every p-value is recomputed from its test statistic"),
    ("line", "$ warrant stats paper.md", ORANGE),
    ("line", "XX t(1350) = 0.150, p = .04  ->  recomputed p = 0.8808  DECISION FLIPS at .05", RED),
    ("pause", 10),
    ("cap", "2,063 p-values in 851 papers: 6 papers' own stats contradict them. github.com/ItsShreyamHere/warrant"),
    ("pause", 40),
]

if __name__ == "__main__":
    main(WATCH, "watch.gif")
    main(REVIEW, "review.gif")
