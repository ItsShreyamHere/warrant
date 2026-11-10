"""`warrant review`: a referee report on a paper's claims and citations.

Code checks (free, deterministic):
  1. every reference exists                                   (audit.py)
  2. numbers attributed to a cited paper appear in its full text
  3. numbers in the abstract appear in the paper's own body/tables
  4. "significant" comes with a p-value, CI, or +/- nearby

Evidence cards (token-efficient judgment):
  for each citing sentence, the 2 passages of the cited paper that best match it (BM25),
  ~110 words each. A model judges the card, never the whole paper, and every verdict must
  carry a verbatim quote that code then finds in the cited text (`--verify`).
"""
import json
import os
import re
import time
from pathlib import Path

from . import audit, cites, stats
from . import paper as pp
from . import provenance as prov

CACHE = Path(os.environ.get("WARRANT_CACHE") or Path.home() / ".warrant" / "cache")
_OWN = re.compile(r"\b(we|our|ours|us|this paper|this work)\b", re.I)
_SIGNIF = re.compile(r"\bsignificant(ly)?\b", re.I)
_NOT_SIGNIF = re.compile(r"\b(not|no|non|in)\s*-?\s*significant", re.I)
_STATS = re.compile(r"\bp\s*[<=>≤]|p-value|\bci\b|confidence interval|±|\+/-|std|standard (deviation|error)|"
                    r"t-test|wilcoxon|bootstrap|anova|\bsem\b|\bse\b", re.I)


# --- sources -----------------------------------------------------------------

def find_arxiv(title: str | None, doi: str | None = None) -> str | None:
    """arXiv id of a work, via OpenAlex (title search or DOI)."""
    import urllib.parse
    if doi:
        m = re.match(r"10\.48550/arxiv\.(.+)$", doi, re.I)
        if m:
            return m.group(1)
        url = "https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/()")
    elif title:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search": title, "per-page": 5})
    else:
        return None
    code, body = cites._get(url)
    if code != 200:
        return None
    data = json.loads(body)
    works = data.get("results") if "results" in data else [data]
    for w in works:
        if title and cites.title_similarity(title, w.get("title") or "") < 0.85:
            continue
        blob = json.dumps(w.get("locations") or []) + json.dumps(w.get("ids") or {})
        m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", blob) or \
            re.search(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", blob, re.I)
        if m:
            return m.group(1)
    return None


def source_text(aid: str) -> dict | None:
    """{"abstract", "body"} of an arXiv paper, cached on disk."""
    f = CACHE / "papers" / f"{aid.replace('/', '_')}.json"
    if f.is_file():
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        files = audit.fetch_arxiv_source(aid)
    except Exception:
        return None
    p = pp.parse_tex(files)
    if len(p.body) < 500:
        return None
    out = {"abstract": p.abstract, "body": p.body}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out), encoding="utf-8")
    return out


# --- checks ------------------------------------------------------------------

def _in_text(tok, nums: list[float]) -> bool:
    return any(lo <= n <= hi for n in nums for lo, hi in prov.windows(tok))


def abstract_numbers(p: pp.Paper) -> list[dict]:
    body_nums = prov.source_numbers(p.body)
    means = [v for _, v in prov.window_means(p.body)]
    out = []
    for t in prov.extract(p.abstract):
        if not _in_text(t, body_nums) and not _in_text(t, means):
            out.append({"check": "abstract number not in body", "level": "yellow", "number": t.raw,
                        "detail": "the abstract reports it, but no table or section of the paper contains it"})
    return out


def significance(p: pp.Paper) -> list[dict]:
    sents = pp._SENT_SPLIT.split(p.body)
    out = []
    for i, s in enumerate(sents):
        if _SIGNIF.search(s) and not _NOT_SIGNIF.search(s) and _OWN.search(s):
            ctx = " ".join(sents[max(0, i - 1):i + 2])
            if not _STATS.search(ctx):
                out.append({"check": "significance without statistics", "level": "yellow",
                            "sentence": s[:300],
                            "detail": "claims significance; no p-value, CI, ± or test in this or adjacent sentences"})
    return out


def stat_findings(text: str) -> list[dict]:
    out = []
    for r in stats.statcheck(text):
        if not r["consistent"]:
            flip = " (decision flips at .05)" if r["gross"] else ""
            out.append({"check": "p-value does not match its test statistic" + flip,
                        "level": "red" if r["gross"] else "yellow", "sentence": r["text"],
                        "detail": f"reported {r['reported_p']}, recomputed p = {r['computed_p']}"})
    for g in stats.grim(text):
        out.append({"check": "impossible mean (GRIM)", "level": "yellow", "sentence": g["text"],
                    "detail": g["detail"] + " (applies if responses are integers, e.g. Likert items or counts)"})
    return out


def run(files: dict[str, str], max_sources: int = 25, max_cards: int = 40, check_refs: bool = True,
        log=lambda *a: None) -> dict:
    p = pp.parse_tex(files)
    refs = {r.key: r for r in audit.refs_from_files(files)}
    findings: list[dict] = []
    findings += abstract_numbers(p)
    findings += significance(p)
    findings += stat_findings(p.abstract + " " + p.body)

    if check_refs and refs:
        log(f"checking {len(refs)} references exist ...")
        for r in audit.audit(list(refs.values())):
            if r.status == "red":
                findings.append({"check": "reference not found anywhere", "level": "red", "ref": r.key,
                                 "detail": f"{r.title or r.raw[:120]}: {r.why}"})

    # cited full texts, most-cited first
    counts: dict[str, int] = {}
    for _, keys in p.sentences:
        for k in keys:
            counts[k] = counts.get(k, 0) + 1
    sources: dict[str, dict] = {}
    for key in sorted(counts, key=lambda k: -counts[k]):
        if len(sources) >= max_sources:
            break
        r = refs.get(key)
        if not r:
            continue
        aid = r.arxiv or find_arxiv(r.title, r.doi)
        if not aid:
            continue
        log(f"reading cited paper {key} (arXiv:{aid}) ...")
        src = source_text(aid)
        if src:
            sources[key] = {"arxiv": aid, "title": r.title, **src}
        time.sleep(1)  # polite to arXiv

    cards = []
    for sent, keys in p.sentences:
        if len(keys) != 1 or keys[0] not in sources:
            continue  # multi-citation sentences can't be attributed to one source
        src = sources[keys[0]]
        full = src["abstract"] + " " + src["body"]
        nums = prov.extract(sent)
        if nums and not _OWN.search(sent):
            src_nums = prov.source_numbers(full)
            missing = [t.raw for t in nums if not _in_text(t, src_nums)]
            if missing:
                findings.append({"check": "attributed number not in cited paper", "level": "red",
                                 "ref": keys[0], "sentence": sent[:300], "number": ", ".join(missing),
                                 "detail": f"not found anywhere in arXiv:{src['arxiv']}"})
        if len(cards) < max_cards:
            ev = pp.best_passages(sent, full, k=2)
            cards.append({"card": len(cards) + 1, "ref": keys[0], "arxiv": src["arxiv"], "title": src["title"],
                          "claim": sent[:400], "passages": [d for _, d in ev], "score": ev[0][0] if ev else 0})
    return {"findings": findings, "cards": cards,
            "stats": {"references": len(refs), "citing_sentences": len(p.sentences),
                      "sources_read": len(sources), "cards": len(cards)}}


# --- quote-verified verdicts -------------------------------------------------

VERDICTS = {"supports", "partial", "contradicts", "not_found"}


def verify(cards: list[dict], verdicts: list[dict]) -> list[dict]:
    """Accept a verdict only if its quote is verbatim in the cited paper ('not_found' needs none)."""
    by = {c["card"]: c for c in cards}
    out = []
    for v in verdicts:
        c = by.get(v.get("card"))
        verdict = v.get("verdict")
        if not c or verdict not in VERDICTS:
            out.append({**v, "accepted": False, "why": "unknown card or verdict"})
            continue
        if verdict == "not_found":
            out.append({**v, "accepted": True, "why": "no supporting passage in the retrieved evidence"})
            continue
        src = source_text(c["arxiv"]) or {}
        full = (src.get("abstract", "") + " " + src.get("body", ""))
        ok = pp.quote_in(v.get("quote", ""), full)
        out.append({**v, "accepted": ok, "why": "quote found verbatim in the cited paper" if ok
                    else "REJECTED: quote is not in the cited paper"})
    return out


# --- output ------------------------------------------------------------------

def markdown(name: str, res: dict) -> str:
    st, f = res["stats"], res["findings"]
    red = [x for x in f if x["level"] == "red"]
    yel = [x for x in f if x["level"] == "yellow"]
    lines = [f"# warrant review: {name}", "",
             f"{st['references']} references · {st['citing_sentences']} citing sentences · "
             f"{st['sources_read']} cited papers read in full · {len(red)} problems · {len(yel)} to check", ""]
    for title, group in (("Problems", red), ("Worth checking", yel)):
        if group:
            lines += [f"## {title}", ""]
            for x in group:
                where = f" [{x['ref']}]" if x.get("ref") else ""
                num = f" `{x['number']}`" if x.get("number") else ""
                lines.append(f"- **{x['check']}**{where}{num}: {x['detail']}")
                if x.get("sentence"):
                    lines.append(f"  > {x['sentence']}")
            lines.append("")
    if res["cards"]:
        lines += ["## Evidence cards", "",
                  "For each card: does the cited passage support the claim? Answer in verdicts.json as "
                  '`{"card": N, "verdict": "supports|partial|contradicts|not_found", "quote": "<verbatim from a passage>"}`, '
                  "then run `warrant review --verify verdicts.json`.", ""]
        for c in res["cards"]:
            lines += [f"### Card {c['card']}: [{c['ref']}] {c['title'] or ''} (arXiv:{c['arxiv']})",
                      f"**Claim:** {c['claim']}", ""]
            lines += [f"> {d}" for d in c["passages"]] + [""]
    return "\n".join(lines)
