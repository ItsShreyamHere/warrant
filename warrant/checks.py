"""Code-decided checks. No model calls anywhere in this file.

status per claim:
  green  - evidence verified by code, wording fits the evidence
  yellow - no evidence, or evidence only a human/model could judge
  red    - evidence contradicts, was tampered with, or wording overstates it
"""
import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path

from . import falsify

GREEN, YELLOW, RED = "green", "yellow", "red"

# wording that needs evidence of a given strength
_SIGNIF = re.compile(r"\b(statistically\s+)?significant(ly)?\b", re.I)
_PROOF = re.compile(r"\b(prove[sn]?|proof that|proven)\b", re.I)
_WIN = re.compile(r"\b(outperform\w*|beats?|better than|improve[sd]?|improvement|state[- ]of[- ]the[- ]art|sota)\b", re.I)
_ABSOLUTE = re.compile(r"\b(always|never|guarantee[sd]?|definitive(ly)?|clearly|obviously|undeniabl[ey])\b", re.I)
_HEDGE = re.compile(r"\b(may|might|could|possibly|perhaps|suggests?|appears? to)\b", re.I)

_NUM = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?%?")


def sha256_file(path: str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def numbers_in(text: str) -> list[str]:
    """Numbers worth tracing. Skips bare small integers and year-like values."""
    out = []
    for m in _NUM.findall(text or ""):
        core = m.rstrip("%").lstrip("+-")
        if "." not in core and not m.endswith("%"):
            v = int(core)
            if v < 10 or 1900 <= v <= 2100:
                continue  # counts, list items, years: too noisy to trace
        out.append(m)
    return out


def _traced(token: str, known: list[float]) -> bool:
    core = token.rstrip("%")
    val = float(core)
    dec = len(core.split(".")[1]) if "." in core else 0
    tol = 0.5 * 10 ** -dec  # rounding the writer could have done
    # same value, or the same value written as a percent / fraction
    cands = [(val, tol), (val / 100, tol / 100), (val * 100, tol * 100)]
    return any(abs(c - k) <= t + 1e-12 for c, t in cands for k in known)


def _run_check(ev: dict) -> tuple[str, list[str]]:
    log = ev.get("log")
    if not log:
        return YELLOW, ["run evidence has no log file"]
    now = sha256_file(log)
    if now is None:
        return RED, [f"log not found: {log}"]
    if ev.get("sha") and now != ev["sha"]:
        return RED, [f"log changed after it was attached: {log}"]
    text = Path(log).read_text(errors="replace")
    logged = [float(x.rstrip("%")) for x in _NUM.findall(text)]
    missing = [f"{k}={v}" for k, v in (ev.get("metrics") or {}).items()
               if not _traced(str(v), logged)]
    if missing:
        return RED, [f"metric not found in log: {', '.join(missing)}"]
    return GREEN, []


def _seeds(claim: dict) -> int:
    return max([int(e.get("seeds") or 1) for e in claim["evidence"] if e.get("type") == "run"] or [0])


def _pval(claim: dict) -> float | None:
    ps = [float(e["p"]) for e in claim["evidence"] if e.get("p") is not None]
    return min(ps) if ps else None


def evaluate(claim: dict) -> dict:
    """Return {"status", "reasons", "notes"} for one folded claim."""
    reasons: list[tuple[str, str]] = []  # (severity, text)
    notes: list[str] = []
    verified = False

    for ev in claim["evidence"]:
        t = ev.get("type")
        if t == "run":
            s, why = _run_check(ev)
            verified |= s == GREEN
            reasons += [(s, w) for w in why]
        else:
            reasons.append((YELLOW, f"{t} evidence not machine-checked yet"))

    if claim.get("predict"):
        res = claim.get("result")
        if not res:
            reasons.append((YELLOW, "pre-registered, no result yet"))
        else:
            v = res.get("verdict")
            if v == "refuted":
                reasons.append((RED, "refuted by its own pre-registered predicate"))
            elif v == "inconclusive":
                miss = res.get("unresolved") or []
                reasons.append((YELLOW, "inconclusive" + (f": missing {', '.join(miss)}" if miss else "")))
            else:
                verified = True

    text, seeds, p = claim["text"], _seeds(claim), _pval(claim)
    if _SIGNIF.search(text) and (seeds < 3 or p is None or p >= 0.05):
        reasons.append((RED, f"says 'significant' but evidence has {seeds} seed(s), p={p}"))
    if _PROOF.search(text) and not any(e.get("type") == "proof" for e in claim["evidence"]):
        reasons.append((RED, "says 'proves' with no proof evidence"))
    if _WIN.search(text) and verified and seeds < 3 and not claim.get("result"):
        reasons.append((RED, f"claims a win on {seeds} seed(s); need >=3 or a pre-registered predicate"))
    if _ABSOLUTE.search(text):
        notes.append("absolute wording: check it is warranted")
    if _HEDGE.search(text) and verified and seeds >= 3 and p is not None and p < 0.01:
        notes.append("possibly understated: evidence is strong, wording is hedged")

    if not claim["evidence"] and not claim.get("predict"):
        reasons.append((YELLOW, "no evidence attached"))

    sev = {s for s, _ in reasons}
    status = RED if RED in sev else (GREEN if verified and YELLOW not in sev else YELLOW)
    return {"status": status, "reasons": [w for _, w in reasons], "notes": notes}


def known_numbers(state: dict) -> list[float]:
    """Every number the record can account for: metrics, logs, predicates, results."""
    known: list[float] = []
    for c in state["claims"].values():
        for ev in c["evidence"]:
            for k in ("seeds", "p", "std"):
                if ev.get(k) is not None:
                    known.append(float(ev[k]))
            known += [float(v) for v in (ev.get("metrics") or {}).values()]
            if ev.get("log") and Path(ev["log"]).is_file():
                known += [float(x.rstrip("%")) for x in _NUM.findall(Path(ev["log"]).read_text(errors="replace"))]
        for key in ("predict", "result"):
            blob = c.get(key) or {}
            for d in (blob.get("observed"), blob.get("baseline")):
                known += [float(v) for v in (d or {}).values()]
            for cl in blob.get("predicate") or []:
                for k in ("threshold", "margin"):
                    if cl.get(k) is not None:
                        known.append(float(cl[k]))
    return known


def untraced_numbers(text: str, state: dict) -> list[str]:
    known = known_numbers(state)
    return [n for n in numbers_in(text) if not _traced(n, known)]


def graveyard_match(idea: str, state: dict, threshold: float = 0.6) -> dict | None:
    """Closest dead idea if `idea` looks like a re-proposal."""
    a = idea.lower()
    wa = set(re.findall(r"\w+", a))
    best, score = None, 0.0
    for g in state["graveyard"]:
        b = g["idea"].lower()
        wb = set(re.findall(r"\w+", b))
        jac = len(wa & wb) / max(1, len(wa | wb))
        s = max(SequenceMatcher(None, a, b).ratio(), jac)
        if s > score:
            best, score = g, s
    return best if score >= threshold else None


def judge(predicate: list, mode: str, observed: dict, baseline: dict) -> tuple[str, list]:
    return falsify.check(predicate, mode, observed, baseline), falsify.unresolved_metrics(predicate, observed, baseline)
