# LinkedIn

**Attach:** `launch/video/warrant-demo.mp4` (LinkedIn plays native video best; 47 s, 1920×1080). Or use `launch/assets/social-preview.png` as the image.
**When:** Tuesday to Thursday morning, your timezone. Put the link in the post, not the first comment: either works, and in-post is simpler.
**Tag:** your university, lab or company, if relevant. Don't tag people who haven't used it.

---

## Main post

```
AI is now writing a lot of research: analyses, related-work sections, whole drafts. It is also confidently wrong in ways that are hard to catch: accuracies no experiment produced, citations to papers that don't exist, "significant" results on a single run.

So I built warrant, an open-source referee for research done with AI agents (Claude Code, Codex, OpenCode). The rule is simple: code checks, not another model.

→ Every number the agent reports must trace to a command that actually ran.
→ Every citation is resolved, and claims attributed to a paper are checked against that paper's full text. When a model judges whether a passage supports a claim, it must quote the passage verbatim, and code rejects quotes that aren't there.
→ Reported p-values are recomputed from their test statistics.
→ Live experiments are watched by zero-token sentinels that flag NaNs, divergence, overfitting and suspiciously perfect scores while the run is still going.

To test the statistics checker, I recomputed 2,063 p-values from 851 open-access psychology papers. In 6 papers, the paper's own test statistic contradicts its significance claim. For example, t(1350) = 0.150 was reported as p = .04; the correct value is .88. I checked every case by hand and I'm not naming them: most are probably typos. That's exactly the kind of error that's easy to make and easy to catch with the right tool.

It's free and MIT-licensed. I'd especially love feedback from people who review papers or run experiments with AI agents.

https://github.com/ItsShreyamHere/warrant

#research #openscience #reproducibility #AI #machinelearning #metascience
```

---

## Short version (for a reshare or a comment)

```
I built an open-source "referee" for AI-assisted research: every number must trace to a real run, every citation is checked against the cited paper, and p-values are recomputed. Recomputing 2,063 p-values from 851 psychology papers found 6 whose own statistics contradict their conclusions. https://github.com/ItsShreyamHere/warrant
```
