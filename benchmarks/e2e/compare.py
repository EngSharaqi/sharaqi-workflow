#!/usr/bin/env python3
"""Build comparison pages for a multi-run round (drive.py --rep). Free: reads only run data.

usage: python3 -I compare.py <runs-dir> <out-dir>

Every number comes from <runs>/scores.json (score.py), the runs' run.json, or
<runs>/terminal/*.txt. Means are over the reps of one task and arm; nothing is typed in.
"""
import html
import json
import os
import statistics
import sys

TASKS = [("simple", "Simple: duration rounding bug"), ("medium", "Medium: orders API"),
         ("complex", "Complex: dependency resolver"), ("research", "Research: vector DB report")]
ARMS = ("plugin", "plain")
CSS = """
body{margin:0;background:#0f1115;color:#e6e6e6;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;padding:28px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px}.sub{color:#9aa0a6;margin:0 0 20px;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin-bottom:18px}
th,td{padding:6px 9px;border-bottom:1px solid #262a33;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:#9aa0a6;font-weight:600;font-size:12px}
.g{color:#5fd38d}.r{color:#ff7b72}.m{color:#9aa0a6}.w{white-space:normal;text-align:left}
.bars{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.card{background:#161a22;border:1px solid #262a33;border-radius:10px;padding:12px}
.card h3{margin:0 0 8px;font-size:12.5px}.row{display:flex;align-items:center;gap:8px;margin:4px 0;font-size:12px}
.lab{width:46px;color:#9aa0a6}.bar{height:13px;border-radius:3px}.pl{background:#7aa2f7}.pn{background:#e0af68}
pre{background:#0b0d10;border:1px solid #262a33;border-radius:8px;padding:12px;font:12px/1.5 ui-monospace,Menlo,monospace;white-space:pre-wrap;margin:0 0 14px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}.tag{font-size:11px;color:#9aa0a6;margin:0 0 6px}
"""


def page(title, sub, body):
    return (f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title><style>{CSS}"
            f"</style><h1>{html.escape(title)}</h1><p class=sub>{html.escape(sub)}</p>{body}")


def pct(a, b):
    return (a - b) / b * 100 if b else 0


def cls(d, lower_is_better=True):
    return "g" if (d < 0) == lower_is_better and d != 0 else ("r" if d != 0 else "m")


def quality(s):
    if "hidden" in s:
        h = s["hidden"]
        return h.get("pass") or 0, h.get("tests") or 0, f"{h.get('pass')}/{h.get('tests')}"
    r = s.get("report") or {}
    if not r.get("exists"):
        return 0, 1, "no report.md"
    return (r.get("rubric_hit", 0), r.get("rubric_of", 0),
            f"rubric {r.get('rubric_hit')}/{r.get('rubric_of')} · {r.get('links_ok', '?')}/{r.get('urls')} links ok")


def group(scores):
    g = {}
    for s in scores:
        g.setdefault((s["task"], s["arm"]), []).append(s)
    for v in g.values():
        v.sort(key=lambda s: str(s.get("rep")))
    return g


def mean(xs):
    return statistics.mean(xs) if xs else 0


def dashboard(scores, version, pid):
    g = group(scores)
    rows, tot = "", {a: [0.0, 0.0] for a in ARMS}
    for t, name in TASKS:
        p, n = g.get((t, "plugin"), []), g.get((t, "plain"), [])
        if not p or not n:
            continue
        pc, nc = mean([s["cost_usd"] for s in p]), mean([s["cost_usd"] for s in n])
        pw, nw = mean([s["wall_s"] for s in p]), mean([s["wall_s"] for s in n])
        tot["plugin"][0] += pc; tot["plain"][0] += nc; tot["plugin"][1] += pw; tot["plain"][1] += nw
        cost = lambda xs: " · ".join(f"${s['cost_usd']:.3f}" for s in xs)
        wall = lambda xs: " · ".join(f"{s['wall_s']:.0f}" for s in xs)
        qual = lambda xs: " · ".join(quality(s)[2] for s in xs)
        dc, dt = pct(pc, nc), pct(pw, nw)
        rows += (f"<tr><td>{html.escape(name)}</td>"
                 f"<td>${pc:.3f}<br><span class=m>{cost(p)}</span></td>"
                 f"<td>${nc:.3f}<br><span class=m>{cost(n)}</span></td>"
                 f"<td class={cls(dc)}>{dc:+.0f}%</td>"
                 f"<td>{pw:.0f} s<br><span class=m>{wall(p)}</span></td>"
                 f"<td>{nw:.0f} s<br><span class=m>{wall(n)}</span></td>"
                 f"<td class={cls(dt)}>{dt:+.0f}%</td>"
                 f"<td>{qual(p)}</td><td>{qual(n)}</td></tr>")
    dc, dt = pct(tot["plugin"][0], tot["plain"][0]), pct(tot["plugin"][1], tot["plain"][1])
    rows += (f"<tr><td><b>Total (sum of means)</b></td><td><b>${tot['plugin'][0]:.3f}</b></td>"
             f"<td><b>${tot['plain'][0]:.3f}</b></td><td class={cls(dc)}><b>{dc:+.0f}%</b></td>"
             f"<td><b>{tot['plugin'][1]:.0f} s</b></td><td><b>{tot['plain'][1]:.0f} s</b></td>"
             f"<td class={cls(dt)}><b>{dt:+.0f}%</b></td><td></td><td></td></tr>")
    table = ("<table><tr><th>Task</th><th>Cost · plugin<br>mean (runs)</th><th>Cost · plain</th>"
             "<th>Δ cost</th><th>Wall · plugin</th><th>Wall · plain</th><th>Δ time</th>"
             f"<th>Quality · plugin (per run)</th><th>Quality · plain</th></tr>{rows}</table>")
    cards = ""
    for metric, key, fmt in (("Cost", "cost_usd", lambda v: f"${v:.3f}"),
                             ("Wall clock", "wall_s", lambda v: f"{v:.0f} s")):
        vals = {k: mean([s[key] for s in v]) for k, v in g.items()}
        mx = max(vals.values()) or 1
        for t, name in TASKS:
            if (t, "plugin") not in vals or (t, "plain") not in vals:
                continue
            a, b = vals[(t, "plugin")], vals[(t, "plain")]
            cards += (f"<div class=card><h3>{metric} · {html.escape(name)}</h3>"
                      f"<div class=row><span class=lab>plugin</span><div class='bar pl' style='width:{a/mx*170:.0f}px'></div>{fmt(a)}</div>"
                      f"<div class=row><span class=lab>plain</span><div class='bar pn' style='width:{b/mx*170:.0f}px'></div>{fmt(b)}</div></div>")
    n = len(scores)
    sub = (f"{n} runs, 2 per arm per task, held-out tasks written 2026-10-29 · {version} · plugin = "
           f"sharaqi {pid[:7]} (working tree), /sharaqi:sharaqi do <task>, no model flags · plain = "
           "--model claude-opus-5-5 --effort medium · cost = Claude Code total_cost_usd")
    return page("sharaqi vs plain Claude Code (Opus 5.5 · medium), 4 held-out tasks", sub,
                table + f"<div class=bars>{cards}</div>")


def detail(scores):
    body = ("<table><tr><th>Run</th><th>Route (plugin)</th><th>Models (cost)</th><th>Agent calls</th>"
            "<th>Turns</th><th>Msgs</th><th>Out tok</th><th>Lines +/−</th></tr>")
    for s in sorted(scores, key=lambda s: ([t for t, _ in TASKS].index(s["task"]), s["arm"], str(s["rep"]))):
        ms = " · ".join(f"{m.replace('claude-', '')} ${u['cost']:.3f}" for m, u in s["models"].items())
        ag = ", ".join(f"{a.get('subagent_type')}·{a.get('model')}·{a.get('effort')}" for a in s["agent_calls"]) or "—"
        rt = s.get("route") or "—"
        short = " ".join(kv for kv in rt.split() if kv.split("=")[0] in ("tier", "executor", "review", "escalate")) or rt
        add = sum(f["added"] for f in s["changed"]); dele = sum(f["deleted"] for f in s["changed"])
        body += (f"<tr><td>{s['run']}</td><td class=w>{html.escape(short)}</td><td class=w>{html.escape(ms)}</td>"
                 f"<td class=w>{html.escape(ag)}</td><td>{s['turns']}</td><td>{s['messages_sent']}</td>"
                 f"<td>{s['output_tokens']:,}</td><td>+{add} −{dele}</td></tr>")
    body += "</table>"
    return page("Per run: route, models, agents, tokens", "from scores.json", body)


def quality_page(scores):
    body = "<h2>Code tasks: hidden tests and the arm's own tests</h2><table><tr><th>Run</th><th>Hidden</th>" \
           "<th>Failed hidden tests</th><th>Own tests (pass/total)</th><th>Code lines +</th><th>Test lines +</th></tr>"
    for s in sorted(scores, key=lambda s: s["run"]):
        if "hidden" not in s:
            continue
        h, o = s["hidden"], s["own_tests"]
        code = sum(f["added"] for f in s["changed"] if not f["file"].startswith("test/"))
        tst = sum(f["added"] for f in s["changed"] if f["file"].startswith("test/"))
        body += (f"<tr><td>{s['run']}</td><td>{h['pass']}/{h['tests']}</td><td class=w>{html.escape(', '.join(h['failed'])) or '—'}</td>"
                 f"<td>{o['pass']}/{o['tests']} (exit {o['exit']})</td><td>{code}</td><td>{tst}</td></tr>")
    body += "</table><h2>Research: report metrics</h2><table><tr><th>Run</th><th>Words</th><th>Headings</th>" \
            "<th>Tables</th><th>URLs</th><th>Domains</th><th>Links ok</th><th>403/429</th><th>Rubric</th><th>Missed</th></tr>"
    for s in sorted(scores, key=lambda s: s["run"]):
        r = s.get("report")
        if not r:
            continue
        if not r.get("exists"):
            body += f"<tr><td>{s['run']}</td><td colspan=9>no report.md</td></tr>"
            continue
        missed = [k for k, v in (r.get("rubric") or {}).items() if not v]
        body += (f"<tr><td>{s['run']}</td><td>{r['words']:,}</td><td>{r['headings']}</td><td>{r['tables']}</td>"
                 f"<td>{r['urls']}</td><td>{r['domains']}</td><td>{r.get('links_ok', '?')}</td><td>{r.get('links_403', '?')}</td>"
                 f"<td>{r.get('rubric_hit')}/{r.get('rubric_of')}</td><td class=w>{html.escape(', '.join(missed)) or '—'}</td></tr>")
    body += "</table>"
    return page("Quality", "hidden tests (never shown to either arm) · report coverage by regex, links by curl", body)


def terminal(runs):
    d = os.path.join(runs, "terminal")
    body = ""
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        body += f"<p class=tag>$ {html.escape(f[:-4].replace('__', ' '))}</p><pre>{html.escape(open(os.path.join(d, f), encoding='utf-8').read())}</pre>"
    return page("Scoring output, as printed", "score.py and the hidden tests", body)


def replies(runs, task, rep="1"):
    cols = ""
    for arm in ARMS:
        p = os.path.join(runs, f"{arm}-{task}-{rep}", "run.json")
        if not os.path.exists(p):
            continue
        r = json.load(open(p, encoding="utf-8"))
        sent = " → ".join(m["text"][:22] + "…" if len(m["text"]) > 22 else m["text"] for m in r["messages_sent"])
        cols += (f"<div><p class=tag>{arm} · run {rep} · messages sent: {html.escape(sent)}</p>"
                 f"<pre dir=auto>{html.escape(r['final_text'] or '')}</pre></div>")
    return page(f"Final reply, {dict(TASKS)[task]}", f"the last result event of run {rep} of each arm, verbatim",
                f"<div class=cols>{cols}</div>")


def main():
    runs, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    scores = json.load(open(os.path.join(runs, "scores.json"), encoding="utf-8"))
    version = open(os.path.join(runs, "claude-version.txt")).read().strip()
    pid = open(os.path.join(runs, "plugin.id")).read().strip()
    pages = {"1-dashboard.html": dashboard(scores, version, pid), "2-quality.html": quality_page(scores),
             "3-detail.html": detail(scores), "4-terminal.html": terminal(runs)}
    for i, (t, _) in enumerate(TASKS):
        pages[f"{5 + i}-reply-{t}.html"] = replies(runs, t)
    for name, s in pages.items():
        open(os.path.join(out, name), "w", encoding="utf-8").write(s)
        print(os.path.join(out, name))


if __name__ == "__main__":
    main()
