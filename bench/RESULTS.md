# Benchmark results

All numbers below come from the scripts in this folder. Every flag counted as an error was checked by hand against the paper's own text. Paper identifiers are deliberately not published: an inconsistency is usually a typo, not misconduct.

## statcheck on open-access psychology papers (Europe PMC, 2026-11-11)

`python bench/scan_pmc.py --n 500` (query: `("t-test" OR "ANOVA" OR "chi-square") AND (psychology OR psychiatry)`, open access with full text)

| | |
|---|---|
| papers scanned | 851 |
| papers reporting APA-style tests | 215 |
| tests recomputed (t, F, χ², r, z) | 2,063 |
| recognised as multiple-comparison-adjusted (not errors) | 74 |
| papers whose own statistics contradict a reported significance decision, **hand-verified** | **6 (2.8% of papers reporting tests)** |

The six, anonymised:

| reported | recomputed p | likely cause |
|---|---|---|
| t(1350) = 0.150, p = .04 | .88 | t or p mistyped |
| F(3, 196) = 2.566, p = .046 | .056 | significance claimed at p > .05 |
| F(1.026, 47.197) = 3.003, p = .025 | .089 | Greenhouse-Geisser interaction reported as significant |
| F(1, 55) = 3.93 / 3.45 / 3.48, p = .024 / .035 / .034 | .052 / .069 / .068 | F-test p-values halved |
| F(1, 74) = 0.22, p = .002 | .64 | F mistyped |
| z = 2.28, p = .21 | .023 | p mistyped |

Minor inconsistencies (the decision doesn't flip) were not hand-checked and are not counted.

## statcheck on recent arXiv papers (cs.HC, q-bio.NC, stat.AP, cs.CY, 2026-11-10)

`python bench/scan_stats.py`: 366 papers, 22 with APA-style tests, 91 tests, **0 inconsistencies**.

The first pass flagged 20 tests. All 20 were parser artifacts: p-values in scientific notation, and Bonferroni-adjusted p-values. Both cases are now handled, with regression tests in `tests/test_warrant.py`.
