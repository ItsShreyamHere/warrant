"""Claude Code hook handlers. Each reads the hook JSON on stdin and prints hook JSON.

Quiet by default: with no `.warrant/` record in the project, every hook is a no-op.
"""
import json
import sys

from . import checks
from .record import Record, default_path

MAX_LIST = 8


def _last_assistant_text(transcript_path: str) -> str:
    text = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("type") != "assistant":
                    continue
                parts = (e.get("message") or {}).get("content") or []
                t = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
                if t.strip():
                    text = t
    except OSError:
        return ""
    return text


def anchor(state: dict, full: bool) -> str:
    if not state["question"]:
        return ""
    lines = [f"[warrant] Research question: {state['question']}"]
    if state["hypothesis"]:
        lines.append(f"[warrant] Current hypothesis: {state['hypothesis']}")
    if full:
        counts = {}
        for c in state["claims"].values():
            if not c["retracted"]:
                s = checks.evaluate(c)["status"]
                counts[s] = counts.get(s, 0) + 1
        if counts:
            lines.append("[warrant] Claims: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
        for g in state["graveyard"][-MAX_LIST:]:
            lines.append(f"[warrant] Dead idea (do not re-propose without new evidence): {g['idea']}")
    return "\n".join(lines)


def session_start(inp: dict, rec: Record) -> dict | None:
    ctx = anchor(rec.state(), full=True)
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}} if ctx else None


def prompt_submit(inp: dict, rec: Record) -> dict | None:
    ctx = anchor(rec.state(), full=False)  # one or two lines: cheap enough for every turn
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}} if ctx else None


def stop(inp: dict, rec: Record) -> dict | None:
    if inp.get("stop_hook_active"):
        return None  # already blocked once this turn; never loop
    state = rec.state()
    if not state["question"]:
        return None
    text = _last_assistant_text(inp.get("transcript_path") or "")
    untraced = checks.untraced_numbers(text, state)
    if not untraced:
        return None
    shown = ", ".join(untraced[:MAX_LIST]) + (" ..." if len(untraced) > MAX_LIST else "")
    return {
        "decision": "block",
        "reason": (
            f"[warrant] These numbers in your reply do not trace to any recorded evidence: {shown}. "
            "Attach the run/log that produced them (`warrant evidence`), or mark them as "
            "unverified or remove them before finishing."
        ),
    }


HANDLERS = {"session": session_start, "prompt": prompt_submit, "stop": stop}


def run(name: str, rec: Record | None = None) -> int:
    try:
        inp = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        inp = {}
    if rec is None:
        rec = Record(default_path(inp.get("cwd")))
    if not rec.exists():
        return 0
    out = HANDLERS[name](inp, rec)
    if out:
        print(json.dumps(out))
    return 0
