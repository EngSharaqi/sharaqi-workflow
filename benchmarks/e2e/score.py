#!/usr/bin/env python3
"""Score every <runs>/<arm>-<task> made by drive.py. Free: no model call.

usage: python3 -I score.py <runs-dir> [--links]   (--links: HEAD-check every URL in report.md)

Cost is Claude Code's own `total_cost_usd` from the run's last result event (cumulative for the
session; checked against the sum of modelUsage costUSD). Code tasks: the hidden tests are copied
into a scratch copy of the run's work dir and run there; the arm's own `npm test` is re-run too.
Writes <runs>/scores.json and prints a summary.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def node_tests(work, files):
    r = subprocess.run(["node", "--test", *files], cwd=work, capture_output=True, text=True,
                       timeout=300)
    out = r.stdout + r.stderr
    num = lambda k: int(m.group(1)) if (m := re.search(rf"^ℹ {k} (\d+)", out, re.M)) else None
    failed = re.findall(r"^✖ (.+?) \(", out, re.M)
    return {"pass": num("pass"), "fail": num("fail"), "tests": num("tests"),
            "failed": sorted(set(f.strip() for f in failed))}


def code_scores(work, task):
    tmp = tempfile.mkdtemp()
    shutil.copytree(work, tmp, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    shutil.copy(os.path.join(HERE, "hidden", task, "hidden.test.js"), os.path.join(tmp, "test"))
    hidden = node_tests(tmp, ["test/hidden.test.js"])
    os.remove(os.path.join(tmp, "test", "hidden.test.js"))
    own = subprocess.run(["npm", "test"], cwd=tmp, capture_output=True, text=True, timeout=300)
    ownout = own.stdout + own.stderr
    m = lambda k: int(x.group(1)) if (x := re.search(rf"^ℹ {k} (\d+)", ownout, re.M)) else None
    shutil.rmtree(tmp)
    return {"hidden": hidden, "own_tests": {"exit": own.returncode, "tests": m("tests"),
                                            "pass": m("pass"), "fail": m("fail")}}


def diff_stat(work):
    subprocess.run(["git", "add", "-A", "-N"], cwd=work, capture_output=True)
    r = subprocess.run(["git", "diff", "--numstat", "HEAD"], cwd=work, capture_output=True,
                       text=True)
    files = []
    for line in r.stdout.splitlines():
        a, d, f = line.split("\t")
        files.append({"file": f, "added": int(a) if a != "-" else 0,
                      "deleted": int(d) if d != "-" else 0})
    return files


def report_scores(work, links):
    p = os.path.join(work, "report.md")
    if not os.path.exists(p):
        return {"exists": False}
    s = open(p, encoding="utf-8").read()
    urls = sorted(set(u.rstrip(").,;]>»'\"") for u in re.findall(r"https?://[^\s)\]>\"'»]+", s)))
    domains = sorted(set(re.sub(r"^https?://(www\.)?", "", u).split("/")[0] for u in urls))
    heads = re.findall(r"^(#{1,4})\s+(.+)$", s, re.M)
    res = {
        "exists": True, "bytes": len(s.encode()), "words": len(s.split()),
        "lines": s.count("\n") + 1, "headings": len(heads),
        "h2": sum(1 for h, _ in heads if h == "##"), "h3": sum(1 for h, _ in heads if h == "###"),
        "tables": len(re.findall(r"^\|[-: |]+\|$", s, re.M)),
        "urls": len(urls), "domains": len(domains),
        "salary_mentions": len(re.findall(r"\$\s?\d|\d\s?(?:دولار|ريال|USD|ألف)|راتب|رواتب", s)),
    }
    if links:
        live = []
        for u in urls:
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "-m", "15", "-A",
                                "Mozilla/5.0", "-w", "%{http_code}", u], capture_output=True,
                               text=True)
            live.append({"url": u, "code": r.stdout.strip()})
        res["links"] = live
        res["links_ok"] = sum(1 for x in live if x["code"].startswith(("2", "3")))
        res["links_403"] = sum(1 for x in live if x["code"] in ("401", "403", "429"))
    return res


def run_scores(d, links):
    run = json.load(open(os.path.join(d, "run.json"), encoding="utf-8"))
    last = run["results"][-1] if run["results"] else {}
    usage = last.get("modelUsage") or {}
    models = {m: {"cost": round(u.get("costUSD", 0), 4), "in": u.get("inputTokens", 0),
                  "out": u.get("outputTokens", 0), "cache_read": u.get("cacheReadInputTokens", 0),
                  "cache_write": u.get("cacheCreationInputTokens", 0),
                  "web_search": u.get("webSearchRequests", 0)}
              for m, u in usage.items()}
    stream = [json.loads(l) for l in open(os.path.join(d, "stream.jsonl"), encoding="utf-8")
              if l.strip().startswith("{")]
    tools, agents = {}, []
    for ev in stream:
        if ev.get("type") != "assistant":
            continue
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "tool_use":
                tools[c["name"]] = tools.get(c["name"], 0) + 1
                if c["name"] in ("Agent", "Task"):
                    i = c.get("input", {})
                    agents.append({k: i.get(k) for k in ("subagent_type", "model", "effort",
                                                         "description")})
    route = None
    ev_path = os.path.join(d, "sharaqi-events.jsonl")
    if os.path.exists(ev_path):
        for l in open(ev_path, encoding="utf-8"):
            m = re.search(r"ROUTE[^\"\\]*", l)
            if m and route is None:
                route = m.group(0)
    total = last.get("total_cost_usd")
    out = {
        "arm": run["arm"], "task": run["task"], "exit_code": run["exit_code"],
        "timed_out": run["timed_out"], "errors": [r["subtype"] for r in run["results"]
                                                  if r.get("is_error")],
        "cost_usd": total, "cost_check_sum_models": round(sum(m["cost"] for m in models.values()), 4),
        "wall_s": run["wall_s"],
        # duration_api_ms and total_cost_usd are cumulative per session; duration_ms is per message.
        "api_s": round((last.get("duration_api_ms") or 0) / 1000, 1),
        "cli_s": round(sum((r.get("duration_ms") or 0) for r in run["results"]) / 1000, 1),
        "model_calls_main": len({e["message"]["id"] for e in stream if e.get("type") == "assistant"
                                 and not e.get("parent_tool_use_id")}),
        "model_calls_sub": len({e["message"]["id"] for e in stream if e.get("type") == "assistant"
                                and e.get("parent_tool_use_id")}),
        "turns": sum((r.get("num_turns") or 0) for r in run["results"]),
        "messages_sent": len(run["messages_sent"]), "go_sent": len(run["messages_sent"]) - 1,
        "models": models, "tools": tools, "agent_calls": agents, "route": route,
        "output_tokens": sum(m["out"] for m in models.values()),
        "changed": diff_stat(os.path.join(d, "work")),
    }
    work = os.path.join(d, "work")
    if run["task"] == "report":
        out["report"] = report_scores(work, links)
    else:
        out.update(code_scores(work, run["task"]))
    return out


def main():
    runs = os.path.abspath(sys.argv[1])
    links = "--links" in sys.argv
    scores = []
    for name in sorted(os.listdir(runs)):
        d = os.path.join(runs, name)
        if os.path.isfile(os.path.join(d, "run.json")):
            scores.append(run_scores(d, links))
    json.dump(scores, open(os.path.join(runs, "scores.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for s in scores:
        q = (s.get("hidden") and f"hidden {s['hidden']['pass']}/{s['hidden']['tests']}") or \
            (s.get("report") and f"words {s['report'].get('words')} urls {s['report'].get('urls')}")
        print(f"{s['arm']:6} {s['task']:8} ${s['cost_usd']:.4f} wall {s['wall_s']:7.1f}s "
              f"turns {s['turns']:3} go {s['go_sent']} {q} models {list(s['models'])}")


if __name__ == "__main__":
    main()
