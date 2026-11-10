import io
import json
import sqlite3
from contextlib import closing

import pytest

from warrant import checks, cites, falsify, hooks, provenance, report
from warrant.cli import main
from warrant.record import Record


@pytest.fixture
def rec(tmp_path, monkeypatch):
    monkeypatch.setenv("WARRANT_DIR", str(tmp_path / ".warrant"))
    monkeypatch.setenv("WARRANT_OFFLINE", "1")
    monkeypatch.chdir(tmp_path)
    r = Record()
    r.create()
    return r


def claim(rec, text):
    rec.append("claim", text=text)
    return len(rec.state()["claims"])


def status(rec, cid):
    return checks.evaluate(rec.state()["claims"][cid])


def observe(rec, text, tool="Bash", label="Bash: python train.py"):
    rec.observe(tool, label, text, provenance.source_numbers(text), provenance.keyed_values(text))


# --- falsify (ported from ROS) ---

def test_falsify_core():
    pred = [{"metric": "recall", "op": "lt", "of": "baseline", "margin": 0.05}]
    assert falsify.check(pred, "any", {"recall": 0.82}, {"recall": 0.90}) == "refuted"
    assert falsify.check(pred, "any", {"recall": 0.885}, {"recall": 0.90}) == "supported"
    assert falsify.check([], "any", {"recall": 0.5}, {}) == "inconclusive"
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


def test_chain_detects_edited_observation(rec):
    observe(rec, "acc=0.81")
    assert rec.verify_chain()
    f = next((rec.dir / "obs").iterdir())
    f.write_text("acc=0.99")
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
    assert status(rec, claim(rec, "the method is interesting"))["status"] == "yellow"


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
    assert status(rec, claim(rec, "this proves the bound is tight"))["status"] == "red"


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
    main(["claim", "label smoothing with mixup improves validation acc"])
    assert "resembles dead idea" in capsys.readouterr().out


def test_unrelated_idea_not_flagged_as_dead(rec):
    rec.append("kill", idea="label smoothing improves val acc", why="refuted")
    assert checks.graveyard_match("cosine schedule shortens training", rec.state()) is None


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


# --- number provenance ---

def test_extract_skips_non_quantities():
    text = ("See Section 3.2 and Table 4. Python 3.13, run on 2026-11-10 at 14:05. "
            "Code: `lr=0.003`. ```\nbatch=512\n``` Paper doi 10.1234/abc.5678 arXiv:2401.01234. "
            "Roughly ~0.7 by estimate. File results_v2.json. Accuracy 0.874.")
    assert [t.raw for t in provenance.extract(text)] == ["0.874"]


def test_trace_exact_percent_mean_derived(rec):
    observe(rec, "seed0 val_acc=0.812\nseed1 val_acc=0.806\nseed2 val_acc=0.818\nbaseline_acc=0.790\n")
    text = ("Mean accuracy 0.812 (81.2%), best seed 0.818, vs baseline 0.790: "
            "a gain of 0.022. Invented: 0.874.")
    assert checks.untraced_numbers(text, rec) == ["0.874"]


def test_mean_across_separate_runs(rec):
    observe(rec, "val_acc=0.70")
    observe(rec, "val_acc=0.80")
    assert checks.untraced_numbers("mean val acc 0.75 across seeds", rec) == []


def test_written_file_is_not_evidence(rec, tmp_path, monkeypatch, capsys):
    p = str(tmp_path / "results.md")
    _hook("post", rec, {"tool_name": "Write", "tool_input": {"file_path": p, "content": "acc 0.931"}},
          monkeypatch, capsys)
    _hook("post", rec, {"tool_name": "Read", "tool_input": {"file_path": p},
                        "tool_response": {"file": {"content": "acc 0.931"}}}, monkeypatch, capsys)
    assert checks.untraced_numbers("accuracy 0.931", rec) == ["0.931"]


def test_bash_output_is_evidence(rec, monkeypatch, capsys):
    _hook("post", rec, {"tool_name": "Bash", "tool_input": {"command": "python eval.py"},
                        "tool_response": {"stdout": "test_acc: 0.8421\n", "stderr": ""}}, monkeypatch, capsys)
    assert checks.untraced_numbers("test accuracy is 84.21%", rec) == []


def test_user_prompt_numbers_are_sources(rec, monkeypatch, capsys):
    _hook("prompt", rec, {"prompt": "our old model got 0.731 on this"}, monkeypatch, capsys)
    assert checks.untraced_numbers("the previous 0.731 result", rec) == []


# --- hooks ---

def _transcript(tmp_path, *entries):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return str(p)


def _say(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _hook(name, rec, inp, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(inp)))
    hooks.run(name, rec)
    out = capsys.readouterr().out
    return json.loads(out) if out.strip() else None


def test_hooks_silent_without_record(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WARRANT_DIR", str(tmp_path / "none"))
    t = _transcript(tmp_path, _say("acc 0.99"))
    assert _hook("stop", Record(), {"transcript_path": t}, monkeypatch, capsys) is None
    assert not (tmp_path / "none").exists()


def test_stop_blocks_untraced_then_releases(rec, tmp_path, monkeypatch, capsys):
    t = _transcript(tmp_path, _say("Final: accuracy 0.874."))
    out = _hook("stop", rec, {"transcript_path": t}, monkeypatch, capsys)
    assert out["decision"] == "block" and "0.874" in out["reason"]
    assert _hook("stop", rec, {"transcript_path": t, "stop_hook_active": True}, monkeypatch, capsys) is None


def test_stop_only_reads_final_reply(rec, tmp_path, monkeypatch, capsys):
    t = _transcript(
        tmp_path,
        _say("Earlier guess 0.555."),
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
        _say("Done, nothing to report."),
    )
    assert _hook("stop", rec, {"transcript_path": t}, monkeypatch, capsys) is None


def test_stop_passes_traced_reply(rec, tmp_path, monkeypatch, capsys):
    observe(rec, "val_acc=0.8123")
    t = _transcript(tmp_path, _say("Validation accuracy reached 81.2%."))
    assert _hook("stop", rec, {"transcript_path": t}, monkeypatch, capsys) is None


def test_prompt_hook_anchors_question(rec, monkeypatch, capsys):
    rec.append("question", text="does it work?", hypothesis="yes")
    out = _hook("prompt", rec, {"prompt": "go"}, monkeypatch, capsys)
    assert "does it work?" in out["hookSpecificOutput"]["additionalContext"]


def test_session_hook_lists_graveyard(rec, monkeypatch, capsys):
    rec.append("question", text="q", hypothesis=None)
    rec.append("kill", idea="bigger batch helps", why="refuted")
    out = _hook("session", rec, {}, monkeypatch, capsys)
    assert "bigger batch helps" in out["hookSpecificOutput"]["additionalContext"]


def test_hook_errors_never_break_session(rec, monkeypatch, capsys):
    monkeypatch.setattr(hooks, "HANDLERS", {"stop": lambda i, r: 1 / 0})
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert hooks.run("stop", rec) == 0


# --- citations (network mocked) ---

def test_citations(rec, monkeypatch):
    monkeypatch.setenv("WARRANT_OFFLINE", "0")
    monkeypatch.setattr(cites, "resolve_doi", lambda d: (
        {"status": "red", "why": "DOI does not exist"} if d.endswith("fake") else
        {"status": "green", "why": "resolves", "title": "Attention Is All You Need"}))
    monkeypatch.setattr(cites, "resolve_arxiv", lambda a: {"status": "green", "why": "resolves",
                                                           "title": "Deep Residual Learning for Image Recognition"})
    monkeypatch.setattr(cites, "search_title", lambda t: {"status": "red", "why": "no paper with this title found"})
    text = ('As shown in "Attention Is All You Need" (doi 10.48550/real), and in 10.9999/fake. '
            '"A Totally Different Paper About Llamas" arXiv:1512.03385. '
            'Smith et al. (2023), "Quantum Gradient Folding in Sparse Transformers".')
    got = {r["id"]: r["status"] for r in cites.check_text(text, rec.dir)}
    assert got["doi:10.48550/real"] == "green"
    assert got["doi:10.9999/fake"] == "red"
    assert got["arXiv:1512.03385"] == "red"  # id is real, but it's a different paper
    assert got['"Quantum Gradient Folding in Sparse Transformers"'] == "red"


def test_bib(rec, monkeypatch):
    monkeypatch.setattr(cites, "resolve_doi", lambda d: {"status": "green", "why": "resolves",
                                                         "title": "Attention Is All You Need"})
    bib = "@article{vaswani,\n  title={Attention is all you need},\n  doi={10.48550/x},\n}\n"
    assert cites.check_bib(bib)[0]["status"] == "green"


# --- report ---

def test_html_report(rec):
    rec.append("question", text="Does <it> work?", hypothesis=None)
    claim(rec, "it proves everything")
    out = report.html(rec)
    assert "Does &lt;it&gt; work?" in out and "flagged" in out and "hash chain intact" in out


def test_doi_cleanup_regressions():
    # live run 1: a DOI in markdown backticks was looked up with the backtick attached
    assert cites.clean_doi("10.1109/CVPR.2016.90`") == "10.1109/CVPR.2016.90"
    assert cites.clean_doi("10.48550/arXiv.1512.03385`).") == "10.48550/arXiv.1512.03385"
    assert cites.clean_doi("10.1016/S0140-6736(20)30183-5).") == "10.1016/S0140-6736(20)30183-5"
    found = [m.group(1) for m in cites._DOI.finditer("DOI `10.1109/CVPR.2016.90` here")]
    assert [cites.clean_doi(x) for x in found] == ["10.1109/CVPR.2016.90"]


def test_audit_parses_bbl_and_bib():
    from warrant import audit
    bbl = (r"\begin{thebibliography}{2}" "\n"
           r"\bibitem[He et~al.(2016)]{he2016}" "\nK.~He, X.~Zhang.\n"
           r"\newblock Deep residual learning for image recognition." "\n"
           r"\newblock In \emph{CVPR}, 2016. doi:10.1109/CVPR.2016.90" "\n"
           r"\end{thebibliography}")
    r = audit.parse_bbl(bbl)[0]
    assert (r.key, r.title, r.doi) == ("he2016", "Deep residual learning for image recognition", "10.1109/CVPR.2016.90")
    b = audit.parse_bib("@article{x,\n  title={Highway {N}etworks},\n  eprint={1505.00387},\n}\n")[0]
    assert (b.title, b.arxiv) == ("Highway N etworks".replace("N e", "Ne"), "1505.00387")


def test_audit_flags_real_title_with_dead_doi(monkeypatch):
    from warrant import audit
    monkeypatch.setattr(cites, "resolve_doi", lambda d: {"status": "red", "why": "DOI does not exist"})
    monkeypatch.setattr(cites, "search_title", lambda t: {"status": "green", "why": "title found", "title": t})
    r = audit.check_ref(audit.Ref(key="k", title="Attention is all you need", doi="10.1/none"))
    assert r.status == "red" and "title is real" in r.why
    monkeypatch.setattr(cites, "search_title", lambda t: {"status": "yellow", "why": "OpenAlex unreachable"})
    monkeypatch.setattr(audit, "search_crossref", lambda t: {"status": "yellow", "why": "Crossref unreachable"})
    r = audit.check_ref(audit.Ref(key="k", title="Some real but unreachable title"))
    assert r.status == "yellow"  # unreachable registries never accuse
