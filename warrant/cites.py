"""Citation checks against public registries (Crossref, arXiv, OpenAlex). Stdlib only.

red    - the identifier does not exist, or the quoted title belongs to a different paper,
         or no paper anywhere resembles a cited title
yellow - could not check (offline, rate-limited, timeout)
green  - resolves, and the title (when given) matches

Network failure is never red: an unreachable registry must not accuse anyone.
Results are cached in `.warrant/cites.json`.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

GREEN, YELLOW, RED = "green", "yellow", "red"
UA = {"User-Agent": "warrant/0.1 (citation check)"}
TIMEOUT = 6
MAX_LOOKUPS = 12

_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)", re.I)
_ARXIV = re.compile(r"(?:arxiv(?:\.org/(?:abs|pdf)/|:\s*))(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?", re.I)
_QUOTED = re.compile(r"[\"“]([^\"”\n]{15,250})[\"”]|\*([^*\n]{15,250})\*")
_CITE_CUE = re.compile(r"\bet al\.?|\b(?:19|20)\d{2}\b")


def _offline() -> bool:
    return os.environ.get("WARRANT_OFFLINE") == "1"


def _get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


def _norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm_title(a), _norm_title(b)).ratio()


def resolve_doi(doi: str) -> dict:
    code, body = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/"))
    if code == 404:
        return {"status": RED, "why": "DOI does not exist"}
    if code != 200:
        return {"status": YELLOW, "why": "Crossref unreachable"}
    try:
        msg = json.loads(body)["message"]
        title = (msg.get("title") or [""])[0]
        abstract = re.sub(r"<[^>]+>", " ", msg.get("abstract") or "")
    except (ValueError, KeyError, IndexError):
        return {"status": YELLOW, "why": "unreadable Crossref response"}
    return {"status": GREEN, "why": "resolves", "title": title, "abstract": abstract}


def resolve_arxiv(aid: str) -> dict:
    code, body = _get("https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid, safe="/"))
    if code != 200:
        return {"status": YELLOW, "why": "arXiv unreachable"}
    entry = re.search(r"<entry>(.*?)</entry>", body, re.S)
    if not entry or "<title>Error</title>" in entry.group(1) or "<id>http://arxiv.org/api/errors" in entry.group(1):
        return {"status": RED, "why": "arXiv id does not exist"}
    title = re.search(r"<title>(.*?)</title>", entry.group(1), re.S)
    summ = re.search(r"<summary>(.*?)</summary>", entry.group(1), re.S)
    return {"status": GREEN, "why": "resolves",
            "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else "",
            "abstract": re.sub(r"\s+", " ", summ.group(1)).strip() if summ else ""}


def search_title(title: str) -> dict:
    q = urllib.parse.urlencode({"search": title, "per-page": 5})
    code, body = _get("https://api.openalex.org/works?" + q)
    if code != 200:
        return {"status": YELLOW, "why": "OpenAlex unreachable"}
    try:
        results = json.loads(body).get("results") or []
    except ValueError:
        return {"status": YELLOW, "why": "unreadable OpenAlex response"}
    best = max(results, key=lambda r: title_similarity(title, r.get("title") or ""), default=None)
    score = title_similarity(title, best.get("title") or "") if best else 0.0
    if score >= 0.85:
        return {"status": GREEN, "why": "title found", "title": best["title"]}
    if score < 0.5:
        return {"status": RED, "why": "no paper with this title found"}
    return {"status": YELLOW, "why": f"closest real title: {best['title']}"}


class _Cache:
    def __init__(self, d: Path | None):
        self.path = (d / "cites.json") if d else None
        self.data = {}
        if self.path and self.path.is_file():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except ValueError:
                self.data = {}

    def get(self, key, fn):
        if key in self.data:
            return self.data[key]
        val = fn()
        if val["status"] != YELLOW:  # never cache "couldn't check"
            self.data[key] = val
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        return val


def _nearby_title(text: str, pos: int) -> str | None:
    """A quoted/italic title in the same paragraph, just before the identifier."""
    para_start = text.rfind("\n\n", 0, pos) + 1
    window = text[max(para_start, pos - 300):pos]
    m = list(_QUOTED.finditer(window))
    return (m[-1].group(1) or m[-1].group(2)) if m else None


def check_text(text: str, cache_dir: Path | None = None) -> list[dict]:
    """Every citation in `text`: identifiers, plus quoted titles that look like citations."""
    if _offline() or not text:
        return []
    cache = _Cache(cache_dir)
    out, seen, lookups = [], set(), 0
    found: list[tuple[str, str, int]] = []
    for m in _DOI.finditer(text):
        found.append(("doi", m.group(1).rstrip(".,;:)]}>"), m.start()))
    for m in _ARXIV.finditer(text):
        found.append(("arxiv", m.group(1), m.start()))
    covered = []
    for kind, ident, pos in found:
        if (kind, ident) in seen or lookups >= MAX_LOOKUPS:
            continue
        seen.add((kind, ident))
        lookups += 1
        res = dict(cache.get(f"{kind}:{ident}", lambda: resolve_doi(ident) if kind == "doi" else resolve_arxiv(ident)))
        res["id"] = f"{'doi' if kind == 'doi' else 'arXiv'}:{ident}"
        claimed = _nearby_title(text, pos)
        if claimed:
            covered.append(claimed)
        if res["status"] == GREEN and claimed and res.get("title"):
            if title_similarity(claimed, res["title"]) < 0.6:
                res = {**res, "status": RED, "why": f"this id is a different paper: \"{res['title']}\""}
        out.append(res)
    # quoted titles with a citation cue (year / et al.) and no identifier
    for m in _QUOTED.finditer(text):
        title = m.group(1) or m.group(2)
        if title in covered or lookups >= MAX_LOOKUPS:
            continue
        ctx = text[max(0, m.start() - 80):m.end() + 80]
        if not _CITE_CUE.search(ctx):
            continue
        lookups += 1
        res = dict(cache.get(f"title:{_norm_title(title)}", lambda: search_title(title)))
        res["id"] = f"\"{title}\""
        out.append(res)
    return out


def check_quote(res: dict, quote: str) -> dict:
    """Is the quoted sentence in the abstract we could fetch? Not finding it is yellow:
    the full text may hold it."""
    if not quote or res.get("status") != GREEN:
        return res
    hay = _norm_title(res.get("abstract", ""))
    if _norm_title(quote) and _norm_title(quote) in hay:
        return {**res, "why": "resolves; quote found in abstract"}
    return {**res, "status": YELLOW, "why": "resolves; quote not in abstract (full text not checked)"}


def resolve(ref: str) -> dict:
    m = _ARXIV.search(ref) or re.fullmatch(r"(\d{4}\.\d{4,5})(v\d+)?", ref.strip())
    if m:
        return resolve_arxiv(m.group(1))
    m = _DOI.search(ref)
    if m:
        return resolve_doi(m.group(1).rstrip(".,;:)]}>"))
    return search_title(ref)


def bib_entries(text: str) -> list[dict]:
    """Minimal BibTeX reader: key, title, doi, eprint per entry."""
    out = []
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", text, re.S):
        body = m.group(2)

        def field(name):
            f = re.search(name + r"\s*=\s*[{\"](.*?)[}\"]\s*,?\s*\n", body, re.S | re.I)
            return re.sub(r"[{}]", "", re.sub(r"\s+", " ", f.group(1))).strip() if f else None
        out.append({"key": m.group(1), "title": field("title"), "doi": field("doi"), "eprint": field("eprint")})
    return out


def check_bib(text: str, cache_dir: Path | None = None) -> list[dict]:
    cache = _Cache(cache_dir)
    out = []
    for e in bib_entries(text):
        if e["doi"]:
            res = dict(cache.get(f"doi:{e['doi']}", lambda: resolve_doi(e["doi"])))
        elif e["eprint"]:
            res = dict(cache.get(f"arxiv:{e['eprint']}", lambda: resolve_arxiv(e["eprint"])))
        elif e["title"]:
            res = dict(cache.get(f"title:{_norm_title(e['title'])}", lambda: search_title(e["title"])))
        else:
            res = {"status": YELLOW, "why": "no doi, eprint, or title"}
        if res["status"] == GREEN and e["title"] and res.get("title") and title_similarity(e["title"], res["title"]) < 0.6:
            res = {**res, "status": RED, "why": f"id points to a different paper: \"{res['title']}\""}
        res["id"] = e["key"]
        out.append(res)
    return out
