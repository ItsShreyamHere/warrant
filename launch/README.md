# Launch pack

Everything you need to announce warrant. You post on social media yourself. Every number in these files is measured and in the repo (README, `bench/RESULTS.md`). Never name the flagged papers.

| folder | what |
|---|---|
| `hacker-news/show-hn.md` | title options, first comment, answers to likely questions |
| `reddit/posts.md` | separate posts for r/MachineLearning, r/ClaudeAI, r/PhD/r/academia, r/AcademicPsychology/r/statistics, r/Python, Codex/OpenCode communities |
| `linkedin/post.md` | main post and a short reshare version |
| `where-to-post.md` | directories, marketplaces, awesome-lists, newsletters and research communities beyond social media, with submission links and a ranked top 15 |
| `video/warrant-demo.mp4` | 47 s, 1920×1080: numbers traced → papers read → live runs watched. Best for LinkedIn |
| `video/warrant-demo-hq.gif` | the same video as a 1280-px GIF, for Reddit and GitHub |
| `assets/` | per-feature GIFs (`demo`, `review`, `watch`) and the 1280×640 social card |

All visuals are rendered from code (`docs/make_video.py`, `docs/make_feature_gifs.py`), so they can be regenerated after any change.

## Timing gates (from `where-to-post.md`)

The repo was created on 2026-11-10. Some lists only accept it later:
- **awesome-claude-code:** from about 2026-11-24 (14 days old), or at 100 stars. Submit with the issue form, not a PR.
- **awesome-opencode:** 25 stars **and** about 2026-12-10 (30 days).
- **awesome-python:** after a non-alpha 1.0 release and 1 month of age.
- **JOSS (software paper):** after about 6 months public (around May 2027).
- **OpenAI's plugin directory** may reject plugins with lifecycle hooks. Check before uploading.

## Suggested order

1. **Day 0:** upload `assets/social-preview.png` (repo Settings → Social preview). Publish to PyPI (`python -m twine upload dist/*`), so `pip install warrant-research` works.
2. **Day 1 (Tue–Thu, 8–10 am ET):** Show HN. Stay for 3 hours to answer comments.
3. **Day 1 evening or Day 2:** LinkedIn with the video. Submit to the top directories and plugin marketplaces in `where-to-post.md`.
4. **Days 2–5:** one Reddit post per day: r/MachineLearning → r/ClaudeAI → r/AcademicPsychology → r/PhD. Open awesome-list PRs.
5. **Week 2:** newsletters, then a follow-up post with something new, such as a fresh benchmark or "we reviewed N famous papers' references".
