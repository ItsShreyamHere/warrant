"""Turn a paper's LaTeX source into checkable pieces.

    sentences with the citation keys they carry, the abstract, and the body text
    passages of a (cited) paper ranked against a claim with BM25, stdlib only

Plain text is kept lossy but number-faithful: numbers, tables and math survive,
markup does not.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field

_CITE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citenum|parencite|textcite|autocite|footcite|supercite)"
    r"\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
_DROP_ENVS = re.compile(r"\\begin\{(figure\*?|algorithm\*?|lstlisting|verbatim|tikzpicture)\}.*?\\end\{\1\}", re.S)
_ABSTRACT = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[⟦])")
MARK = "⟦{}⟧"
_MARK_RE = re.compile(r"⟦([^⟧]*)⟧")


def strip_comments(tex: str) -> str:
    return _COMMENT.sub("", tex)


def tex_to_text(tex: str) -> str:
    """LaTeX -> plain text that keeps every number."""
    s = _DROP_ENVS.sub(" ", tex)
    s = re.sub(r"\\(?:label|ref|eqref|cref|Cref|autoref|url|href|includegraphics|bibliography\w*|"
               r"input|include|usepackage|documentclass|newcommand|renewcommand|def)\*?(?:\[[^\]]*\])?\{[^}]*\}",
               " ", s)
    s = re.sub(r"\\(?:textbf|textit|emph|texttt|textsc|mathrm|mathbf|mathit|text|underline|section|subsection|"
               r"subsubsection|paragraph|caption|title|footnote)\*?\s*\{", "{", s)
    s = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\{[^}]*\})?", " ", s)
    s = s.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_").replace("~", " ")
    s = re.sub(r"\\chi\s*\^\s*\{?2\}?", "chi2", s)
    s = re.sub(r"\\pm\b", "±", s)
    s = re.sub(r"\\times\b", "×", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = re.sub(r"[{}$&\\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Paper:
    abstract: str = ""
    body: str = ""
    sentences: list = field(default_factory=list)  # [(sentence_text, [cite keys])]


def parse_tex(files: dict[str, str]) -> Paper:
    parts = []
    for name, t in files.items():
        if not name.lower().endswith(".tex"):
            continue
        t = strip_comments(t)
        start = t.find("\\begin{document}")  # per file: section files have no preamble
        t = t[start:] if start >= 0 else t
        parts.append(re.split(r"\\begin\{thebibliography\}|\\bibliography\{|\\printbibliography", t)[0])
    tex = "\n".join(parts)
    p = Paper()
    m = _ABSTRACT.search(tex)
    if m:
        p.abstract = tex_to_text(m.group(1))
        tex = tex.replace(m.group(0), " ")
    marked = _CITE.sub(lambda m: " " + MARK.format(m.group(1).replace(" ", "")) + " ", tex)
    text = tex_to_text(marked)
    p.body = _MARK_RE.sub(" ", text)
    for sent in _SENT_SPLIT.split(text):
        keys = [k for grp in _MARK_RE.findall(sent) for k in grp.split(",") if k]
        if keys:
            clean = re.sub(r"\s+", " ", _MARK_RE.sub("[*]", sent)).strip()
            p.sentences.append((clean, keys))
    return p


# --- retrieval -------------------------------------------------------------

_STOP = set("the and for with that this from are was were been have has had not but its their our we they "
            "which also can may such than then these those into over under more most less very using used "
            "use based show shows shown paper work method methods approach results result model models".split())


def _terms(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9-]{2,}", s.lower()) if w not in _STOP]


def passages(text: str, size: int = 110, step: int = 70) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [text] if text else []
    return [" ".join(words[i:i + size]) for i in range(0, max(1, len(words) - size + step), step)]


def best_passages(query: str, text: str, k: int = 2) -> list[tuple[float, str]]:
    """BM25 over overlapping ~110-word windows. Returns [(score, passage)], best first."""
    docs = passages(text)
    if not docs:
        return []
    toks = [_terms(d) for d in docs]
    n, avg = len(docs), sum(map(len, toks)) / max(1, len(docs))
    df = Counter(t for ts in toks for t in set(ts))
    q = set(_terms(query))
    scored = []
    for d, ts in zip(docs, toks):
        tf = Counter(ts)
        s = 0.0
        for t in q:
            if tf[t]:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(ts) / max(1, avg)))
        scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    # drop near-duplicate overlapping windows
    out: list[tuple[float, str]] = []
    for s, d in scored:
        if all(len(set(d.split()) & set(o.split())) < 0.5 * len(set(d.split())) for _, o in out):
            out.append((round(s, 2), d))
        if len(out) == k:
            break
    return out


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9%.]+", " ", s.lower()).strip()


def quote_in(quote: str, text: str) -> bool:
    """Verbatim (modulo case, spacing, punctuation) quote check."""
    q = normalize(quote)
    return len(q) >= 15 and q in normalize(text)
