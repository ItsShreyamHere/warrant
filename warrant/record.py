"""The shared record: an append-only, hash-chained event log in SQLite.

Events are never updated or deleted. Current state (question, claims, evidence,
verdicts, graveyard) is derived by folding events in order. Each row stores the hash
of the previous row, so any rewrite of history breaks `verify_chain()`.
"""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

KINDS = {"question", "claim", "evidence", "predict", "result", "kill", "retract"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    prev TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""


def default_path(cwd: str | None = None) -> Path:
    return Path(os.environ.get("WARRANT_DIR") or Path(cwd or Path.cwd()) / ".warrant") / "record.db"


def _digest(prev: str, kind: str, body: str) -> str:
    return hashlib.sha256(f"{prev}\n{kind}\n{body}".encode()).hexdigest()


class Record:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()

    def _conn(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(self.path)
        c.execute(_SCHEMA)
        return c

    def exists(self) -> bool:
        return self.path.exists()

    def append(self, kind: str, **body) -> int:
        if kind not in KINDS:
            raise ValueError(f"unknown event kind: {kind}")
        text = json.dumps(body, sort_keys=True)
        with closing(self._conn()) as c, c:
            row = c.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            prev = row[0] if row else ""
            cur = c.execute(
                "INSERT INTO events (ts, kind, body, prev, hash) VALUES (?,?,?,?,?)",
                (time.time(), kind, text, prev, _digest(prev, kind, text)),
            )
            return cur.lastrowid

    def events(self) -> list[dict]:
        if not self.exists():
            return []
        with closing(self._conn()) as c:
            rows = c.execute("SELECT seq, ts, kind, body FROM events ORDER BY seq").fetchall()
        return [{"seq": s, "ts": t, "kind": k, **json.loads(b)} for s, t, k, b in rows]

    def verify_chain(self) -> bool:
        if not self.exists():
            return True
        with closing(self._conn()) as c:
            rows = c.execute("SELECT kind, body, prev, hash FROM events ORDER BY seq").fetchall()
        prev = ""
        for kind, body, p, h in rows:
            if p != prev or h != _digest(prev, kind, body):
                return False
            prev = h
        return True

    def state(self) -> dict:
        """Fold events into current state."""
        st = {"question": None, "hypothesis": None, "claims": {}, "graveyard": []}
        for e in self.events():
            k, seq = e["kind"], e["seq"]
            if k == "question":
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
