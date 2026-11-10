"""statcheck over open-access psychology/medicine papers from Europe PMC (full-text XML).

    python bench/scan_pmc.py --n 500 --query '("t-test" OR ANOVA) AND (psychology OR psychiatry)'

One JSON line per paper (with every inconsistent test, verbatim) in bench/results/pmc.jsonl.
Resumable. Full text is structured XML: no PDF parsing, no guessing at layout.
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from warrant import cites, stats  # noqa: E402

API = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def search(query: str, n: int) -> list[str]:
    out, cursor = [], "*"
    while len(out) < n:
        q = urllib.parse.urlencode({"query": f"({query}) AND OPEN_ACCESS:y AND HAS_FT:y", "format": "json",
                                    "pageSize": 100, "resultType": "lite", "cursorMark": cursor})
        code, body = cites._get(f"{API}/search?{q}", timeout=60)
        if code != 200:
            break
        d = json.loads(body)
        out += [r["pmcid"] for r in d["resultList"]["result"] if r.get("pmcid")]
        if d.get("nextCursorMark") in (None, cursor):
            break
        cursor = d["nextCursorMark"]
    return out[:n]


def fulltext(pmcid: str) -> str:
    code, xml = cites._get(f"{API}/{pmcid}/fullTextXML", timeout=60)
    if code != 200:
        raise ValueError(f"HTTP {code}")
    xml = re.split(r"<ref-list", xml)[0]                 # drop references
    xml = re.sub(r"<sup>\s*([-−–]?\d+)\s*</sup>", r"^\1", xml)  # 10<sup>-5</sup> -> 10^-5
    xml = re.sub(r"<(?:italic|bold|sub|sc)[^>]*>|</(?:italic|bold|sub|sc)>", "", xml)  # inline markup
    xml = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", html.unescape(xml))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default='("t-test" OR "ANOVA" OR "chi-square") AND (psychology OR psychiatry)')
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default="bench/results/pmc.jsonl")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()
    ids = search(a.query, a.n)
    print(f"{len(ids)} papers", flush=True)
    for i, pmcid in enumerate(ids):
        if pmcid in done:
            continue
        row = {"id": pmcid}
        try:
            text = fulltext(pmcid)
            tests = stats.statcheck(text)
            row.update(tests=len(tests), adjusted=sum(t["adjusted"] for t in tests),
                       inconsistent=[t for t in tests if not t["consistent"]])
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"[:200]
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"[{i + 1}/{len(ids)}] {pmcid} tests={row.get('tests')} bad={len(row.get('inconsistent', []))}",
              flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
