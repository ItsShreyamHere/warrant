"""Recompute every reported p-value in recent arXiv papers. Reproducible launch benchmark.

    python bench/scan_stats.py --cats cs.HC q-bio.NC stat.AP cs.CY --per-cat 150

Reads each paper's LaTeX source (in memory), runs statcheck + GRIM, writes one JSON line per
paper to bench/results/stats.jsonl. Resumable. Only arXiv is contacted, a few seconds apart.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from warrant import audit, cites, paper, stats  # noqa: E402


def ids(cat: str, n: int) -> list[str]:
    code, body = cites._get(f"https://arxiv.org/list/{urllib.parse.quote(cat)}/pastweek?skip=0&show=250",
                            tries=6, timeout=60)
    if code != 200:
        print(f"skipping {cat}: HTTP {code}", flush=True)
        return []
    return list(dict.fromkeys(re.findall(r'href\s*=\s*"/abs/(\d{4}\.\d{4,5})', body)))[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cats", nargs="+", default=["cs.HC", "q-bio.NC", "stat.AP", "cs.CY"])
    ap.add_argument("--per-cat", type=int, default=150)
    ap.add_argument("--out", default="bench/results/stats.jsonl")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo: dict[str, str] = {}
    for cat in a.cats:
        for aid in ids(cat, a.per_cat):
            todo.setdefault(aid, cat)
        time.sleep(3)
    for i, (aid, cat) in enumerate(todo.items()):
        if aid in done:
            continue
        row = {"id": aid, "cat": cat}
        try:
            p = paper.parse_tex(audit.fetch_arxiv_source(aid))
            text = p.abstract + " " + p.body
            tests = stats.statcheck(text)
            row.update(tests=len(tests), inconsistent=[t for t in tests if not t["consistent"]],
                       grim=stats.grim(text))
        except Exception as e:  # one odd bundle must not stop the scan
            row["error"] = f"{type(e).__name__}: {e}"[:200]
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"[{i + 1}/{len(todo)}] {aid} tests={row.get('tests')} "
              f"bad={len(row.get('inconsistent', []))}{' ERR' if 'error' in row else ''}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
