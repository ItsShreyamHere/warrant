"""Self-contained HTML report: question, every claim with its verdict, graveyard, integrity."""
import html as h
import time

from . import checks

_CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e6e3dc;--card:#fff;
--g:#1f7a4d;--gb:#e5f3ea;--y:#8a6100;--yb:#fbf1d9;--r:#b42318;--rb:#fbe7e5}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe6;--mut:#9b9a95;--line:#2c2b29;
--card:#1c1c1a;--g:#5fc68f;--gb:#163222;--y:#e3b54f;--yb:#33280f;--r:#f2877c;--rb:#3a1a17}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 64px}
.k{font:600 12px/1 ui-monospace,Menlo,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
h1{font-size:26px;line-height:1.25;margin:8px 0 6px}.hyp{color:var(--mut);margin:0 0 24px}
.tally{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 28px}
.chip{padding:8px 14px;border-radius:10px;font-weight:600}
.green{background:var(--gb);color:var(--g)}.yellow{background:var(--yb);color:var(--y)}.red{background:var(--rb);color:var(--r)}
.claim{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:0 0 10px;
display:grid;grid-template-columns:auto 1fr;gap:4px 14px;align-items:start}
.pill{font:700 11px/1 ui-monospace,Menlo,Consolas,monospace;padding:6px 8px;border-radius:6px;text-transform:uppercase}
.txt{font-weight:600}.why{grid-column:2;color:var(--mut);font-size:14px;margin:0;padding-left:18px}
h2{font-size:15px;margin:36px 0 12px}.grave{color:var(--mut);margin:0;padding-left:18px}
.grave li{margin:4px 0}.grave b{color:var(--fg);text-decoration:line-through;text-decoration-color:var(--r)}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:14px;color:var(--mut);font-size:13px}
.ok{color:var(--g)}.bad{color:var(--r);font-weight:700}
"""


def html(rec) -> str:
    st = rec.state()
    rows = [(c, checks.evaluate(c)) for c in st["claims"].values() if not c["retracted"]]
    tally = {s: sum(r["status"] == s for _, r in rows) for s in ("green", "yellow", "red")}
    label = {"green": "verified", "yellow": "unverified", "red": "flagged"}
    e = h.escape
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>warrant report</title><style>{_CSS}</style></head><body><main>",
        "<div class=k>Research question</div>",
        f"<h1>{e(st['question'] or 'No question set')}</h1>",
        f"<p class=hyp>Hypothesis: {e(st['hypothesis'])}</p>" if st["hypothesis"] else "<p class=hyp></p>",
        "<div class=tally>" + "".join(
            f"<span class='chip {s}'>{tally[s]} {label[s]}</span>" for s in ("green", "yellow", "red")) + "</div>",
    ]
    order = {"red": 0, "yellow": 1, "green": 2}
    for c, r in sorted(rows, key=lambda x: (order[x[1]["status"]], x[0]["id"])):
        why = r["reasons"] + r["notes"] or ["evidence checks out"]
        parts.append(
            f"<div class=claim><span class='pill {r['status']}'>{label[r['status']]}</span>"
            f"<div class=txt>#{c['id']} {e(c['text'])}</div>"
            "<ul class=why>" + "".join(f"<li>{e(w)}</li>" for w in why) + "</ul></div>")
    if st["graveyard"]:
        parts.append("<h2>Graveyard</h2><ul class=grave>" + "".join(
            f"<li><b>{e(g['idea'])}</b> &mdash; {e(g['why'] or 'buried')}</li>" for g in st["graveyard"]) + "</ul>")
    ok = rec.verify_chain()
    parts.append(
        f"<footer>{st['observations']} tool outputs captured &middot; record integrity: "
        + ("<span class=ok>hash chain intact</span>" if ok else "<span class=bad>BROKEN: history was edited</span>")
        + f" &middot; generated {time.strftime('%Y-%m-%d %H:%M')} by warrant</footer></main></body></html>")
    return "\n".join(parts)


_DRAFT_CSS = """
.draft{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;
white-space:pre-wrap;font-size:16px;line-height:1.7}
.n{border-radius:4px;padding:1px 3px;cursor:help;position:relative;font-weight:600}
.n.ok{background:var(--gb);color:var(--g)}.n.no{background:var(--rb);color:var(--r)}
.n .tip{display:none;position:absolute;left:0;top:1.9em;z-index:2;min-width:260px;max-width:min(520px,80vw);
background:var(--fg);color:var(--bg);font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;font-weight:400;
padding:8px 10px;border-radius:8px;white-space:pre-wrap}
.n:hover .tip,.n:focus .tip{display:block}
"""


def _source_line(rec, label: str, token) -> str:
    """The line of the captured output that holds the value, for the hover card."""
    import re as _re
    from . import provenance as prov
    m = _re.match(r"observation #(\d+)", label or "")
    if not m:
        return ""
    f = rec.dir / "obs" / f"{m.group(1)}.txt"
    if not f.is_file():
        return ""
    ranges = prov.windows(token)
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if any(lo <= v <= hi for v in prov.source_numbers(line) for lo, hi in ranges):
            return line.strip()[:200]
    return ""


def draft_html(rec, text: str, name: str = "draft") -> str:
    """The draft itself, every reported number marked: green (hover: where it came from) or red."""
    from . import provenance as prov
    traced = checks.trace_text(text, rec)
    e = h.escape
    # map each token occurrence back onto the original text, left to right
    out, pos = [], 0
    for tok, hit in traced:
        i = text.find(tok.raw, pos)
        if i < 0:
            continue
        out.append(e(text[pos:i]))
        if hit:
            src = _source_line(rec, hit[0], tok)
            tip = f"{hit[1]}: {hit[0]}" + (f"\n> {src}" if src else "")
            out.append(f"<span class='n ok' tabindex=0>{e(tok.raw)}<span class=tip>{e(tip)}</span></span>")
        else:
            out.append(f"<span class='n no' tabindex=0>{e(tok.raw)}<span class=tip>no command output, "
                       f"file, or record entry produced this number</span></span>")
        pos = i + len(tok.raw)
    out.append(e(text[pos:]))
    ok = sum(1 for _, hit in traced if hit)
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>warrant: {e(name)}</title><style>{_CSS}{_DRAFT_CSS}</style></head><body><main>"
        f"<div class=k>Number provenance</div><h1>{e(name)}</h1>"
        f"<div class=tally><span class='chip green'>{ok} traced to a real source</span>"
        f"<span class='chip red'>{len(traced) - ok} from nowhere</span></div>"
        f"<div class=draft>{''.join(out)}</div>"
        "<footer>Hover a number to see the command output it came from. Generated by warrant.</footer>"
        "</main></body></html>"
    )
