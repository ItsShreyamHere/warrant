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
from . import provenance as prov

GREEN, YELLOW, RED = "green", "yellow", "red"

# wording that needs evidence of a given strength
_SIGNIF = re.compile(r"\b(statistically\s+)?significant(ly)?\b", re.I)
_PROOF = re.compile(r"\b(prove[sn]?|proof that|proven)\b", re.I)
_WIN = re.compile(r"\b(outperform\w*|beats?|better than|improve[sd]?|improvement|state[- ]of[- ]the[- ]art|sota)\b", re.I)
_ABSOLUTE = re.compile(r"\b(always|never|guarantee[sd]?|definitive(ly)?|clearly|obviously|undeniabl[ey])\b", re.I)
_HEDGE = re.compile(r"\b(may|might|could|possibly|perhaps|suggests?|appears? to)\b", re.I)



def sha256_file(path: str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _in_source(value: str, nums: list[float]) -> bool:
    t = prov._token(value)
    return any(lo <= n <= hi for n in nums for lo, hi in prov.windows(t))


def _run_check(ev: dict) -> tuple[str, list[str]]:
    log = ev.get("log")
    if not log:
        return YELLOW, ["run evidence has no log file"]
    now = sha256_file(log)
    if now is None:
        return RED, [f"log not found: {log}"]
    if ev.get("sha") and now != ev["sha"]:
        return RED, [f"log changed after it was attached: {log}"]
    logged = prov.source_numbers(Path(log).read_text(errors="replace"))
    missing = [f"{k}={v}" for k, v in (ev.get("metrics") or {}).items()
               if not _in_source(repr(float(v)), logged)]
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
        elif t == "proof" and ev.get("check"):
            s, why = ev["check"]["status"], ev["check"]["why"]
            if s == GREEN and ev.get("ref") and sha256_file(ev["ref"]) != ev["check"].get("sha"):
                s, why = RED, "proof file changed after it was checked; re-attach it"
            verified |= s == GREEN
            reasons += [] if s == GREEN else [(s, f"proof {ev.get('ref')}: {why}")]
        elif t == "cite" and ev.get("check"):
            s, why = ev["check"]["status"], ev["check"]["why"]
            verified |= s == GREEN
            reasons += [] if s == GREEN else [(s, f"citation {ev.get('ref')}: {why}")]
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
    if _PROOF.search(text) and not any(e.get("type") == "proof" and (e.get("check") or {}).get("status") == GREEN
                                       for e in claim["evidence"]):
        reasons.append((RED, "says 'proves' with no checked proof"))
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


def record_numbers(state: dict) -> list[float]:
    """Numbers held in the record itself: question, metrics, logs, predicates, results."""
    known: list[float] = prov.source_numbers(state.get("question") or "")
    for c in state["claims"].values():
        for ev in c["evidence"]:
            for k in ("seeds", "p", "std"):
                if ev.get(k) is not None:
                    known.append(float(ev[k]))
            known += [float(v) for v in (ev.get("metrics") or {}).values()]
            if ev.get("log") and Path(ev["log"]).is_file():
                known += prov.source_numbers(Path(ev["log"]).read_text(errors="replace"))
        for key in ("predict", "result"):
            blob = c.get(key) or {}
            for d in (blob.get("observed"), blob.get("baseline")):
                known += [float(v) for v in (d or {}).values()]
            for cl in blob.get("predicate") or []:
                for k in ("threshold", "margin"):
                    if cl.get(k) is not None:
                        known.append(float(cl[k]))
    return known


def trace_text(text: str, rec, state: dict | None = None):
    """[(token, (label, how) | None)] for every reported number in `text`."""
    state = state or rec.state()
    mem = record_numbers(state)

    def find(t):
        rs = prov.windows(t)
        if any(lo <= n <= hi for n in mem for lo, hi in rs):
            return "the warrant record"
        hit = rec.find_number(rs)
        if hit:
            return f"observation #{hit[0]}: {hit[1]}"
        hit = rec.find_mean(rs)
        return (f"observation #{hit[0]}: {hit[1]}", "mean") if hit else None

    return prov.trace_all(text, find, rec.key_means())


def untraced_numbers(text: str, rec, state: dict | None = None) -> list[str]:
    return [t.raw for t, h in trace_text(text, rec, state) if h is None]


_STOP = set("a an the of on in to for with and or is are be by over than vs our we it this that "
             "at as from into using use via its their".split())


def _content_words(s: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z][a-z0-9_-]+", s):
        if w in _STOP:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def graveyard_match(idea: str, state: dict, threshold: float = 0.6) -> dict | None:
    """Closest dead idea if `idea` looks like a re-proposal."""
    a = idea.lower()
    wa = _content_words(a)
    best, score = None, 0.0
    for g in state["graveyard"]:
        b = g["idea"].lower()
        wb = _content_words(b)
        # containment: the dead idea's core words reappearing inside a new, longer idea
        cont = len(wa & wb) / max(1, min(len(wa), len(wb)))
        s = max(SequenceMatcher(None, a, b).ratio(), cont)
        if s > score:
            best, score = g, s
    return best if score >= threshold else None


def judge(predicate: list, mode: str, observed: dict, baseline: dict) -> tuple[str, list]:
    return falsify.check(predicate, mode, observed, baseline), falsify.unresolved_metrics(predicate, observed, baseline)
