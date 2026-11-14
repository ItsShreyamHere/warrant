"""`warrant` command line. Claude drives it through the skill; humans can too."""
import argparse
import re
import urllib.parse
import json
import sys
from pathlib import Path

from . import audit, checks, cites, hooks, report
from .record import Record

ICON = {"green": "OK ", "yellow": "?? ", "red": "XX "}


def _kv(pairs: list[str] | None) -> dict:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if not _:
            raise SystemExit(f"expected name=value, got: {p}")
        out[k.strip()] = float(v)
    return out


def _claim_or_die(st: dict, cid: int) -> dict:
    c = st["claims"].get(cid)
    if not c:
        raise SystemExit(f"no claim #{cid}")
    return c


def cmd_init(a, rec):
    rec.create()
    if a.question:
        rec.append("question", text=a.question, hypothesis=None)
    print(f"warrant is on for this project ({rec.dir}). Hooks will now capture tool output "
          "and check Claude's replies.")


def cmd_question(a, rec):
    rec.append("question", text=a.text, hypothesis=a.hypothesis)
    print(f"question set: {a.text}")


def cmd_claim(a, rec):
    st = rec.state()
    dead = checks.graveyard_match(a.text, st)
    rec.append("claim", text=a.text)
    cid = len(st["claims"]) + 1
    print(f"claim #{cid}")
    if dead:
        print(f"warning: resembles dead idea #{dead['id']}: {dead['idea']} ({dead['why']}). "
              "Pre-register what result would justify revisiting it (`warrant predict`).")


def cmd_evidence(a, rec):
    _claim_or_die(rec.state(), a.claim)
    body = {"claim": a.claim, "type": a.type}
    if a.type == "run":
        if not a.log:
            raise SystemExit("run evidence needs --log")
        sha = checks.sha256_file(a.log)
        if sha is None:
            raise SystemExit(f"log not found: {a.log}")
        body.update(log=str(Path(a.log).resolve()), sha=sha, metrics=_kv(a.metric),
                    seeds=a.seeds, p=a.p, std=a.std)
    elif a.type == "proof":
        if not a.ref:
            raise SystemExit("proof evidence needs --ref proof.lean or check.py")
        from .proofs import check_proof
        res = check_proof(a.ref)
        body.update(ref=str(Path(a.ref).resolve()), check=res)
    elif a.type == "cite":
        if not a.ref:
            raise SystemExit("cite evidence needs --ref (DOI, arXiv id, or title)")
        res = cites.check_quote(cites.resolve(a.ref), a.quote)
        body.update(ref=a.ref, quote=a.quote, check={k: res.get(k) for k in ("status", "why", "title")})
    else:
        body.update(ref=a.ref, quote=a.quote, note=a.note)
    rec.append("evidence", **body)
    c = _claim_or_die(rec.state(), a.claim)
    r = checks.evaluate(c)
    print(f"claim #{a.claim}: {r['status']}" + "".join(f"\n  - {x}" for x in r["reasons"]))


def cmd_predict(a, rec):
    c = _claim_or_die(rec.state(), a.claim)
    if c.get("result"):
        raise SystemExit("this claim already has a result; pre-registration must come first")
    pred = json.loads(a.predicate)
    if isinstance(pred, dict):
        pred = [pred]
    checks.judge(pred, a.mode, {}, {})  # validates clauses, raises on bad ones
    rec.append("predict", claim=a.claim, predicate=pred, mode=a.mode)
    print(f"pre-registered on claim #{a.claim}: refuted if {a.mode} of {json.dumps(pred)}")


def cmd_result(a, rec):
    c = _claim_or_die(rec.state(), a.claim)
    p = c.get("predict")
    if not p:
        raise SystemExit("no pre-registered predicate on this claim (`warrant predict` first)")
    obs, base = _kv(a.observed), _kv(a.baseline)
    verdict, unresolved = checks.judge(p["predicate"], p["mode"], obs, base)
    rec.append("result", claim=a.claim, observed=obs, baseline=base, verdict=verdict, unresolved=unresolved)
    if verdict == "refuted":
        rec.append("kill", idea=c["text"], why="refuted by pre-registered predicate", claim=a.claim)
    print(f"claim #{a.claim}: {verdict}" + (f" (missing: {', '.join(unresolved)})" if unresolved else ""))


def cmd_kill(a, rec):
    rec.append("kill", idea=a.idea, why=a.why)
    print(f"buried: {a.idea}")


def cmd_retract(a, rec):
    _claim_or_die(rec.state(), a.claim)
    rec.append("retract", claim=a.claim, why=a.why)
    print(f"claim #{a.claim} retracted")


def _rows(st):
    for c in st["claims"].values():
        if not c["retracted"]:
            yield c, checks.evaluate(c)


def cmd_status(a, rec):
    st = rec.state()
    if a.json:
        print(json.dumps({"question": st["question"], "hypothesis": st["hypothesis"],
                          "claims": [{"id": c["id"], "text": c["text"], **r} for c, r in _rows(st)],
                          "graveyard": st["graveyard"], "chain_ok": rec.verify_chain()}, indent=2))
        return
    print(f"Question: {st['question'] or '(none: run `warrant question`)'}")
    if st["hypothesis"]:
        print(f"Hypothesis: {st['hypothesis']}")
    for c, r in _rows(st):
        print(f"{ICON[r['status']]}#{c['id']} {c['text']}")
        for x in r["reasons"] + r["notes"]:
            print(f"     - {x}")
    if st["graveyard"]:
        print("Graveyard:")
        for g in st["graveyard"]:
            print(f"  + {g['idea']} ({g['why']})")
    if not rec.verify_chain():
        print("WARNING: record hash chain is broken; history was edited.")


def cmd_report(a, rec):
    if a.draft:
        out = Path(a.output or "warrant-draft.html")
        text = Path(a.draft).read_text(encoding="utf-8", errors="replace")
        out.write_text(report.draft_html(rec, text, Path(a.draft).name), encoding="utf-8")
        print(f"wrote {out}")
        return
    if a.html:
        out = Path(a.output or "warrant-report.html")
        out.write_text(report.html(rec), encoding="utf-8")
        print(f"wrote {out}")
        return
    st = rec.state()
    out = [f"# Research record\n\n**Question:** {st['question'] or '-'}\n"]
    if st["hypothesis"]:
        out.append(f"**Hypothesis:** {st['hypothesis']}\n")
    rows = list(_rows(st))
    tally = {s: sum(1 for _, r in rows if r["status"] == s) for s in ("green", "yellow", "red")}
    out.append(f"**Claims:** {tally['green']} verified, {tally['yellow']} unverified, {tally['red']} flagged\n")
    out.append("| | # | claim | why |\n|---|---|---|---|")
    for c, r in rows:
        why = "; ".join(r["reasons"] + r["notes"]).replace("|", "/") or "evidence checks out"
        out.append(f"| {r['status']} | {c['id']} | {c['text'].replace('|', '/')} | {why} |")
    if st["graveyard"]:
        out.append("\n## Graveyard\n")
        out += [f"- {g['idea']} ({g['why']})" for g in st["graveyard"]]
    out.append(f"\nRecord hash chain intact: {'yes' if rec.verify_chain() else 'NO'}\n")
    text = "\n".join(out)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"wrote {a.output}")
    else:
        print(text)


def cmd_trace(a, rec):
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8", errors="replace")
    rows = checks.trace_text(text, rec)
    for t, h in rows:
        if h is None:
            print(f"XX  {t.raw:>12}  untraced")
        elif a.all:
            print(f"OK  {t.raw:>12}  {h[1]}: {h[0]}")
    bad = [t for t, h in rows if h is None]
    print(f"{len(rows) - len(bad)}/{len(rows)} numbers traced")
    if bad:
        sys.exit(1)


def cmd_cites(a, rec):
    text = Path(a.file).read_text(encoding="utf-8", errors="replace")
    rows = cites.check_bib(text, rec.dir) if a.file.endswith(".bib") else cites.check_text(text, rec.dir)
    for r in rows:
        print(f"{ICON[r['status']]}{r['id']}: {r['why']}")
    red = sum(r["status"] == "red" for r in rows)
    print(f"{len(rows)} citations, {red} flagged")
    if red:
        sys.exit(1)


def cmd_review(a, rec):
    from . import review
    if a.verify:
        vf = Path(a.verify)
        cards_f = Path(a.cards) if a.cards else vf.with_name("cards.json")
        if not cards_f.is_file():
            raise SystemExit(f"cards not found: {cards_f} (pass --cards)")
        res = review.verify(json.loads(cards_f.read_text(encoding="utf-8")),
                            json.loads(vf.read_text(encoding="utf-8")))
        for r in res:
            mark = "OK " if r["accepted"] else "XX "
            print(f"{mark}card {r.get('card')}: {r.get('verdict')}: {r['why']}")
        bad = [r for r in res if not r["accepted"]]
        tally = {v: sum(r["accepted"] and r["verdict"] == v for r in res) for v in sorted(review.VERDICTS)}
        print(", ".join(f"{n} {v}" for v, n in tally.items()) + f"; {len(bad)} rejected")
        return 1 if bad else 0
    if not a.target:
        raise SystemExit("give a paper: arXiv id, DOI, URL, or a folder/.tex file")
    src = a.target
    if Path(src).is_dir():
        files = {str(f): f.read_text(encoding="utf-8", errors="replace")
                 for f in Path(src).rglob("*") if f.suffix.lower() in (".tex", ".bbl", ".bib")}
        name = Path(src).name
    elif Path(src).is_file():
        files = {src: Path(src).read_text(encoding="utf-8", errors="replace")}
        name = Path(src).stem
    else:
        doi = cites._DOI.search(urllib.parse.unquote(src))
        arx = re.search(r"(\d{4}\.\d{4,5})", src)
        aid = review.find_arxiv(None, cites.clean_doi(doi.group(1))) if doi else (arx.group(1) if arx else None)
        if not aid:
            raise SystemExit("could not find this paper's LaTeX source (needs an arXiv version); "
                             "for any DOI, `warrant audit` still checks its references")
        print(f"reading arXiv:{aid} ...", file=sys.stderr)
        files = audit.fetch_arxiv_source(aid)
        name = aid
    res = review.run(files, a.max_sources, a.max_cards, not a.no_refs,
                     log=lambda m: print(m, file=sys.stderr))
    out = Path(a.output or Path("warrant-review") / name.replace("/", "_"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(review.markdown(name, res), encoding="utf-8")
    (out / "cards.json").write_text(json.dumps(res["cards"], indent=1), encoding="utf-8")
    st = res["stats"]
    red = [x for x in res["findings"] if x["level"] == "red"]
    for x in res["findings"]:
        tag = "XX " if x["level"] == "red" else "?? "
        print(f"{tag}{x['check']}{' [' + x['ref'] + ']' if x.get('ref') else ''}"
              f"{' ' + x['number'] if x.get('number') else ''}: {x['detail']}")
    print(f"\n{st['references']} references, {st['citing_sentences']} citing sentences, "
          f"{st['sources_read']} cited papers read, {st['cards']} evidence cards -> {out / 'report.md'}")
    return 1 if red else 0


def cmd_stats(a, rec):
    from . import paper, stats
    text = Path(a.file).read_text(encoding="utf-8", errors="replace")
    if a.file.endswith(".tex"):
        text = paper.tex_to_text(paper.strip_comments(text))
    rows = stats.statcheck(text)
    bad = 0
    for r in rows:
        tag = "OK " if r["consistent"] else ("XX " if r["gross"] else "?? ")
        bad += not r["consistent"]
        note = "" if r["consistent"] else ("  DECISION FLIPS at .05" if r["gross"] else "  inconsistent")
        print(f"{tag}{r['text']}  ->  recomputed p = {r['computed_p']}{note}")
    for g in stats.grim(text):
        bad += 1
        print(f"??  GRIM: {g['text']}  ->  {g['detail']}")
    print(f"{len(rows)} tests recomputed, {bad} problems")
    return 1 if bad else 0


def cmd_watch(a, rec):
    from .watch import Watch
    if not rec.exists():
        rec.create()
    w = Watch(rec, a.paths, stale=a.stale, wake=a.wake, max_wakes=a.max_wakes)
    if not a.once:
        print(f"warrant watch: {len(w.files())} file(s), every {a.interval}s, 0 tokens. Ctrl+C to stop.")
    try:
        w.run(a.interval, a.once)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_alerts(a, rec):
    import json as _json
    f = rec.dir / "alerts.jsonl"
    rows = [_json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip() not in ("", "null")]         if f.is_file() else []
    for r in rows[-a.n:]:
        print(f"[{r['level'].upper()}] {r['sentinel']}: {r['msg']} ({r['file']})")
    print(f"{len(rows)} alerts")
    return 0


def cmd_dashboard(a, rec):
    from .dashboard import serve
    if not rec.exists():
        raise SystemExit("no warrant record here; run `warrant init` first")
    serve(rec, a.port, not a.no_browser)


def cmd_audit(a, rec):
    src = a.target
    doi = cites._DOI.search(urllib.parse.unquote(src))
    arx = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})", src)
    try:
        if Path(src).is_file():
            refs = audit.refs_from_files({src: Path(src).read_text(encoding="utf-8", errors="replace")})
        elif doi:
            d = cites.clean_doi(doi.group(1))
            print(f"fetching the reference list of doi:{d} ...", file=sys.stderr)
            refs = audit.refs_from_doi(d)
        elif arx:
            print(f"fetching arXiv:{arx.group(1)} source ...", file=sys.stderr)
            refs = audit.refs_from_files(audit.fetch_arxiv_source(arx.group(1)))
        else:
            raise SystemExit("give a DOI, an arXiv id, a doi.org/arxiv.org URL, or a .bib/.bbl/.tex file")
    except ValueError as e:
        raise SystemExit(f"cannot audit {src}: {e}")
    if not refs:
        raise SystemExit("no references found")
    print(f"checking {len(refs)} references against doi.org, arXiv, OpenAlex, Crossref ...", file=sys.stderr)
    refs = audit.audit(refs)
    red = [r for r in refs if r.status == "red"]
    yellow = [r for r in refs if r.status == "yellow"]
    if a.badge:
        Path(a.badge).write_text(report.badge_svg(len(refs) - len(red) - len(yellow), len(yellow), len(red)),
                                 encoding="utf-8")
        print(f"wrote badge {a.badge}", file=sys.stderr)
    if a.json:
        print(json.dumps([r.__dict__ for r in refs], indent=1))
    else:
        for r in red:
            print(f"XX  [{r.key}] {r.title or r.raw[:120]}\n      {r.why}")
        if a.all:
            for r in yellow:
                print(f"??  [{r.key}] {r.title or r.raw[:120]}\n      {r.why}")
        print(f"\n{len(refs)} references: {len(refs) - len(red) - len(yellow)} verified, "
              f"{len(yellow)} unchecked, {len(red)} not found anywhere")
        if red:
            print("Not found does not prove fabrication: check these by hand before accusing anyone.")
    return 1 if red else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="warrant", description="Code-verified research for AI agents: numbers, citations, statistics, live runs.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="turn warrant on for this project")
    s.add_argument("question", nargs="?")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("question", help="set the research question")
    s.add_argument("text")
    s.add_argument("--hypothesis")
    s.set_defaults(fn=cmd_question)

    s = sub.add_parser("claim", help="record a claim")
    s.add_argument("text")
    s.set_defaults(fn=cmd_claim)

    s = sub.add_parser("evidence", help="attach evidence to a claim")
    s.add_argument("claim", type=int)
    s.add_argument("--type", choices=["run", "cite", "proof", "data", "note"], default="run")
    s.add_argument("--log", help="run log file (hashed on attach)")
    s.add_argument("--metric", action="append", help="name=value, must appear in the log")
    s.add_argument("--seeds", type=int, default=1)
    s.add_argument("--p", type=float)
    s.add_argument("--std", type=float)
    s.add_argument("--ref", help="DOI / arXiv id / file for cite, proof, data")
    s.add_argument("--quote")
    s.add_argument("--note")
    s.set_defaults(fn=cmd_evidence)

    s = sub.add_parser("predict", help="pre-register a refutation predicate before running")
    s.add_argument("claim", type=int)
    s.add_argument("predicate", help='JSON, e.g. \'{"metric":"acc","op":"lt","of":"baseline","margin":0.01}\'')
    s.add_argument("--mode", choices=["any", "all"], default="any")
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("result", help="record observed metrics; code decides the verdict")
    s.add_argument("claim", type=int)
    s.add_argument("--observed", action="append", required=True, help="name=value")
    s.add_argument("--baseline", action="append", help="name=value")
    s.set_defaults(fn=cmd_result)

    s = sub.add_parser("kill", help="bury a dead idea in the graveyard")
    s.add_argument("idea")
    s.add_argument("--why", default="")
    s.set_defaults(fn=cmd_kill)

    s = sub.add_parser("retract", help="withdraw a claim")
    s.add_argument("claim", type=int)
    s.add_argument("--why", default="")
    s.set_defaults(fn=cmd_retract)

    s = sub.add_parser("status", help="question, claims with status, graveyard")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("report", help="report of every claim (markdown, or --html)")
    s.add_argument("-o", "--output")
    s.add_argument("--html", action="store_true")
    s.add_argument("--draft", help="render this draft with every number marked traced / untraced")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("trace", help="list numbers in a draft that no evidence accounts for")
    s.add_argument("file", help="draft file, or - for stdin")
    s.add_argument("--all", action="store_true", help="also show where traced numbers came from")
    s.set_defaults(fn=cmd_trace)

    s = sub.add_parser("cites", help="check citations in a draft (.md/.tex/.txt) or a .bib file")
    s.add_argument("file")
    s.set_defaults(fn=cmd_cites)

    s = sub.add_parser("audit", help="check every reference in a paper (DOI, arXiv id, URL, or .bib/.bbl/.tex)")
    s.add_argument("target")
    s.add_argument("--all", action="store_true", help="also list references that could not be checked")
    s.add_argument("--badge", help="also write an SVG status badge to this path")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_audit)

    s = sub.add_parser("review", help="referee report: claims vs. cited papers, numbers, stats (arXiv/DOI/LaTeX)")
    s.add_argument("target", nargs="?")
    s.add_argument("--max-sources", type=int, default=25, help="cited papers to read in full (most-cited first)")
    s.add_argument("--max-cards", type=int, default=40)
    s.add_argument("--no-refs", action="store_true", help="skip the reference-existence check")
    s.add_argument("-o", "--output", help="output folder (default warrant-review/<paper>)")
    s.add_argument("--verify", help="verdicts.json to check against the cards (quotes must be verbatim)")
    s.add_argument("--cards", help="cards.json (default: next to the verdicts file)")
    s.set_defaults(fn=cmd_review)

    s = sub.add_parser("watch", help="sentinels over live experiment logs (NaN, divergence, overfit, crashes...): 0 tokens")
    s.add_argument("paths", nargs="+", help="log/CSV/JSONL files, folders or globs")
    s.add_argument("--interval", type=float, default=5)
    s.add_argument("--once", action="store_true", help="check what is there now and exit")
    s.add_argument("--stale", type=float, default=600, help="seconds without output before 'run may have died'")
    s.add_argument("--wake", help="command run with a one-line alert card on stdin for red alerts")
    s.add_argument("--max-wakes", type=int, default=3, help="wake budget per hour")
    s.set_defaults(fn=cmd_watch)

    s = sub.add_parser("alerts", help="recent watch alerts")
    s.add_argument("-n", type=int, default=20)
    s.set_defaults(fn=cmd_alerts)

    s = sub.add_parser("stats", help="recompute every reported p-value (statcheck) and check means (GRIM)")
    s.add_argument("file", help=".md / .txt / .tex")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("dashboard", help="live local page of the session (refreshes every 3 s)")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=cmd_dashboard)

    s = sub.add_parser("hook", help="Claude Code hook entry point")
    s.add_argument("name", choices=sorted(hooks.HANDLERS))
    s.set_defaults(fn=None)

    a = ap.parse_args(argv)
    if a.cmd == "hook":
        return hooks.run(a.name)
    return a.fn(a, Record()) or 0
