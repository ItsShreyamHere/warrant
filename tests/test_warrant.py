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
    return (json.loads(out) or None) if out.strip() else None  # "{}" = nothing to say


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
    assert r.status == "yellow" and "title is real" in r.why  # broken id is not a fake paper
    monkeypatch.setattr(cites, "search_title", lambda t: {"status": "yellow", "why": "OpenAlex unreachable"})
    monkeypatch.setattr(audit, "search_crossref", lambda t: {"status": "yellow", "why": "Crossref unreachable"})
    r = audit.check_ref(audit.Ref(key="k", title="Some real but unreachable title"))
    assert r.status == "yellow"  # unreachable registries never accuse


def test_audit_bbl_regressions():
    from warrant import audit
    # DOI hard-wrapped by LaTeX, ACL-style entry without \newblock, page numbers like 2009.3573
    bbl = (
        r"\bibitem[{Cameron and Miller(2015)}]{cameron2015}" "\n"
        "A.~Colin Cameron and Douglas~L. Miller. 2015. A practitioner's guide to cluster-robust inference.\n"
        r"\emph{Journal of Human Resources}, 50(2):317--372. doi:10.3368/jhr.50.2." "\n317\n\n"
        r"\bibitem{s}" "\nB. Succar. 2009. Building information modelling framework: a research and "
        "delivery foundation for industry stakeholders. Automation in Construction, 18(3):2009.3573.\n"
    )
    a, b = audit.parse_bbl(bbl)
    assert a.doi == "10.3368/jhr.50.2.317"
    assert a.title == "A practitioner's guide to cluster-robust inference"
    assert b.arxiv is None and b.title.startswith("Building information modelling framework")


def test_audit_refs_from_doi(monkeypatch):
    from warrant import audit
    body = json.dumps({"message": {"reference": [
        {"key": "r1", "DOI": "10.1038/nature14539"},
        {"key": "r2", "unstructured": "Smith, J. (2019) Gradient folding in sparse nets. J. Imag. Res. 3, 1-9."},
        {"key": "r3", "article-title": "Deep learning", "year": "2015"},
    ]}})
    monkeypatch.setattr(cites, "_get", lambda url, **kw: (200, body))
    refs = audit.refs_from_doi("10.1038/s41586-021-03819-2")
    assert [r.key for r in refs] == ["r1", "r2", "r3"]
    assert refs[0].doi == "10.1038/nature14539"
    assert refs[1].title == "Gradient folding in sparse nets"
    assert refs[2].title == "Deep learning"
    monkeypatch.setattr(cites, "_get", lambda url, **kw: (200, json.dumps({"message": {}})))
    with pytest.raises(ValueError, match="did not deposit"):
        audit.refs_from_doi("10.1/x")


def test_proof_receipts(rec, tmp_path):
    from warrant import proofs
    good = tmp_path / "ok.py"
    good.write_text("assert 2 + 2 == 4\n")
    bad = tmp_path / "bad.py"
    bad.write_text("assert 2 + 2 == 5, 'arithmetic'\n")
    empty = tmp_path / "none.py"
    empty.write_text("x = 1\n")
    lean = tmp_path / "t.lean"
    lean.write_text("theorem t : 1 = 1 := by\n  sorry\n")
    assert proofs.check_proof(str(good))["status"] == "green"
    assert proofs.check_proof(str(bad))["status"] == "red"
    assert proofs.check_proof(str(empty))["status"] == "yellow"
    assert "sorry" in proofs.check_proof(str(lean))["why"]
    cid = claim(rec, "this proves addition works")
    main(["evidence", str(cid), "--type", "proof", "--ref", str(good)])
    assert status(rec, cid)["status"] == "green"
    good.write_text("assert True\n")
    assert status(rec, cid)["status"] == "red"  # proof edited after checking


def test_drift_warns_once_after_three_off_topic_replies(rec, tmp_path, monkeypatch, capsys):
    rec.append("question", text="Does label smoothing improve calibration?", hypothesis=None)
    off = "Here is a long discussion of the office coffee machine and its espresso settings. " * 6
    t = _transcript(tmp_path, _say(off))
    notes = []
    for _ in range(4):
        out = _hook("prompt", rec, {"prompt": "next", "transcript_path": t}, monkeypatch, capsys)
        notes.append("did not touch" in out["hookSpecificOutput"]["additionalContext"])
    assert notes == [False, False, True, False]
    on = "Label smoothing changed calibration error noticeably in this run. " * 6
    t2 = _transcript(tmp_path, _say(on))
    out = _hook("prompt", rec, {"prompt": "next", "transcript_path": t2}, monkeypatch, capsys)
    assert "did not touch" not in out["hookSpecificOutput"]["additionalContext"]


def test_badge_and_live_report(rec):
    assert "84/84 verified" in report.badge_svg(84, 0, 0) and "#1f7a4d" in report.badge_svg(84, 0, 0)
    assert "2 not found" in report.badge_svg(80, 2, 2)
    rec.append("question", text="q", hypothesis=None)
    observe(rec, "acc=0.5")
    page = report.html(rec, live=True)
    assert "http-equiv=refresh" in page and "Latest evidence captured" in page


def test_stats_math_matches_reference_values():
    from warrant import stats
    assert round(stats.p_t(2.10, 28), 4) == 0.0449
    assert round(stats.p_f(4.41, 1, 28), 4) == 0.0449
    assert round(stats.p_chi2(3.84, 1), 3) == 0.050
    assert round(stats.p_chi2(30, 20), 4) == 0.0699
    assert round(stats.p_z(1.96), 3) == 0.050
    assert round(stats.p_t(1.0, 1), 4) == 0.5


def test_statcheck_and_grim():
    from warrant import stats
    txt = ("t(28) = 2.10, p = .04. t(28) = 1.20, p < .05. chi2(1) = 3.84, p = .05. "
           "z = 2.5, p < .001. r(28) = .37, p = .04.")
    got = {r["text"]: (r["consistent"], r["gross"]) for r in stats.statcheck(txt)}
    assert got["t(28) = 2.10, p = .04"] == (True, False)
    assert got["t(28) = 1.20, p < .05"] == (False, True)   # p is really .24: decision flips
    assert got["z = 2.5, p < .001"] == (False, False)      # wrong, but still significant
    assert got["r(28) = .37, p = .04"] == (True, False)
    assert [g["mean"] for g in stats.grim("M = 3.48, SD = 1.1, n = 25 and M = 3.47, n = 21")] == ["3.47"]


def test_stop_blocks_inconsistent_statistics(rec, tmp_path, monkeypatch, capsys):
    t = _transcript(tmp_path, _say("The effect was reliable, t(28) = 1.20, p < .05."))
    out = _hook("stop", rec, {"transcript_path": t}, monkeypatch, capsys)
    assert out and "recomputed p = 0.24" in out["reason"]


def test_review_cards_and_quote_verification(monkeypatch, tmp_path):
    from warrant import review, paper
    monkeypatch.setattr(review, "CACHE", tmp_path)
    cited = ("We train on ImageNet. Our residual network reaches 3.57% top-5 error on the test set, "
             "winning first place. Deeper plain networks show higher training error, the degradation problem.")
    monkeypatch.setattr(review, "source_text", lambda aid: {"abstract": "", "body": cited})
    monkeypatch.setattr(review, "find_arxiv", lambda t, d=None: "1512.03385")
    tex = (r"\begin{document} Residual networks reach 3.57\% top-5 error \cite{he}. "
           r"They also report 1.23\% error on CIFAR \cite{he}. We find t(28) = 1.20, p < .05 in our study."
           "\n" r"\begin{thebibliography}{1}\bibitem{he} K. He. \newblock Deep residual learning for image "
           r"recognition. \newblock CVPR, 2016.\end{thebibliography}\end{document}")
    res = review.run({"main.tex": tex}, check_refs=False)
    checks = [f["check"] for f in res["findings"]]
    assert "attributed number not in cited paper" in checks          # 1.23% is not in the source
    assert any("decision flips" in c for c in checks)
    assert any(f.get("number") == "1.23%" for f in res["findings"])
    assert not any(f.get("number") == "3.57%" for f in res["findings"])
    assert res["cards"] and "3.57% top-5 error" in res["cards"][0]["passages"][0]
    v = review.verify(res["cards"], [
        {"card": 1, "verdict": "supports", "quote": "reaches 3.57% top-5 error on the test set"},
        {"card": 1, "verdict": "supports", "quote": "reaches 2.1% top-5 error on the test set"}])
    assert [x["accepted"] for x in v] == [True, False]


def test_statcheck_scan_regressions():
    """False positives found by the arXiv scan (bench/scan_stats.py)."""
    from warrant import stats
    # scientific notation, as LaTeX becomes after tex_to_text: "4.7 × 10^ -5"
    r = stats.statcheck("t(11) = -4.90 ; p = 4.7 × 10^ -4")
    assert r and r[0]["consistent"]
    assert stats.statcheck("z = 5.05, p = 4.4e-7")[0]["consistent"]
    # unreadable layouts are skipped, never flagged
    assert stats.statcheck("t(4)=18.76, p=4.8") == []
    # Bonferroni-adjusted p-values are not errors in a paper that says it adjusts
    txt = "We applied Bonferroni correction. t(16) = 2.64, p = .125 and t(16) = -0.48, p = 1.000"
    assert all(x["consistent"] and x["adjusted"] for x in stats.statcheck(txt))
    # ...but the same numbers without any correction stated are still flagged
    assert not stats.statcheck("t(16) = 2.64, p = .125")[0]["consistent"]


def test_codex_and_opencode_hook_shapes(rec, tmp_path, monkeypatch, capsys):
    # Codex Stop passes the reply directly
    out = _hook("stop", rec, {"last_assistant_message": "Accuracy reached 0.874."}, monkeypatch, capsys)
    assert out["decision"] == "block" and "0.874" in out["reason"]
    # Codex apply_patch: the patched file is not evidence when read back
    patch = "*** Begin Patch\n*** Add File: notes/results.md\n+acc 0.931\n*** End Patch"
    _hook("post", rec, {"tool_name": "apply_patch", "tool_input": {"command": patch}, "cwd": str(tmp_path)},
          monkeypatch, capsys)
    assert any(p.endswith("results.md") for p in rec.written_paths())
    # OpenCode bash tool output is evidence
    _hook("post", rec, {"tool_name": "bash", "tool_input": {"command": "python eval.py"},
                        "tool_response": {"output": "val_acc=0.7781"}}, monkeypatch, capsys)
    assert checks.untraced_numbers("accuracy 77.81%", rec) == []


def test_drift_works_without_claude_transcript(rec, monkeypatch, capsys):
    """Codex/OpenCode: drift reads the reply the Stop hook saved, not a transcript."""
    rec.append("question", text="Does label smoothing improve calibration?", hypothesis=None)
    off = "Here is a long discussion of the office coffee machine and its espresso settings. " * 6
    seen = []
    for _ in range(3):
        _hook("stop", rec, {"last_assistant_message": off}, monkeypatch, capsys)
        out = _hook("prompt", rec, {"prompt": "next"}, monkeypatch, capsys)
        seen.append("did not touch" in out["hookSpecificOutput"]["additionalContext"])
    assert seen == [False, False, True]


# --- warrant watch ---

def _watch(rec, tmp_path, name, text, **kw):
    from warrant.watch import Watch
    f = tmp_path / name
    f.write_text(text)
    w = Watch(rec, [str(f)], log=lambda *a: None, **kw)
    return w, f, {a["sentinel"] for a in w.poll()}


def test_watch_healthy_run_is_silent(rec, tmp_path):
    lines = "".join(f"step={i} loss={2.0 * 0.97 ** i:.4f} val_loss={2.1 * 0.975 ** i:.4f} "
                    f"val_acc={min(0.9, 0.5 + i * 0.004):.3f}\n" for i in range(50))
    _, _, got = _watch(rec, tmp_path, "train.log", lines)
    assert got == set()


def test_watch_catches_failures(rec, tmp_path):
    bad = ("step=1 loss=1.0\nstep=2 loss=0.8\nstep=3 loss=0.7\nstep=4 loss=0.6\nstep=5 loss=2.5\n"
           "step=6 loss=nan\nTraceback (most recent call last):\nRuntimeError: CUDA out of memory\n")
    _, _, got = _watch(rec, tmp_path, "a.log", bad)
    assert {"diverge", "nonfinite", "crash"} <= got


def test_watch_overfit_leakage_and_jsonl(rec, tmp_path):
    rows = [{"step": i, "train_loss": 1 - 0.1 * i, "val_loss": 0.5 + 0.05 * i, "test_acc": 1.0} for i in range(6)]
    _, _, got = _watch(rec, tmp_path, "m.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
    assert {"overfit", "too_good"} <= got


def test_watch_incremental_csv_and_stale(rec, tmp_path):
    w, f, got = _watch(rec, tmp_path, "m.csv", "step,loss\n1,1.0\n2,0.9\n", stale=0)
    assert got == set()
    with f.open("a") as fh:
        fh.write("3,0.8\n4,0.7\n5,4.0\n")
    assert "diverge" in {a["sentinel"] for a in w.poll()}
    assert "stale" in {a["sentinel"] for a in w.poll()}  # no growth since


def test_watch_refutes_preregistered_claim_and_alerts_reach_agent(rec, tmp_path, monkeypatch, capsys):
    cid = claim(rec, "accuracy stays above 0.9")
    main(["predict", str(cid), '{"metric":"val_acc","op":"lt","of":"absolute","threshold":0.9}'])
    _, _, got = _watch(rec, tmp_path, "r.log", "val_acc=0.81\n")
    assert "refuted" in got
    rec.append("question", text="q", hypothesis=None)
    capsys.readouterr()  # drop the CLI output printed above
    out = _hook("prompt", rec, {"prompt": "how is it going"}, monkeypatch, capsys)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "[warrant watch]" in ctx and "refuted" in ctx
    out = _hook("prompt", rec, {"prompt": "again"}, monkeypatch, capsys)
    assert "[warrant watch]" not in out["hookSpecificOutput"]["additionalContext"]  # delivered once
    # watched output is evidence: the agent can now report 0.81
    assert checks.untraced_numbers("validation accuracy is 0.81", rec) == []
