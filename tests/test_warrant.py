import io
import json
import sqlite3
from contextlib import closing

import pytest

from warrant import checks, falsify, hooks
from warrant.cli import main
from warrant.record import Record


@pytest.fixture
def rec(tmp_path, monkeypatch):
    monkeypatch.setenv("WARRANT_DIR", str(tmp_path / ".warrant"))
    monkeypatch.chdir(tmp_path)
    return Record()


def claim(rec, text):
    rec.append("claim", text=text)
    return len(rec.state()["claims"])


def status(rec, cid):
    return checks.evaluate(rec.state()["claims"][cid])


# --- falsify (ported from ROS) ---

def test_falsify_core():
    pred = [{"metric": "recall", "op": "lt", "of": "baseline", "margin": 0.05}]
    assert falsify.check(pred, "any", {"recall": 0.82}, {"recall": 0.90}) == "refuted"
    assert falsify.check(pred, "any", {"recall": 0.885}, {"recall": 0.90}) == "supported"
    assert falsify.check([], "any", {"recall": 0.5}, {}) == "inconclusive"
    # missing metric must never read as supported
    assert falsify.check(pred, "any", {"acc": 0.9}, {"recall": 0.9}) == "inconclusive"
    two = [{"metric": "a", "op": "lt", "of": "absolute", "threshold": 1},
           {"metric": "b", "op": "gt", "of": "absolute", "threshold": 1}]
    assert falsify.check(two, "all", {"a": 0}, {}) == "inconclusive"
    assert falsify.check(two, "any", {"a": 0}, {}) == "refuted"


# --- record ---

def test_chain_detects_tampering(rec):
    claim(rec, "x")
    claim(rec, "y")
    assert rec.verify_chain()
    with closing(sqlite3.connect(rec.path)) as c, c:
        c.execute("UPDATE events SET body = ? WHERE seq = 1", (json.dumps({"text": "edited"}),))
    assert not rec.verify_chain()


# --- claim checks ---

def test_run_evidence_green_then_tampered_red(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("epoch 10 val_acc=0.8123 loss=0.41\n")
    cid = claim(rec, "val acc reaches 0.812")
    main(["evidence", str(cid), "--log", str(log), "--metric", "val_acc=0.812", "--seeds", "3"])
    assert status(rec, cid)["status"] == "green"
    log.write_text("epoch 10 val_acc=0.9000\n")
    r = status(rec, cid)
    assert r["status"] == "red" and "changed" in r["reasons"][0]


def test_metric_not_in_log_is_red(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("val_acc=0.70\n")
    cid = claim(rec, "acc is 0.81")
    main(["evidence", str(cid), "--log", str(log), "--metric", "val_acc=0.81"])
    assert status(rec, cid)["status"] == "red"


def test_no_evidence_is_yellow(rec):
    cid = claim(rec, "the method is interesting")
    assert status(rec, cid)["status"] == "yellow"


def test_significant_on_one_seed_is_red(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("acc 0.83\n")
    cid = claim(rec, "smoothing significantly improves acc")
    main(["evidence", str(cid), "--log", str(log), "--metric", "acc=0.83"])
    r = status(rec, cid)
    assert r["status"] == "red" and any("significant" in x for x in r["reasons"])


def test_significant_with_seeds_and_p_is_green(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("acc 0.83\n")
    cid = claim(rec, "smoothing significantly improves acc")
    main(["evidence", str(cid), "--log", str(log), "--metric", "acc=0.83", "--seeds", "5", "--p", "0.01"])
    assert status(rec, cid)["status"] == "green"


def test_proves_without_proof_is_red(rec):
    cid = claim(rec, "this proves the bound is tight")
    assert status(rec, cid)["status"] == "red"


def test_understatement_note(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("acc 0.91\n")
    cid = claim(rec, "smoothing may slightly help")
    main(["evidence", str(cid), "--log", str(log), "--metric", "acc=0.91", "--seeds", "5", "--p", "0.001"])
    assert any("understated" in n for n in status(rec, cid)["notes"])


# --- pre-registration + graveyard ---

def test_predict_result_refuted_goes_to_graveyard(rec, capsys):
    cid = claim(rec, "label smoothing improves val acc")
    main(["predict", str(cid), '{"metric":"val_acc","op":"le","of":"baseline"}'])
    main(["result", str(cid), "--observed", "val_acc=0.80", "--baseline", "val_acc=0.81"])
    st = rec.state()
    assert st["claims"][cid]["result"]["verdict"] == "refuted"
    assert status(rec, cid)["status"] == "red"
    assert st["graveyard"][0]["idea"] == "label smoothing improves val acc"
    capsys.readouterr()
    main(["claim", "label smoothing improves validation acc with mixup"])
    assert "resembles dead idea" in capsys.readouterr().out


def test_missing_metric_is_inconclusive(rec):
    cid = claim(rec, "x improves recall")
    main(["predict", str(cid), '{"metric":"recall","op":"lt","of":"baseline"}'])
    main(["result", str(cid), "--observed", "acc=0.9", "--baseline", "recall=0.8"])
    r = status(rec, cid)
    assert r["status"] == "yellow" and "recall" in r["reasons"][0]


def test_predict_after_result_rejected(rec):
    cid = claim(rec, "x")
    main(["predict", str(cid), '{"metric":"a","op":"lt","of":"absolute","threshold":1}'])
    main(["result", str(cid), "--observed", "a=2"])
    with pytest.raises(SystemExit):
        main(["predict", str(cid), '{"metric":"a","op":"gt","of":"absolute","threshold":1}'])


# --- number tracing ---

def test_trace_numbers(rec, tmp_path):
    log = tmp_path / "run.log"
    log.write_text("val_acc=0.8123\n")
    cid = claim(rec, "acc")
    main(["evidence", str(cid), "--log", str(log), "--metric", "val_acc=0.8123"])
    st = rec.state()
    assert checks.untraced_numbers("we reach 81.2% accuracy in 2024 with 3 runs", st) == []
    assert checks.untraced_numbers("accuracy 0.874 and F1 0.66", st) == ["0.874", "0.66"]


# --- hooks ---

def _transcript(tmp_path, text):
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
    return str(p)


def _hook(name, rec, inp, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(inp)))
    hooks.run(name, rec)
    out = capsys.readouterr().out
    return json.loads(out) if out.strip() else None


def test_hooks_silent_without_record(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WARRANT_DIR", str(tmp_path / "none"))
    assert _hook("stop", Record(), {"transcript_path": _transcript(tmp_path, "acc 0.99")}, monkeypatch, capsys) is None


def test_stop_blocks_untraced_then_releases(rec, tmp_path, monkeypatch, capsys):
    rec.append("question", text="does it work?", hypothesis=None)
    t = _transcript(tmp_path, "Final: accuracy 0.874.")
    out = _hook("stop", rec, {"transcript_path": t}, monkeypatch, capsys)
    assert out["decision"] == "block" and "0.874" in out["reason"]
    assert _hook("stop", rec, {"transcript_path": t, "stop_hook_active": True}, monkeypatch, capsys) is None


def test_prompt_hook_anchors_question(rec, monkeypatch, capsys):
    rec.append("question", text="does it work?", hypothesis="yes")
    out = _hook("prompt", rec, {}, monkeypatch, capsys)
    assert "does it work?" in out["hookSpecificOutput"]["additionalContext"]


def test_session_hook_lists_graveyard(rec, monkeypatch, capsys):
    rec.append("question", text="q", hypothesis=None)
    rec.append("kill", idea="bigger batch helps", why="refuted")
    out = _hook("session", rec, {}, monkeypatch, capsys)
    assert "bigger batch helps" in out["hookSpecificOutput"]["additionalContext"]
