"""Recompute reported statistics. Pure stdlib math, no scipy.

statcheck-style: a reported test statistic and df imply a p-value. If the reported p cannot
come from the reported statistic (allowing for rounding of the statistic), it is an
inconsistency; if the significance decision at .05 flips, it is a gross inconsistency.
(Method: Nuijten et al. 2016, Behav. Res. Methods, doi:10.3758/s13428-015-0664-2.)

GRIM: a mean of n integer-valued responses must equal k/n for some integer k. Reported means
that no k can produce are impossible. (Brown & Heathers 2017, doi:10.1177/1948550616673876.)
"""
import math
import re

# --- special functions -----------------------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (modified Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def gammaincc(s: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(s, x)."""
    if x <= 0:
        return 1.0
    if x < s + 1:  # series for P, then 1 - P
        term = total = 1.0 / s
        n = s
        for _ in range(1000):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return 1.0 - total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    tiny = 1e-300  # continued fraction for Q
    b, c, d = x + 1 - s, 1 / tiny, 1 / (x + 1 - s)
    h = d
    for i in range(1, 1000):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > tiny else tiny)
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


# --- p-values ----------------------------------------------------------------------

def p_t(t: float, df: float) -> float:
    return betainc(df / 2, 0.5, df / (df + t * t))


def p_f(f: float, d1: float, d2: float) -> float:
    return betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * f)) if f > 0 else 1.0


def p_chi2(x: float, df: float) -> float:
    return gammaincc(df / 2, x / 2)


def p_z(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def p_r(r: float, df: float) -> float:
    if abs(r) >= 1:
        return 0.0
    return p_t(r * math.sqrt(df / (1 - r * r)), df)


# --- extraction --------------------------------------------------------------------

_NUM = r"[-−–]?\s*\d*\.?\d+"
# p, optionally in scientific notation: p = 4.7 × 10^-5, p = 4.7e-5, p < 10^{-3}
_P = (r"p\s*([<>=≤≥])\s*(\d*\.\d+|\d+)"
      r"(?:\s*(?:×|x|\*|·)\s*10\s*\^?\s*\(?\s*([-−–]\s*\d+)|[eE]\s*([-−–]?\s*\d+))?")
# reported p-values adjusted for multiple comparisons are larger than the raw p by design
_CORRECTED = re.compile(r"bonferroni|holm|šid[aá]k|sidak|benjamini|hochberg|false discovery|\bfdr\b|"
                        r"tukey|adjusted p|corrected p|p_?\{?adj|multiple comparison", re.I)
_TESTS = [
    ("t", re.compile(rf"\bt\s*\(\s*(\d+(?:\.\d+)?)\s*\)\s*=\s*({_NUM})\s*[,;]\s*{_P}", re.I)),
    ("F", re.compile(rf"\bF\s*\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)\s*=\s*({_NUM})\s*[,;]\s*{_P}")),
    ("chi2", re.compile(rf"(?:χ\s*2|χ²|chi\s*\^?\s*2|chi-square[d]?|X\s*\^?\s*2)\s*\(\s*(\d+)\s*(?:,\s*N\s*=\s*\d+\s*)?\)"
                        rf"\s*=\s*({_NUM})\s*[,;]\s*{_P}", re.I)),
    ("r", re.compile(rf"\br\s*\(\s*(\d+)\s*\)\s*=\s*({_NUM})\s*[,;]\s*{_P}")),
    ("z", re.compile(rf"\bz\s*=\s*({_NUM})\s*[,;]\s*{_P}", re.I)),
]


def _f(s: str) -> float:
    return float(s.replace("−", "-").replace("–", "-").replace(" ", ""))


def _dec(s: str) -> int:
    s = s.strip().lstrip("-−–").strip()
    return len(s.split(".")[1]) if "." in s else 0


def _p_range(kind: str, args: list[float], stat_raw: str) -> tuple[float, float]:
    """p-values reachable by any statistic that rounds to the reported one."""
    stat = abs(_f(stat_raw))
    half = 0.5 * 10 ** -_dec(stat_raw)
    lo_s, hi_s = max(0.0, stat - half), stat + half

    def p(x):
        if kind == "t":
            return p_t(x, args[0])
        if kind == "F":
            return p_f(x, args[0], args[1])
        if kind == "chi2":
            return p_chi2(x, args[0])
        if kind == "r":
            return p_r(min(x, 0.999999), args[0])
        return p_z(x)
    a, b = p(lo_s), p(hi_s)
    return min(a, b), max(a, b)


def statcheck(text: str, alpha: float = 0.05) -> list[dict]:
    """Every APA-style test in `text`, with its recomputed p and a verdict."""
    out = []
    corrected_paper = bool(_CORRECTED.search(text))
    one_tailed_paper = bool(re.search(r"one[- ]?(?:tailed|sided)|directional (?:test|hypothes)", text, re.I))
    for kind, rx in _TESTS:
        for m in rx.finditer(text):
            g = m.groups()
            op, p_raw, e1, e2 = g[-4:]
            rest = g[:-4]
            stat_raw = rest[-1]
            args = [float(x) for x in rest[:-1]]
            if kind == "r" and abs(_f(stat_raw)) > 1:
                continue
            exp = int(_f(e1 or e2)) if (e1 or e2) else 0
            p_rep = float(p_raw) * 10 ** exp
            if p_rep > 1:
                continue  # not a p-value as parsed (layout we can't read); never guess
            lo, hi = _p_range(kind, args, stat_raw)
            p_half = 0.5 * 10 ** (-_dec(p_raw) + exp)
            if op in "=":
                ok = lo <= p_rep + p_half and hi >= p_rep - p_half
                rep_sig = p_rep < alpha or (p_rep == alpha and False)
            elif op in "<≤":
                ok = lo < p_rep or (op == "≤" and lo <= p_rep)
                rep_sig = p_rep <= alpha
            else:
                ok = hi > p_rep
                rep_sig = False
            comp_sig = hi < alpha if lo < alpha else False
            p_mid = (lo + hi) / 2
            # reported p above the raw p in a paper that adjusts for multiple comparisons: an
            # adjusted p-value, not an error (statcheck's best-known false positive)
            adjusted = not ok and corrected_paper and p_rep > hi
            # one-tailed t/z/r: half the two-tailed p, when the paper says it tests directionally
            one_tailed = False
            if not ok and not adjusted and one_tailed_paper and kind in ("t", "z", "r"):
                if op == "=":
                    one_tailed = lo / 2 <= p_rep + p_half and hi / 2 >= p_rep - p_half
                elif op in "<≤":
                    one_tailed = lo / 2 < p_rep
            if adjusted or one_tailed:
                ok = True
            gross = (not ok) and (rep_sig != (p_mid < alpha))
            shown = p_raw + (f"e{exp}" if exp else "")
            out.append({"test": kind, "text": m.group(0).strip(), "reported_p": f"p {op} {shown}",
                        "computed_p": round(p_mid, 4) if p_mid >= 1e-4 else float(f"{p_mid:.2e}"),
                        "consistent": ok, "gross": gross and not ok, "comp_sig": comp_sig,
                        "adjusted": adjusted, "one_tailed": one_tailed})
    return out


_GRIM = re.compile(r"\bM\s*=\s*(\d+\.\d+)\s*(?:,\s*SD\s*=\s*\d*\.?\d+\s*)?[,;)]?\s*(?:\(?\s*)?n\s*=\s*(\d+)", re.I)


def grim(text: str) -> list[dict]:
    """Means reported with their n that no integer total can produce (integer-valued data only)."""
    out = []
    for m in _GRIM.finditer(text):
        mean, n = m.group(1), int(m.group(2))
        dec = len(mean.split(".")[1])
        if n <= 0 or n >= 10 ** dec:
            continue  # GRIM has no power once n reaches 10^decimals
        target = float(mean)
        k = round(target * n)
        possible = any(round((k + d) / n, dec) == round(target, dec) for d in (-1, 0, 1))
        if not possible:
            out.append({"text": m.group(0).strip(), "mean": mean, "n": n,
                        "detail": f"no integer total / {n} rounds to {mean}"})
    return out
