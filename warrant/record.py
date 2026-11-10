"""The shared record: an append-only, hash-chained event log in SQLite.

Events are never updated or deleted. Current state (question, claims, evidence,
verdicts, graveyard) is derived by folding events in order. Each row stores the hash
of the previous row, so any rewrite of history breaks `verify_chain()`.

Observations (tool outputs captured by hooks) are events too; their full text lives in
`.warrant/obs/<seq>.txt` (sha256 in the event) and their numbers are indexed in side
tables for fast lookup. The index is derived data and can be rebuilt from the files.
"""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from .provenance import window_means

KINDS = {"question", "claim", "evidence", "predict", "result", "kill", "retract", "observe", "wrote"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    prev TEXT NOT NULL,
    hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS obs_nums (value REAL NOT NULL, obs INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS obs_nums_v ON obs_nums(value);
CREATE TABLE IF NOT EXISTS obs_keys (key TEXT NOT NULL, value REAL NOT NULL, obs INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS obs_means (label TEXT NOT NULL, value REAL NOT NULL, obs INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS obs_means_v ON obs_means(value);
"""

MAX_OBS_BYTES = 2_000_000
MAX_OBS_NUMS = 20_000


def default_path(cwd: str | None = None) -> Path:
    return Path(os.environ.get("WARRANT_DIR") or Path(cwd or Path.cwd()) / ".warrant") / "record.db"


def _digest(prev: str, kind: str, body: str) -> str:
    return hashlib.sha256(f"{prev}\n{kind}\n{body}".encode()).hexdigest()


class Record:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()

    @property
    def dir(self) -> Path:
        return self.path.parent

    def _conn(self) -> sqlite3.Connection:
        self.dir.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(self.path, timeout=10)
        c.executescript(_SCHEMA)
        return c

    def create(self) -> None:
        self._conn().close()

    def exists(self) -> bool:
        return self.path.exists()

    def _append(self, c: sqlite3.Connection, kind: str, body: dict) -> int:
        if kind not in KINDS:
            raise ValueError(f"unknown event kind: {kind}")
        text = json.dumps(body, sort_keys=True)
        row = c.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row[0] if row else ""
        cur = c.execute(
            "INSERT INTO events (ts, kind, body, prev, hash) VALUES (?,?,?,?,?)",
            (time.time(), kind, text, prev, _digest(prev, kind, text)),
        )
        return cur.lastrowid

    def append(self, kind: str, **body) -> int:
        with closing(self._conn()) as c, c:
            return self._append(c, kind, body)

    def observe(self, tool: str, label: str, text: str, nums: list[float],
                keyed: dict[str, list[float]]) -> int:
        """Store a captured tool output and index its numbers."""
        data = text.encode("utf-8", errors="replace")[:MAX_OBS_BYTES]
        sha = hashlib.sha256(data).hexdigest()
        with closing(self._conn()) as c, c:
            seq = self._append(c, "observe", {"tool": tool, "label": label[:200], "sha": sha})
            (self.dir / "obs").mkdir(exist_ok=True)
            (self.dir / "obs" / f"{seq}.txt").write_bytes(data)
            c.executemany("INSERT INTO obs_nums VALUES (?,?)", [(v, seq) for v in nums[:MAX_OBS_NUMS]])
            c.executemany("INSERT INTO obs_keys VALUES (?,?,?)",
                          [(k, v, seq) for k, vs in keyed.items() for v in vs[:1000]])
            c.executemany("INSERT INTO obs_means VALUES (?,?,?)",
                          [(lab, v, seq) for lab, v in window_means(text)])
            return seq

    def find_number(self, ranges: list[tuple[float, float]]) -> tuple[int, str] | None:
        """Most recent observation holding a value inside any of `ranges`."""
        return self._find("obs_nums", ranges)

    def find_mean(self, ranges: list[tuple[float, float]]) -> tuple[int, str] | None:
        """Most recent observation with a plausible reported mean inside `ranges`."""
        return self._find("obs_means", ranges)

    def _find(self, table: str, ranges: list[tuple[float, float]]) -> tuple[int, str] | None:
        if not self.exists():
            return None
        q = " OR ".join("(value BETWEEN ? AND ?)" for _ in ranges)
        args = [x for r in ranges for x in r]
        with closing(self._conn()) as c:
            row = c.execute(f"SELECT obs FROM {table} WHERE {q} ORDER BY obs DESC LIMIT 1", args).fetchone()
            if not row:
                return None
            body = c.execute("SELECT body FROM events WHERE seq = ?", (row[0],)).fetchone()
        return row[0], json.loads(body[0]).get("label", "")

    def key_means(self) -> list[tuple[str, float]]:
        """Means of values logged under one key: per observation, and across observations."""
        if not self.exists():
            return []
        with closing(self._conn()) as c:
            per = c.execute("SELECT key, obs, AVG(value) FROM obs_keys GROUP BY key, obs HAVING COUNT(*) > 1").fetchall()
            glob = c.execute("SELECT key, AVG(value) FROM obs_keys GROUP BY key "
                             "HAVING COUNT(DISTINCT obs) > 1").fetchall()
        return [(f"mean of {k} in observation #{o}", v) for k, o, v in per] + \
               [(f"mean of {k} across runs", v) for k, v in glob]

    def events(self, kinds: set[str] | None = None) -> list[dict]:
        if not self.exists():
            return []
        with closing(self._conn()) as c:
            rows = c.execute("SELECT seq, ts, kind, body FROM events ORDER BY seq").fetchall()
        return [{"seq": s, "ts": t, "kind": k, **json.loads(b)} for s, t, k, b in rows
                if kinds is None or k in kinds]

    def verify_chain(self) -> bool:
        """Hash chain intact and every observation file unchanged."""
        if not self.exists():
            return True
        with closing(self._conn()) as c:
            rows = c.execute("SELECT seq, kind, body, prev, hash FROM events ORDER BY seq").fetchall()
        prev = ""
        for seq, kind, body, p, h in rows:
            if p != prev or h != _digest(prev, kind, body):
                return False
            if kind == "observe":
                f = self.dir / "obs" / f"{seq}.txt"
                if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != json.loads(body)["sha"]:
                    return False
            prev = h
        return True

    def written_paths(self) -> set[str]:
        return {e["path"] for e in self.events({"wrote"})}

    def state(self) -> dict:
        """Fold events into current state (observations excluded; they are indexed)."""
        st = {"question": None, "hypothesis": None, "claims": {}, "graveyard": [], "observations": 0}
        for e in self.events():
            k, seq = e["kind"], e["seq"]
            if k == "observe":
                st["observations"] += 1
            elif k == "question":
                st["question"], st["hypothesis"] = e.get("text"), e.get("hypothesis")
            elif k == "claim":
                n = len(st["claims"]) + 1  # claims numbered 1, 2, 3 for humans
                st["claims"][n] = {"id": n, "text": e["text"], "evidence": [],
                                   "predict": None, "result": None, "retracted": False}
            elif k in ("evidence", "predict", "result", "retract"):
                cl = st["claims"].get(e.get("claim"))
                if cl is None:
                    continue
                if k == "evidence":
                    cl["evidence"].append(e)
                elif k == "predict":
                    cl["predict"] = e
                elif k == "result":
                    cl["result"] = e
                else:
                    cl["retracted"] = True
            elif k == "kill":
                st["graveyard"].append({"id": seq, "idea": e["idea"], "why": e.get("why", ""),
                                        "claim": e.get("claim")})
        return st
