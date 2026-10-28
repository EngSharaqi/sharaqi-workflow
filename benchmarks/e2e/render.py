#!/usr/bin/env python3
"""Build the HTML pages the README screenshots are taken from. Free: reads only run data.

usage: python3 -I render.py <runs-dir> <out-dir>

Every number and every line of text on these pages comes from <runs>/scores.json, the runs'
run.json / stream.jsonl, or <runs>/terminal/*.txt (captured command output). Nothing is typed in.
"""
import html
import json
import os
import sys

TASKS = [("report", "Report: new AI-era jobs, 2026"), ("medium", "Medium code: list API"),
         ("complex", "Complex code: spreadsheet engine")]
CSS = """
body{margin:0;background:#0f1115;color:#e6e6e6;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;padding:28px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#9aa0a6;margin:0 0 20px;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin-bottom:22px}
th,td{padding:7px 10px;border-bottom:1px solid #262a33;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:#9aa0a6;font-weight:600;font-size:12px}
.g{color:#5fd38d}.r{color:#ff7b72}.m{color:#9aa0a6}
.bars{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.card{background:#161a22;border:1px solid #262a33;border-radius:10px;padding:14px}
.card h3{margin:0 0 10px;font-size:13px}.row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px}
.lab{width:52px;color:#9aa0a6}.bar{height:14px;border-radius:3px}.pl{background:#7aa2f7}.pn{background:#e0af68}
pre{background:#0b0d10;border:1px solid #262a33;border-radius:8px;padding:14px;font:12px/1.5 ui-monospace,Menlo,monospace;white-space:pre-wrap;margin:0 0 16px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}.tag{font-size:11px;color:#9aa0a6;margin:0 0 6px}
"""


def page(title, sub, body):
    return (f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title><style>{CSS}"
            f"</style><h1>{html.escape(title)}</h1><p class=sub>{html.escape(sub)}</p>{body}")


def pct(a, b):
    return (a - b) / b * 100 if b else 0


def dashboard(scores, version, plugin_id):
    by = {(s["task"], s["arm"]): s for s in scores}
    rows = ""
    tot = {"plugin": [0, 0], "plain": [0, 0]}
    for t, name in TASKS:
        p, n = by.get((t, "plugin")), by.get((t, "plain"))
        if not p or not n:
            continue
        for a, s in (("plugin", p), ("plain", n)):
            tot[a][0] += s["cost_usd"]
            tot[a][1] += s["wall_s"]
        q = lambda s: (f"{s['hidden']['pass']}/{s['hidden']['tests']}" if "hidden" in s else
                       f"{s['report']['words']} words · {s['report']['urls']} URLs")
        dc, dt = pct(p["cost_usd"], n["cost_usd"]), pct(p["wall_s"], n["wall_s"])
        rows += (f"<tr><td>{html.escape(name)}</td><td>${p['cost_usd']:.3f}</td>"
                 f"<td>${n['cost_usd']:.3f}</td><td class={'g' if dc < 0 else 'r'}>{dc:+.0f}%</td>"
                 f"<td>{p['wall_s']:.0f} s</td><td>{n['wall_s']:.0f} s</td>"
                 f"<td class={'g' if dt < 0 else 'r'}>{dt:+.0f}%</td><td>{q(p)}</td><td>{q(n)}</td></tr>")
    dc, dt = pct(tot["plugin"][0], tot["plain"][0]), pct(tot["plugin"][1], tot["plain"][1])
    rows += (f"<tr><td><b>Total</b></td><td><b>${tot['plugin'][0]:.3f}</b></td>"
             f"<td><b>${tot['plain'][0]:.3f}</b></td><td class={'g' if dc < 0 else 'r'}><b>{dc:+.0f}%</b></td>"
             f"<td><b>{tot['plugin'][1]:.0f} s</b></td><td><b>{tot['plain'][1]:.0f} s</b></td>"
             f"<td class={'g' if dt < 0 else 'r'}><b>{dt:+.0f}%</b></td><td></td><td></td></tr>")
    table = ("<table><tr><th>Task</th><th>Cost · plugin</th><th>Cost · plain</th><th>Δ cost</th>"
             "<th>Wall · plugin</th><th>Wall · plain</th><th>Δ time</th><th>Result · plugin</th>"
             f"<th>Result · plain</th></tr>{rows}</table>")
    cards = ""
    for metric, unit, key in (("Cost", "$", "cost_usd"), ("Wall clock", "s", "wall_s")):
        mx = max(s[key] for s in scores) or 1
        for t, name in TASKS:
            p, n = by.get((t, "plugin")), by.get((t, "plain"))
            if not p or not n:
                continue
            fmt = (lambda v: f"${v:.3f}") if unit == "$" else (lambda v: f"{v:.0f} s")
            cards += (f"<div class=card><h3>{metric} · {html.escape(name)}</h3>"
                      f"<div class=row><span class=lab>plugin</span><div class='bar pl' style='width:{p[key]/mx*220:.0f}px'></div>{fmt(p[key])}</div>"
                      f"<div class=row><span class=lab>plain</span><div class='bar pn' style='width:{n[key]/mx*220:.0f}px'></div>{fmt(n[key])}</div></div>")
    detail = ("<table><tr><th>Run</th><th>Models (cost)</th><th>Main calls</th><th>Sub calls</th>"
              "<th>Turns</th><th>Msgs sent</th><th>Agent calls</th><th>Output tok</th></tr>")
    for s in scores:
        ms = " · ".join(f"{m.replace('claude-', '')} ${u['cost']:.3f}" for m, u in s["models"].items())
        ag = ", ".join(f"{a.get('subagent_type')}·{a.get('model')}·{a.get('effort')}" for a in s["agent_calls"]) or "—"
        detail += (f"<tr><td>{s['arm']} · {s['task']}</td><td>{html.escape(ms)}</td><td>{s['model_calls_main']}</td>"
                   f"<td>{s['model_calls_sub']}</td><td>{s['turns']}</td><td>{s['messages_sent']}</td>"
                   f"<td>{html.escape(ag)}</td><td>{s['output_tokens']:,}</td></tr>")
    detail += "</table>"
    sub = (f"6 runs, one per arm per task, 2026-10-28 · {version} · plugin = sharaqi {plugin_id[:7]}, "
           "/sharaqi:sharaqi do <task>, no model flags · plain = --model claude-opus-5-5 --effort medium · "
           "cost = Claude Code total_cost_usd")
    return page("sharaqi v1.0 vs plain Claude Code — 3 finished tasks", sub,
                table + f"<div class=bars>{cards}</div><br>" + detail)


def terminal(runs):
    d = os.path.join(runs, "terminal")
    body = ""
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        body += f"<p class=tag>$ {html.escape(f[:-4].replace('__', ' '))}</p><pre>{html.escape(open(os.path.join(d, f), encoding='utf-8').read())}</pre>"
    return page("Scoring output, as printed", "score.py and the hidden tests, run on the six work dirs", body)


def replies(runs, task):
    cols = ""
    for arm in ("plugin", "plain"):
        r = json.load(open(os.path.join(runs, f"{arm}-{task}", "run.json"), encoding="utf-8"))
        sent = " → ".join(m["text"][:22] + "…" if len(m["text"]) > 22 else m["text"] for m in r["messages_sent"])
        cols += (f"<div><p class=tag>{arm} · messages sent: {html.escape(sent)}</p>"
                 f"<pre dir=auto>{html.escape(r['final_text'] or '')}</pre></div>")
    name = dict(TASKS)[task]
    return page(f"Final reply, {name}", "the last result event of each run, verbatim", f"<div class=cols>{cols}</div>")


def main():
    runs, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    scores = json.load(open(os.path.join(runs, "scores.json"), encoding="utf-8"))
    version = open(os.path.join(runs, "claude-version.txt")).read().strip()
    pid = open(os.path.join(runs, "plugin.id")).read().strip()
    pages = {"dashboard.html": dashboard(scores, version, pid), "terminal.html": terminal(runs)}
    for t, _ in TASKS:
        pages[f"reply-{t}.html"] = replies(runs, t)
    for name, s in pages.items():
        open(os.path.join(out, name), "w", encoding="utf-8").write(s)
        print(os.path.join(out, name))


if __name__ == "__main__":
    main()
