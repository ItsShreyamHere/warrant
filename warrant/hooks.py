"""Claude Code hook handlers. Each reads the hook JSON on stdin and prints hook JSON.

Quiet by default: with no `.warrant/` record in the project, every hook is a no-op.
Run `warrant init` (or `warrant question ...`) to turn a project on.
"""
import json
import sys
from pathlib import Path

from . import checks, cites
from . import provenance as prov
from .record import Record, default_path

MAX_LIST = 8
_WRITERS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
_SKIP = {"TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "ExitPlanMode", "EnterPlanMode"}


def _flatten(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return "\n".join(_flatten(v) for v in x.values())
    if isinstance(x, list):
        return "\n".join(_flatten(v) for v in x)
    return "" if x is None else str(x)


def _norm(p: str) -> str:
    try:
        return str(Path(p).resolve()).lower()
    except OSError:
        return p.lower()


def final_reply(transcript_path: str, before_prompt: bool = False) -> str:
    """Text of Claude's final reply: assistant text after the last tool result or user prompt.
    With before_prompt, a just-submitted prompt is skipped and the reply before it returned."""
    chunks: list[str] = []
    last: list[str] = []
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("type") == "user":
                    if chunks:
                        last = chunks
                    chunks = []
                elif e.get("type") == "assistant":
                    parts = (e.get("message") or {}).get("content") or []
                    if isinstance(parts, str):
                        chunks.append(parts)
                        continue
                    for p in parts:
                        if isinstance(p, dict) and p.get("type") == "text":
                            chunks.append(p.get("text", ""))
                        elif isinstance(p, dict) and p.get("type") == "tool_use":
                            chunks = []
    except OSError:
        return ""
    return "\n".join(chunks if chunks or not before_prompt else last)


def anchor(state: dict, full: bool) -> str:
    if not state["question"]:
        return ""
    lines = [f"[warrant] Research question: {state['question']}"]
    if state["hypothesis"]:
        lines.append(f"[warrant] Current hypothesis: {state['hypothesis']}")
    if full:
        counts: dict[str, int] = {}
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


_GENERIC = set("does help work better effect impact improve improves using use method result results "
               "model data question whether what when which much many more less than".split())
DRIFT_TURNS = 3


def _topic_words(state: dict) -> set[str]:
    text = " ".join([state["question"] or "", state["hypothesis"] or ""] +
                    [c["text"] for c in state["claims"].values()])
    return {w for w in checks._content_words(text.lower()) if len(w) >= 4 and w not in _GENERIC}


def drift_note(inp: dict, rec: Record, state: dict) -> str:
    """Code-only drift check: N substantial replies in a row sharing no topic word with the
    question, hypothesis or claims. Warns once, then resets, so it never nags."""
    topic = _topic_words(state)
    reply = final_reply(inp.get("transcript_path") or "", before_prompt=True)
    if not topic or len(reply) < 300:
        return ""
    f = rec.dir / "drift.json"
    try:
        streak = json.loads(f.read_text())["streak"]
    except (OSError, ValueError, KeyError):
        streak = 0
    words = checks._content_words(reply.lower())
    streak = 0 if words & topic else streak + 1
    note = ""
    if streak >= DRIFT_TURNS:
        note = (f"[warrant] The last {streak} replies did not touch the research question "
                f"(\"{state['question']}\"). If this is a deliberate new sub-question, record it with "
                "`warrant question`; otherwise say so to the user and steer back.")
        streak = 0
    f.write_text(json.dumps({"streak": streak}))
    return note


def prompt_submit(inp: dict, rec: Record) -> dict | None:
    prompt = inp.get("prompt") or ""
    if prompt.strip():
        # numbers the user gave are legitimate sources
        rec.observe("user", "your prompt", prompt, prov.source_numbers(prompt), prov.keyed_values(prompt))
    state = rec.state()
    ctx = "\n".join(x for x in (anchor(state, full=False), drift_note(inp, rec, state)) if x)
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}} if ctx else None


def post_tool(inp: dict, rec: Record) -> dict | None:
    tool = inp.get("tool_name") or "tool"
    if tool in _SKIP or tool.startswith("mcp__warrant"):
        return None
    ti, tr = inp.get("tool_input") or {}, inp.get("tool_response")
    if tool in _WRITERS:
        # text Claude writes is not evidence; remember the path so reading it back isn't either
        path = ti.get("file_path") or ti.get("notebook_path")
        if path:
            rec.append("wrote", path=_norm(path), tool=tool)
        return None
    text = _flatten(ti) + "\n" + _flatten(tr)
    ints_only = False
    if tool == "Read":
        label = f"Read: {ti.get('file_path', '')}"
        ints_only = _norm(ti.get("file_path", "")) in rec.written_paths()
    elif tool == "Bash":
        label = f"Bash: {(ti.get('command') or '')[:120]}"
    else:
        label = tool
    rec.observe(tool, label, text, prov.source_numbers(text, ints_only=ints_only),
                {} if ints_only else prov.keyed_values(text))
    return None


def stop(inp: dict, rec: Record) -> dict | None:
    if inp.get("stop_hook_active"):
        return None  # already blocked once this turn; never loop
    text = final_reply(inp.get("transcript_path") or "")
    if not text.strip():
        return None
    problems = []
    untraced = checks.untraced_numbers(text, rec)
    if untraced:
        shown = ", ".join(untraced[:MAX_LIST]) + (" ..." if len(untraced) > MAX_LIST else "")
        problems.append(f"numbers that no command output, file, or record entry produced: {shown}")
    from .stats import statcheck
    wrong = [r for r in statcheck(text) if not r["consistent"]]
    if wrong:
        problems.append("statistics whose p-value does not follow from the test statistic: " +
                        "; ".join(f"{r['text']} (recomputed p = {r['computed_p']})" for r in wrong[:MAX_LIST]))
    bad = [r for r in cites.check_text(text, rec.dir) if r["status"] == "red"]
    if bad:
        problems.append("citations that do not resolve or do not match: " +
                        "; ".join(f"{r['id']} ({r['why']})" for r in bad[:MAX_LIST]))
    if not problems:
        return None
    return {
        "decision": "block",
        "reason": (
            "[warrant] Your reply has " + " and ".join(problems) + ". "
            "Run the command that produces each number, fix or remove the citation, or label a "
            "number as an estimate with '~' before finishing."
        ),
    }


HANDLERS = {"session": session_start, "prompt": prompt_submit, "post": post_tool, "stop": stop}


def run(name: str, rec: Record | None = None) -> int:
    try:
        inp = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        inp = {}
    if rec is None:
        rec = Record(default_path(inp.get("cwd")))
    if not rec.exists():
        return 0
    try:
        out = HANDLERS[name](inp, rec)
    except Exception as e:  # a supervisor must never break the session it supervises
        print(f"[warrant] hook {name} failed: {e}", file=sys.stderr)
        return 0
    if out:
        print(json.dumps(out))
    return 0
