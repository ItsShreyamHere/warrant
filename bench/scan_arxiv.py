"""Audit the references of recent arXiv papers. Reproducible launch benchmark.

    python bench/scan_arxiv.py --per-cat 70 --cats cs.CL cs.LG cs.AI --out bench/results/scan.jsonl

One JSON line per paper. Resumable: papers already in --out are skipped. Polite to
arXiv: one source download at a time, a few seconds apart.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from warrant import audit, cites  # noqa: E402


def recent_ids(cat: str, n: int) -> list[tuple[str, str]]:
    q = urllib.parse.urlencode({"search_query": f"cat:{cat}", "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": n})
    code, body = cites._get("https://export.arxiv.org/api/query?" + q)
    if code != 200:
        raise SystemExit(f"arXiv listing failed for {cat}: HTTP {code}")
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", body, re.S):
        aid = re.search(r"<id>http://arxiv.org/abs/([^<]+?)(v\d+)?</id>", entry)
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        if aid:
            out.append((aid.group(1), re.sub(r"\s+", " ", title.group(1)).strip() if title else ""))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cats", nargs="+", default=["cs.CL", "cs.LG", "cs.AI"])
    ap.add_argument("--per-cat", type=int, default=70)
    ap.add_argument("--out", default="bench/results/scan.jsonl")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()

    papers: dict[str, tuple[str, str]] = {}
    for cat in a.cats:
        for aid, title in recent_ids(cat, a.per_cat):
            papers.setdefault(aid, (cat, title))
        time.sleep(3)

    for i, (aid, (cat, title)) in enumerate(papers.items()):
        if aid in done:
            continue
        row = {"id": aid, "cat": cat, "title": title}
        try:
            refs = audit.refs_from_files(audit.fetch_arxiv_source(aid))
            refs = audit.audit(refs, workers=a.workers) if refs else []
            row.update(n=len(refs),
                       verified=sum(r.status == "green" for r in refs),
                       unchecked=sum(r.status == "yellow" for r in refs),
                       flagged=[{"key": r.key, "title": r.title, "doi": r.doi, "arxiv": r.arxiv,
                                 "why": r.why, "raw": r.raw[:300]} for r in refs if r.status == "red"])
        except Exception as e:  # one bad bundle must not stop the scan
            row["error"] = f"{type(e).__name__}: {e}"[:200]
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"[{i + 1}/{len(papers)}] {aid} refs={row.get('n')} flagged={len(row.get('flagged', []))}"
              f"{' ERR ' + row['error'] if 'error' in row else ''}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
