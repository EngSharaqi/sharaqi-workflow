#!/usr/bin/env python3
"""Tables for RESULTS.md from the files run.sh wrote. Prints Markdown; no paths or session ids.

usage: summarize.py <RUNS dir> <PLUGIN dir>
"""
import glob
import json
import os
import re
import statistics
import subprocess
import sys

RUNS, PLUGIN = sys.argv[1], sys.argv[2]
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def transcript_facts(sid):
    """Mode and Route lines, agents spawned, references read, from the main transcript."""
    hits = glob.glob(os.path.join(CONFIG, "projects", "*", sid + ".jsonl"))
    facts = {"mode": "", "route": "", "agents": [], "refs": []}
    if not hits:
        return facts
    with open(hits[0], encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            for c in (d.get("message") or {}).get("content") or []:
                if c.get("type") == "text":
                    t = c["text"]
                    m = re.search(r"Mode:\**\s*\**\s*(FAST|STANDARD|CRITICAL)[^\n]*", t)
                    if m and not facts["mode"]:
                        facts["mode"] = m.group(0).replace("*", "").strip()
                    r = re.search(r"Route:\**\s*([^\n]*)", t)
                    if r and not facts["route"]:
                        facts["route"] = r.group(1).replace("*", "").strip()
                elif c.get("type") == "tool_use":
                    i = c.get("input") or {}
                    if c["name"] in ("Agent", "Task"):
                        facts["agents"].append("%s · %s" % (i.get("subagent_type", "?"), i.get("model", "(none)")))
                    if c["name"] == "Read" and "/references/" in (i.get("file_path") or ""):
                        facts["refs"].append(os.path.basename(i["file_path"]))
    return facts


def run_row(name):
    j = json.loads(read(os.path.join(RUNS, name + ".json")) or "{}")
    err = read(os.path.join(RUNS, name + ".err"))
    hidden = read(os.path.join(RUNS, name + ".hidden"))
    probe = read(os.path.join(RUNS, name + ".probe"))
    npm = read(os.path.join(RUNS, name + ".npm"))
    markers = read(os.path.join(RUNS, name + ".markers")).split()
    status = read(os.path.join(RUNS, name + ".status")).splitlines()
    tokens = read(os.path.join(RUNS, name + ".tokens"))
    p = re.search(r"ℹ pass (\d+)", hidden)
    pr = re.search(r"probe: (\d+)/(\d+)", probe)
    wall = re.search(r"wall_s=(\d+)", err)
    marks = [m for m in markers if m.startswith("marker=")]
    facts = transcript_facts(j.get("session_id", "")) if j.get("session_id") else {}
    refs = sorted(set(facts.get("refs", [])))
    skill_bytes = ""
    if name.startswith("skill"):
        skill_bytes = os.path.getsize(os.path.join(PLUGIN, "SKILL.md")) + sum(
            os.path.getsize(os.path.join(PLUGIN, "references", r)) for r in refs)
    return {
        "name": name,
        "cost": j.get("total_cost_usd"),
        "wall": int(wall.group(1)) if wall else None,
        "turns": j.get("num_turns"),
        "denials": len(j.get("permission_denials") or []),
        "error": j.get("is_error"),
        "hidden": int(p.group(1)) if p else 0,
        "probe": int(pr.group(1)) if pr else 0,
        "probe_fails": [l.split(":")[0][5:] for l in probe.splitlines() if l.startswith("FAIL")],
        "npm_ok": "npm_exit=0" in npm,
        # The fixture commit is the only one a run may have.
        "commits": subprocess.run(["git", "-C", os.path.join(RUNS, name), "rev-list", "--count", "HEAD"],
                                  capture_output=True, text=True).stdout.strip(),
        "changed": len(status),
        "markers": "%d/%d yes" % (marks.count("marker=yes"), len(marks)),
        "models": {m: round(u.get("costUSD", 0), 4) for m, u in (j.get("modelUsage") or {}).items()},
        "tokens_summary": [l for l in tokens.splitlines() if l.startswith(("Tokens:", "By model", "TOKENS:", "|"))],
        "mode": facts.get("mode", ""),
        "route": facts.get("route", ""),
        "agents": facts.get("agents", []),
        "refs": refs,
        "skill_bytes": skill_bytes,
    }


def med_range(xs, fmt):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "—"
    return "%s (%s–%s)" % (fmt % statistics.median(xs), fmt % min(xs), fmt % max(xs))


names = sorted({os.path.basename(f)[:-5] for f in glob.glob(os.path.join(RUNS, "*-*.json"))})
rows = [run_row(n) for n in names]

print("| Run | Cost $ | Wall s | Turns | Hidden /16 | Probe /8 | npm test | Files changed | Commits | Denials | Marker log |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| %s | %.2f | %s | %s | %d | %d%s | %s | %d | %s | %d | %s |" % (
        r["name"], r["cost"] or 0, r["wall"], r["turns"], r["hidden"], r["probe"],
        (" (fail: %s)" % ", ".join(r["probe_fails"])) if r["probe_fails"] else "",
        "pass" if r["npm_ok"] else "FAIL", r["changed"], r["commits"], r["denials"], r["markers"]))
print()
print("| Arm | Cost $ | Wall s | Turns | Hidden /16 | Probe /8 | Succeeded |")
print("|---|---|---|---|---|---|---|")
for arm in ("plain", "skill"):
    a = [r for r in rows if r["name"].startswith(arm)]
    if not a:
        continue
    ok = sum(1 for r in a if r["hidden"] == 16 and r["npm_ok"] and r["commits"] == "1")
    print("| %s | %s | %s | %s | %s | %s | %d/%d |" % (
        arm, med_range([r["cost"] for r in a], "%.2f"), med_range([r["wall"] for r in a], "%d"),
        med_range([r["turns"] for r in a], "%d"), med_range([r["hidden"] for r in a], "%d"),
        med_range([r["probe"] for r in a], "%d"), ok, len(a)))
print()
print("| Run | Claude Code cost per model | Mode | Route | Agents spawned | References read | Skill bytes |")
print("|---|---|---|---|---|---|---|")
for r in rows:
    print("| %s | %s | %s | %s | %s | %s | %s |" % (
        r["name"], ", ".join("%s $%.4f" % kv for kv in r["models"].items()),
        r["mode"] or "—", r["route"] or "—", "; ".join(r["agents"]) or "none",
        ", ".join(r["refs"]) or "none", r["skill_bytes"] or "—"))
print()
for r in rows:
    print("**%s** tokens.py:" % r["name"])
    print()
    print("```")
    print("\n".join(r["tokens_summary"]) or "(no output)")
    print("```")
    print()
