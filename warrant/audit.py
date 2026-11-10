"""`warrant audit`: check every reference in a paper exists.

Input: an arXiv id (its LaTeX source is fetched and read in memory, never extracted to
disk), or a local .bib / .bbl / .tex / .md file.

A reference is flagged only when every registry misses it: its identifier does not
resolve, or no work in OpenAlex or Crossref has a similar title. Anything we cannot
reach or parse is "unchecked", never "fake".
"""
import gzip
import io
import json
import re
import tarfile
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import cites

MAX_SOURCE_BYTES = 50_000_000


@dataclass
class Ref:
    key: str
    title: str | None = None
    doi: str | None = None
    arxiv: str | None = None
    raw: str = ""
    status: str = "yellow"
    why: str = "unchecked"
    found: str | None = None
    extra: dict = field(default_factory=dict)


def _latex_to_text(s: str) -> str:
    s = re.sub(r"\\(?:emph|textit|textbf|em|it|bf|url|href)\s*", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"[{}~]", " ", s)
    s = s.replace("\\&", "&").replace("--", "-")
    return re.sub(r"\s+", " ", s).strip()


def _ids(ref: Ref, text: str) -> None:
    # .bbl files hard-wrap lines and use `%` line continuations, which can split a DOI
    # in two; join them, then keep the longest candidate (the one that wasn't cut)
    joined = re.sub(r"%\s*\n\s*", "", text)
    joined = re.sub(r"(10\.\d{4,9}/\S*?)\s*\n\s*(?=[\w./-]+[}\s,])", r"\1", joined)
    dois = [cites.clean_doi(m.group(1)) for m in cites._DOI.finditer(joined)]
    if dois:
        ref.doi = max(dois, key=len)
    # only explicit arXiv references: a bare NNNN.NNNNN also matches page numbers
    m = cites._ARXIV.search(joined) or re.search(r"\\eprint\{(\d{4}\.\d{4,5})", joined)
    if m:
        ref.arxiv = m.group(1)


def _title_without_newblock(body: str) -> str | None:
    """ACL/plain styles: `Authors. 2024. Title. Venue.` -> Title."""
    t = _latex_to_text(body)
    m = re.search(r"\b(?:19|20)\d{2}[a-z]?\.\s+(.+?[^A-Z])\.\s", t)
    return m.group(1).strip() if m and len(m.group(1)) >= 12 else None


def parse_bbl(text: str) -> list[Ref]:
    """natbib/biblatex-free .bbl: \\bibitem{key} Authors. \\newblock Title. \\newblock Venue."""
    out = []
    for chunk in re.split(r"\\bibitem", text)[1:]:
        m = re.match(r"\s*(?:\[[^\]]*(?:\][^\]]*)?\])?\s*\{([^}]*)\}(.*)", chunk, re.S)
        if not m:
            continue
        key, body = m.group(1), m.group(2).split("\\end{thebibliography}")[0]
        ref = Ref(key=key, raw=_latex_to_text(body)[:300])
        _ids(ref, body)
        blocks = [_latex_to_text(b) for b in re.split(r"\\newblock", body)]
        if len(blocks) >= 2:
            ref.title = blocks[1].rstrip(". ")
        else:
            ref.title = _title_without_newblock(body)
        out.append(ref)
    return out


def parse_bib(text: str) -> list[Ref]:
    out = []
    for e in cites.bib_entries(text):
        ref = Ref(key=e["key"], title=_latex_to_text(e["title"]) if e["title"] else None,
                  doi=cites.clean_doi(e["doi"]) if e["doi"] else None, arxiv=e["eprint"])
        ref.raw = ref.title or ""
        out.append(ref)
    return out


def fetch_arxiv_source(aid: str) -> dict[str, str]:
    """{filename: text} of .bbl/.bib/.tex files in an arXiv source bundle, read in memory."""
    import urllib.request
    req = urllib.request.Request(f"https://arxiv.org/e-print/{urllib.parse.quote(aid)}", headers=cites.UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("source bundle too large")
    files: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            for mem in tf.getmembers():
                if mem.isfile() and mem.name.lower().endswith((".bbl", ".bib", ".tex")) and mem.size < 5_000_000:
                    f = tf.extractfile(mem)
                    if f:
                        files[mem.name] = f.read().decode("utf-8", errors="replace")
    except tarfile.ReadError:
        try:
            files["main.tex"] = gzip.decompress(data).decode("utf-8", errors="replace")
        except OSError:
            if data[:4] == b"%PDF":
                raise ValueError("arXiv only has a PDF for this paper; no LaTeX source to read")
            files["main.tex"] = data.decode("utf-8", errors="replace")
    return files


def refs_from_files(files: dict[str, str]) -> list[Ref]:
    """Prefer the compiled .bbl (what the paper actually cites), then .bib, then inline bibitems."""
    for ext, parser in ((".bbl", parse_bbl), (".bib", parse_bib), (".tex", parse_bbl)):
        refs = [r for name, text in files.items() if name.lower().endswith(ext) for r in parser(text)]
        if refs:
            return refs
    return []


def search_crossref(title: str) -> dict:
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5})
    code, body = cites._get("https://api.crossref.org/works?" + q)
    if code != 200:
        return {"status": "yellow", "why": "Crossref unreachable"}
    try:
        items = json.loads(body)["message"]["items"]
    except (ValueError, KeyError):
        return {"status": "yellow", "why": "unreadable Crossref response"}
    best = max(((cites.title_similarity(title, (i.get("title") or [""])[0]), (i.get("title") or [""])[0])
                for i in items), default=(0.0, ""))
    if best[0] >= 0.85:
        return {"status": "green", "why": "title found", "title": best[1]}
    return {"status": "red" if best[0] < 0.5 else "yellow", "why": "not in Crossref", "title": best[1]}


def check_ref(ref: Ref) -> Ref:
    id_missing = False  # an identifier that definitely does not exist
    for kind, ident, fn in (("DOI", ref.doi, cites.resolve_doi), ("arXiv", ref.arxiv, cites.resolve_arxiv)):
        if not ident:
            continue
        r = fn(ident)
        if r["status"] == "green":
            ref.status, ref.why, ref.found = "green", f"{kind} resolves", r.get("title")
            return ref
        id_missing |= r["status"] == "red"
        # unreachable (e.g. arXiv rate limit): fall through to a title search
    # A dead identifier alone is never "fake": in a parsed bibliography it is far more
    # often a typo or a line-wrapped DOI. Only a title no registry knows is flagged.
    if not ref.title or len(ref.title) < 12:
        ref.status, ref.why = "yellow", ("identifier does not resolve; no title to search" if id_missing
                                         else "no title or identifier to check")
        return ref
    oa = cites.search_title(ref.title)
    cr = search_crossref(ref.title) if oa["status"] != "green" else {}
    found = oa if oa["status"] == "green" else cr if cr.get("status") == "green" else None
    if found:
        ref.status, ref.why = ("yellow", "title is real, but its identifier does not resolve") if id_missing \
            else ("green", "title found")
        ref.found = found.get("title")
        return ref
    # Crossref's fuzzy search always returns something loosely similar, so only a
    # clear OpenAlex miss plus no Crossref match counts as "not found". Software,
    # web pages, reports and theses are often not indexed: never flag those.
    not_indexed = re.search(r"https?://|github|technical report|tech\. rep|thesis|blog|documentation|"
                            r"manual|preprint|in preparation|personal communication|accessed", ref.raw, re.I)
    if oa["status"] == "red" and cr.get("why") == "not in Crossref" and len(ref.title.split()) >= 4 \
            and not not_indexed:
        ref.status, ref.why = "red", "no work with this title in OpenAlex or Crossref"
    else:
        ref.status, ref.why = "yellow", "close but not exact match: " + (oa.get("why") or "")
    return ref


def audit(refs: list[Ref], workers: int = 4) -> list[Ref]:
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(check_ref, refs))
