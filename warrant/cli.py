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
    ap = argparse.ArgumentParser(prog="warrant", description="Keep research with Claude honest.")
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
