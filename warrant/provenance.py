"""Number provenance: where did each number in a piece of text come from?

A number is traced when it matches, within the writer's rounding, a number some
source actually produced: a command's output, a file that was read, the user's
prompt, recorded evidence. It is also traced when it is a simple derivation of
source numbers (difference, ratio, relative change, mean of a run of values).

Precision matters more than recall here: a false alarm costs the user's trust,
so anything that is not a reported quantity (code, URLs, DOIs, dates, versions,
section numbers, declared estimates) is skipped.
"""
import os
import re
from dataclasses import dataclass

_SCRUB = [
    re.compile(r"```.*?```", re.S),                       # fenced code
    re.compile(r"`[^`\n]*`"),                             # inline code
    re.compile(r"https?://\S+"),                          # URLs
    re.compile(r"\b10\.\d{4,9}/\S+"),                     # DOIs
    re.compile(r"\b(?:arXiv:)?\d{4}\.\d{4,5}(?:v\d+)?\b", re.I),  # arXiv ids
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b"),  # ISO dates
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),          # clock times
    re.compile(r"\b[A-Za-z]:\\\S+|(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+"),  # paths
    re.compile(r"[\w.-]+\.(?:py|json|csv|log|txt|md|yaml|yml|toml|pt|ckpt)\b"),  # filenames
]

# words before a number that make it a label, not a quantity
_LABEL = re.compile(
    r"(?:^|[^\w])(?:section|sec\.|§|figure|fig\.|table|tab\.|eq\.|equation|chapter|ch\.|version|"
    r"v|python|pp\.|appendix|lemma|theorem|thm\.|definition|def\.|corollary|proposition|prop\.)\s*$",
    re.I,
)
# labels that only name integers ("seed 3", "epoch 10"); "seed 0.818" is still a quantity
_LABEL_INT = re.compile(
    r"(?:^|[^\w])(?:step|line|lines|page|p\.|issue|pr|#|item|claim|run|seed|iteration|iter|epoch|phase|"
    r"round|trial|layer|gpu|node|rank|chunk|batch|part|no\.)\s*$",
    re.I,
)
_ESTIMATE = re.compile(r"(?:~|≈|approx\.?\s*|estimated\s+|est\.\s*)$", re.I)

_NUM = re.compile(r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?%?(?![\w])")
_RAW_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


@dataclass
class Token:
    raw: str
    value: float
    tol: float


def _token(raw: str) -> Token:
    core = raw.rstrip("%").replace(",", "")
    mant = re.split(r"[eE]", core)[0]
    dec = len(mant.split(".")[1]) if "." in mant else 0
    exp = int(re.split(r"[eE]", core)[1]) if re.search(r"[eE]", core) else 0
    return Token(raw, float(core), 0.5 * 10 ** (exp - dec))


def scrub(text: str) -> str:
    for pat in _SCRUB:
        text = pat.sub(" ", text)
    return text


def extract(text: str) -> list[Token]:
    """Reported quantities in prose."""
    text = scrub(text or "")
    out = []
    for m in _NUM.finditer(text):
        raw = m.group(0)
        before = text[max(0, m.start() - 16):m.start()]
        if _LABEL.search(before) or _ESTIMATE.search(before):
            continue
        if _LABEL_INT.search(before) and re.fullmatch(r"[-+]?[\d,]+", raw):
            continue
        t = _token(raw)
        if not raw.endswith("%") and "." not in raw and "e" not in raw.lower():
            # whole numbers ("15 minutes", "3 files") are mostly prose, not results:
            # only traced in strict mode, and never small counts or years
            v = abs(int(t.value))
            if not os.environ.get("WARRANT_STRICT") or v < 10 or 1900 <= v <= 2100:
                continue
        out.append(t)
    return out


def source_numbers(text: str, ints_only: bool = False) -> list[float]:
    """Every number in a source. Sources are not scrubbed: a value inside code
    output or a path still counts as produced."""
    out = []
    for x in _RAW_NUM.findall(text or ""):
        if ints_only and not re.fullmatch(r"[-+]?\d+", x):
            continue
        try:
            out.append(float(x))
        except ValueError:
            continue
    return out


def _targets(t: Token):
    # the value itself, or the same value written as a percent / fraction
    return ((t.value, t.tol), (t.value / 100, t.tol / 100), (t.value * 100, t.tol * 100))


def _hit(x: float, t: Token) -> bool:
    return any(abs(abs(x) - abs(c)) <= tol + 1e-12 for c, tol in _targets(t))


_KEYED = re.compile(r"([A-Za-z_][\w./-]*)\s*[:=]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")


def keyed_values(text: str) -> dict[str, list[float]]:
    """`val_acc=0.81`, `loss: 0.4` -> {"val_acc": [0.81], "loss": [0.4]}."""
    out: dict[str, list[float]] = {}
    for k, v in _KEYED.findall(text or ""):
        out.setdefault(k.lower(), []).append(float(v))
    return out


def windows(t: Token) -> list[tuple[float, float]]:
    """Value ranges a source number must fall in to match `t` (sign ignored)."""
    out = []
    for c, tol in _targets(t):
        c = abs(c)
        out += [(c - tol - 1e-12, c + tol + 1e-12), (-c - tol - 1e-12, -c + tol + 1e-12)]
    return out


def trace_all(text: str, find, means: list[tuple[str, float]]) -> list[tuple[Token, tuple[str, str] | None]]:
    """Trace every reported number in `text`. Returns [(token, (label, how) | None)].

    `find(token) -> label | None` looks the value up in the sources.
    `means` are (label, value) pairs: means of values sharing one key.

    Derivations are deliberately narrow, or almost any number would 'trace':
      - mean of the values logged under one key (per-seed `acc=` lines -> mean acc)
      - difference / ratio / relative change of two numbers that are themselves
        traced in the same text ("0.812 vs 0.806, +0.006")
    """
    tokens = extract(text)
    result: list[tuple[Token, tuple[str, str] | None]] = []
    for t in tokens:
        label = find(t)
        hit = (label, "exact") if label else None
        if hit is None:
            hit = next(((lab, "mean") for lab, v in means if _hit(v, t)), None)
        result.append((t, hit))
    anchors = [t.value for t, h in result if h]
    for i, (t, h) in enumerate(result):
        if h is None:
            for a in anchors:
                for b in anchors:
                    if a != b and (_hit(a - b, t) or (b and (_hit(a / b, t) or _hit((a - b) / b, t)))):
                        result[i] = (t, ("derived from other reported numbers", "derived"))
                        break
                if result[i][1]:
                    break
    return result
