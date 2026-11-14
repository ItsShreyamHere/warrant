"""Proof receipts: a claim that something is proven is checked by running a checker.

  .lean  -> Lean 4 (`lake env lean` inside a Lake project, else `lean`). `sorry`/`admit` = not a proof.
  .py    -> a SymPy (or plain Python) script whose `assert`s carry the claim; exit 0 = holds.

green  = the checker accepted it
red    = the checker rejected it, or the proof cheats (`sorry`)
yellow = no checker installed / unsupported file: we cannot say
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .checks import GREEN, RED, YELLOW, sha256_file

_SORRY = re.compile(r"\b(sorry|admit)\b")
_LEAN_COMMENT = re.compile(r"/-.*?-/|--[^\n]*", re.S)


def _first_error(text: str) -> str:
    for line in text.splitlines():
        if "error" in line.lower():
            return line.strip()[:200]
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return lines[-1].strip()[:200] if lines else "failed"


def check_proof(path: str, timeout: int = 300) -> dict:
    p = Path(path)
    if not p.is_file():
        return {"status": RED, "why": f"proof file not found: {path}"}
    sha = sha256_file(path)
    src = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".lean":
        if _SORRY.search(_LEAN_COMMENT.sub("", src)):
            return {"status": RED, "why": "proof uses sorry/admit", "sha": sha}
        lake_root = next((d for d in [p.parent, *p.parent.parents] if (d / "lakefile.lean").exists()
                          or (d / "lakefile.toml").exists()), None)
        if lake_root and shutil.which("lake"):
            cmd, cwd = ["lake", "env", "lean", str(p.resolve())], lake_root
        elif shutil.which("lean"):
            cmd, cwd = ["lean", str(p.resolve())], p.parent
        else:
            return {"status": YELLOW, "why": "Lean is not installed; proof not checked", "sha": sha}
        label = "Lean"
    elif p.suffix == ".py":
        if not re.search(r"^\s*assert\b", src, re.M):
            return {"status": YELLOW, "why": "script has no assert, so it claims nothing", "sha": sha}
        cmd, cwd, label = [sys.executable, str(p.resolve())], p.parent, "script"
    else:
        return {"status": YELLOW, "why": f"no checker for {p.suffix} files (use .lean or .py)", "sha": sha}
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": YELLOW, "why": f"{label} timed out after {timeout}s", "sha": sha}
    if r.returncode == 0:
        why = "Lean accepted the proof" if label == "Lean" else "the script's assertions hold"
        return {"status": GREEN, "why": why, "sha": sha}
    err = r.stderr + r.stdout
    # a broken install (e.g. elan shim without a toolchain, missing module) says nothing about the proof
    if re.search(r"no default toolchain|toolchain .* not installed|command not found|ModuleNotFoundError|"
                 r"unknown package|could not resolve|failed to download", err, re.I):
        return {"status": YELLOW, "why": f"{label} could not run here: {_first_error(err)}", "sha": sha}
    return {"status": RED, "why": f"{label} rejected it: {_first_error(err)}", "sha": sha}
