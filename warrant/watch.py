"""`warrant watch`: sentinels that audit live experiment output, at zero token cost.

Plain code tails log / CSV / JSONL files and checks every new value as it lands:

  red     nonfinite   a metric became NaN or inf
  red     crash       a traceback, OOM, kill or segfault in the log
  red     diverge     a loss climbed past 3x its best value
  yellow  spike       a value more than 6 robust deviations from its recent median
  yellow  plateau     no improvement over the last 30 values of a metric
  yellow  overfit     validation loss rising while training loss keeps falling
  yellow  too_good    a val/test score >= 0.999: check for leakage
  yellow  stale       the file stopped growing: the run may have died
  yellow  refuted     a pre-registered predicate is already refuted mid-run

A model is never involved in watching. Alerts go to .warrant/alerts.jsonl; the agent sees
one short line per new alert on its next turn (hooks), and an optional `--wake` command
is run for red alerts only, under a per-hour budget. Watched output is also recorded as
evidence, so numbers the agent later reports from these runs trace automatically.
"""
import json
import math
import re
import subprocess
import time
from collections import deque
from pathlib import Path
from statistics import median

from . import falsify
from . import provenance as prov

_NONFINITE = re.compile(r"([A-Za-z_][\w./-]*)\s*[:=]\s*[-+]?(nan|inf(?:inity)?)\b", re.I)
_CRASH = re.compile(r"Traceback \(most recent call last\)|CUDA out of memory|OutOfMemoryError|"
                    r"\bKilled\b|Segmentation fault|core dumped|RuntimeError:|Error: .*exit", re.I)
_STEP_KEYS = ("step", "global_step", "iter", "iteration", "epoch", "batch")
_HIGHER_BETTER = re.compile(r"acc|f1|auc|precision|recall|bleu|rouge|score|map|iou|r2", re.I)
_EVAL_SCORE = re.compile(r"^(val|valid|validation|test|eval|dev)[\w./-]*(acc|f1|auc|precision|recall)", re.I)
_LOSSY = re.compile(r"loss|error|perplexity|ppl|mse|mae|rmse", re.I)

HISTORY = 2000


def _rows(path: Path, chunk: str) -> list[dict[str, float]]:
    """New text -> one {metric: value} dict per log line / CSV row / JSON object."""
    out = []
    if path.suffix == ".jsonl":
        for line in chunk.splitlines():
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append({k.lower(): float(v) for k, v in obj.items()
                            if isinstance(v, (int, float)) and not isinstance(v, bool)})
        return out
    for line in chunk.splitlines():
        kv = prov.keyed_values(line)
        if kv:
            out.append({k: v[-1] for k, v in kv.items()})
    return out


def _csv_rows(header: list[str], chunk: str) -> list[dict[str, float]]:
    out = []
    for line in chunk.splitlines():
        cells = [c.strip() for c in line.split(",")]
        if len(cells) != len(header):
            continue
        row = {}
        for k, c in zip(header, cells):
            try:
                row[k] = float(c)
            except ValueError:
                pass
        if row:
            out.append(row)
    return out


class Watch:
    def __init__(self, rec, paths: list[str], stale: float = 600, wake: str | None = None,
                 max_wakes: int = 3, log=print):
        self.rec, self.globs, self.stale, self.wake = rec, paths, stale, wake
        self.max_wakes, self.log = max_wakes, log
        self.offsets: dict[Path, int] = {}
        self.headers: dict[Path, list[str]] = {}
        self.series: dict[tuple[str, str], deque] = {}
        self.grew: dict[Path, float] = {}
        self.seen: set = set()
        self.wakes: deque = deque()
        f = rec.dir / "alerts.jsonl"
        if f.is_file():  # don't re-alert across restarts
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    self.seen.add(json.loads(line)["id"])
                except (ValueError, KeyError):
                    pass

    # -- files ------------------------------------------------------------------
    def files(self) -> list[Path]:
        out = []
        for g in self.globs:
            p = Path(g)
            out += [p] if p.is_file() else sorted(Path().glob(g)) if any(c in g for c in "*?[") else \
                [f for f in p.rglob("*") if f.suffix in (".log", ".txt", ".csv", ".jsonl", ".out")] if p.is_dir() else []
        return out

    def poll(self) -> list[dict]:
        alerts = []
        now = time.time()
        for path in self.files():
            try:
                size = path.stat().st_size
            except OSError:
                continue
            start = self.offsets.get(path, 0)
            if size < start:
                start = 0  # truncated / rotated
            if size == start:
                last = self.grew.get(path)
                if last and now - last > self.stale:
                    alerts.append(self.alert("yellow", "stale", path, "",
                                             f"no new output for {int(now - last)}s: the run may have died"))
                continue
            with path.open("rb") as fh:
                fh.seek(start)
                chunk = fh.read(size - start).decode("utf-8", errors="replace")
            cut = chunk.rfind("\n") + 1  # only complete lines
            if not cut:
                continue
            chunk = chunk[:cut]
            self.offsets[path] = start + len(chunk.encode("utf-8"))
            self.grew[path] = now
            alerts += self.check_chunk(path, chunk)
        alerts = [a for a in alerts if a]  # None = already alerted (deduped)
        for a in alerts:
            self.emit(a)
        return alerts

    # -- sentinels ----------------------------------------------------------------
    def check_chunk(self, path: Path, chunk: str) -> list[dict]:
        out = []
        self.rec.observe("watch", f"watch: {path}", chunk, prov.source_numbers(chunk), prov.keyed_values(chunk))
        for m in _NONFINITE.finditer(chunk):
            out.append(self.alert("red", "nonfinite", path, m.group(1).lower(), f"{m.group(1)} became {m.group(2)}"))
        for m in _CRASH.finditer(chunk):
            line = chunk[m.start():].splitlines()[0][:120]
            out.append(self.alert("red", "crash", path, m.group(0)[:30], line))
        if path.suffix == ".csv":
            if path not in self.headers:
                first, _, rest = chunk.partition("\n")
                self.headers[path] = [h.strip().lower() for h in first.split(",")]
                chunk = rest
            rows = _csv_rows(self.headers[path], chunk)
        else:
            rows = _rows(path, chunk)
        for row in rows:
            for key, val in row.items():
                if key in _STEP_KEYS or not math.isfinite(val):
                    continue
                s = self.series.setdefault((str(path), key), deque(maxlen=HISTORY))
                s.append(val)
                out += self.check_series(path, key, s)
        out += self.check_overfit(path)
        out += self.check_predicates()
        return [a for a in out if a]

    def check_series(self, path, key, s) -> list:
        out, v = [], s[-1]
        lossy = bool(_LOSSY.search(key)) and not _HIGHER_BETTER.search(key)
        if lossy and len(s) >= 5:
            best = min(s)
            if best > 0 and v > 3 * best and v > s[0]:
                out.append(self.alert("red", "diverge", path, key, f"{key} = {v:g}, more than 3x its best {best:g}"))
        if _EVAL_SCORE.search(key) and 0.999 <= v <= 1.0:
            out.append(self.alert("yellow", "too_good", path, key,
                                  f"{key} = {v:g}: near-perfect held-out score, check for leakage"))
        diverged = f"diverge:{path}:{key}" in self.seen
        if len(s) >= 20 and not diverged:  # a diverging metric already has its red alert
            recent = list(s)[-51:-1]
            med = median(recent)
            mad = median(abs(x - med) for x in recent) or 1e-12
            if abs(v - med) / (1.4826 * mad) > 6 and abs(v - med) > 1e-9 * max(1, abs(med)):
                out.append(self.alert("yellow", "spike", path, f"{key}@{len(s) // 100}",  # at most 1 per 100 values
                                      f"{key} = {v:g} vs recent median {med:g}"))
        if len(s) >= 60 and len(s) % 30 == 0:
            higher = bool(_HIGHER_BETTER.search(key))
            old, new = list(s)[:-30], list(s)[-30:]
            best_old = max(old) if higher else min(old)
            best_new = max(new) if higher else min(new)
            gain = (best_new - best_old) if higher else (best_old - best_new)
            if gain <= 1e-3 * max(abs(best_old), 1e-12):
                out.append(self.alert("yellow", "plateau", path, f"{key}@{len(s)}",
                                      f"{key} has not improved over its last 30 values (best {best_old:g})"))
        return out

    def check_overfit(self, path) -> list:
        out = []
        keys = {k for (p, k) in self.series if p == str(path)}
        for k in keys:
            m = re.match(r"^(val|valid|validation|eval|dev)[_./-]?(.*loss.*)$", k)
            if not m:
                continue
            tk = next((t for t in (f"train_{m.group(2)}", f"train/{m.group(2)}", m.group(2), "loss") if t in keys), None)
            if not tk:
                continue
            va, tr = list(self.series[(str(path), k)]), list(self.series[(str(path), tk)])
            if len(va) >= 5 and len(tr) >= 5:
                v5, t5 = va[-5:], tr[-5:]
                if all(b > a for a, b in zip(v5, v5[1:])) and t5[-1] < t5[0]:
                    out.append(self.alert("yellow", "overfit", path, k,
                                          f"{k} rose 4 evals in a row while {tk} kept falling"))
        return out

    def check_predicates(self) -> list:
        out = []
        st = self.rec.state()
        latest = {}
        for (p, k), s in self.series.items():
            latest[k] = s[-1]
        for c in st["claims"].values():
            p = c.get("predict")
            if not p or c.get("result"):
                continue
            base = {}
            verdict = falsify.check(p["predicate"], p["mode"], latest, base)
            if verdict == "refuted":
                out.append(self.alert("yellow", "refuted", Path("record"), f"claim{c['id']}",
                                      f"claim #{c['id']} '{c['text'][:60]}': its pre-registered predicate "
                                      "is already refuted by the live values (not final)"))
        return out

    # -- output -------------------------------------------------------------------
    def alert(self, level, sentinel, path, key, msg) -> dict | None:
        aid = f"{sentinel}:{path}:{key}"
        if aid in self.seen:
            return None
        self.seen.add(aid)
        return {"id": aid, "ts": time.time(), "level": level, "sentinel": sentinel,
                "file": str(path), "msg": msg, "delivered": False}

    def emit(self, a: dict) -> None:
        with (self.rec.dir / "alerts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(a) + "\n")
        self.log(f"[{a['level'].upper()}] {a['sentinel']}: {a['msg']} ({a['file']})")
        if a["level"] == "red" and self.wake:
            now = time.time()
            while self.wakes and now - self.wakes[0] > 3600:
                self.wakes.popleft()
            if len(self.wakes) >= self.max_wakes:
                self.log(f"wake budget reached ({self.max_wakes}/hour): not waking an agent")
                return
            self.wakes.append(now)
            card = card_text(a)
            try:
                subprocess.Popen(self.wake, shell=True, stdin=subprocess.PIPE, text=True).communicate(card, timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def run(self, interval: float = 5, once: bool = False) -> None:
        while True:
            self.poll()
            if once:
                return
            time.sleep(interval)


def card_text(a: dict) -> str:
    """The whole context a woken agent gets: one line, ~40 tokens."""
    return f"[warrant watch] {a['level']} {a['sentinel']} in {a['file']}: {a['msg']}"


def pending(rec, limit: int = 5, mark: bool = True) -> list[dict]:
    """Undelivered alerts, red first; optionally mark them delivered."""
    f = rec.dir / "alerts.jsonl"
    if not f.is_file():
        return []
    rows = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    new = [r for r in rows if not r.get("delivered")]
    if not new:
        return []
    picked = sorted(new, key=lambda r: (r["level"] != "red", r["ts"]))[:limit]
    if mark:
        ids = {r["id"] for r in picked}
        for r in rows:
            if r["id"] in ids:
                r["delivered"] = True
        f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return picked
