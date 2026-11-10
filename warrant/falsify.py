"""Deterministic falsification check. Ported from ROS `loop/falsify.py`.

The verdict on an experiment is decided here, in Python, against a predicate committed
BEFORE the run. The model never votes on it.

A predicate is a list of clauses, each a REFUTATION condition:
    {"metric": "acc", "op": "lt", "of": "baseline", "margin": 0.05}
reads "refuted if observed acc drops below baseline by more than 5%".
`of: absolute` compares to a fixed `threshold`. `mode` ("any"|"all") composes clauses.
"""
from typing import Optional

_OPS = {
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
    "le": lambda a, b: a <= b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


def _apply_margin(op: str, ref: float, margin: float) -> float:
    if not margin:
        return ref
    if op in ("lt", "le"):
        return ref * (1 - margin)
    if op in ("gt", "ge"):
        return ref * (1 + margin)
    return ref  # shortcut: eq/ne ignore margin; add abs tolerance if a real predicate needs it


def _eval_clause(p: dict, observed: dict, baseline: dict) -> Optional[bool]:
    """True = fired (refutes), False = measured and did not fire, None = unresolved.
    None must never collapse to False: a missing metric reading as 'did not refute'
    is exactly how a typo'd predicate marks a hypothesis 'supported'."""
    metric, op = p.get("metric"), p.get("op")
    if not metric or op not in _OPS:
        raise ValueError(f"bad clause (needs metric + valid op): {p!r}")
    actual = observed.get(metric)
    if actual is None:
        return None
    ref = p.get("threshold") if p.get("of", "baseline") == "absolute" else (baseline or {}).get(metric)
    if ref is None:
        return None
    ref = _apply_margin(op, float(ref), float(p.get("margin", 0.0) or 0.0))
    return bool(_OPS[op](float(actual), ref))


def unresolved_metrics(predicate: Optional[list], observed: dict, baseline: dict) -> list:
    out = []
    for p in predicate or []:
        try:
            if _eval_clause(p, observed or {}, baseline or {}) is None:
                out.append(p.get("metric"))
        except ValueError:
            out.append(p.get("metric"))
    return out


def check(predicate: Optional[list], mode: str, observed: dict, baseline: dict) -> str:
    """Return 'refuted' | 'supported' | 'inconclusive'."""
    if not predicate:
        return "inconclusive"  # nothing pre-committed -> cannot be judged
    evals = [_eval_clause(p, observed or {}, baseline or {}) for p in predicate]
    if mode == "all":
        if any(e is None for e in evals):
            return "inconclusive"
        return "refuted" if all(evals) else "supported"
    if any(e is True for e in evals):
        return "refuted"
    if any(e is None for e in evals):
        return "inconclusive"
    return "supported"
