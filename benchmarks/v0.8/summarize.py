#!/usr/bin/env python3
"""Tables for RESULTS.md from the files run.sh wrote, with the verdict per class by the rules
in PROTOCOL.md. Prints Markdown; no paths or session ids.

usage: summarize.py <RUNS dir>
"""
import glob
import json
import os
import re
import statistics
import subprocess
import sys

RUNS = sys.argv[1]
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
CLASSES = ("tiny", "small", "medium", "large")
HIDDEN = {"tiny": 7, "small": 10, "medium": 13, "large": 16}
PROBE = {"tiny": 4, "small": 8, "medium": 8, "large": 8}
RULE = {"tiny": (1.15, False), "small": (1.15, False), "medium": (0.80, True), "large": (0.80, True)}


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def transcript_facts(sid):
    """The routing card, agents spawned (type · model), and the reviewer trigger line."""
    hits = glob.glob(os.path.join(CONFIG, "projects", "*", sid + ".jsonl"))
    facts = {"card": "", "agents": [], "trigger": ""}
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
                    m = re.search(r"(FAST|STANDARD|CRITICAL)\s*\|\s*Plan:[^\n]*", t)
                    if m and not facts["card"]:
                        facts["card"] = m.group(0).replace("*", "").replace("`", "").strip()
                    r = re.search(r"trigger:\s*([^\n]*)", t)
                    if r:
                        facts["trigger"] = r.group(1).replace("*", "").strip()
                elif c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                    i = c.get("input") or {}
                    facts["agents"].append("%s · %s" % (i.get("subagent_type", "?").replace("sharaqi:", ""),
                                                        i.get("model", "(none)")))
    return facts


def phases(tokens):
    """Rows and summary lines from tokens.py --phases."""
    out = {"rows": [], "orch": "", "spawns": "", "double": ""}
    on = False
    for l in tokens.splitlines():
        if l.startswith("PHASES:"):
            on = True
        elif on and l.startswith("| ") and not l.startswith("| Phase"):
            out["rows"].append(l)
        elif l.startswith("ORCHESTRATOR:"):
            out["orch"] = l[len("ORCHESTRATOR: "):]
        elif l.startswith("SPAWNS:"):
            out["spawns"] = l[len("SPAWNS: "):]
        elif l.startswith("DOUBLE_READS:"):
            out["double"] = l[len("DOUBLE_READS: "):]
    return out


def run_row(name):
    task = name.split("-")[0]
    j = json.loads(read(os.path.join(RUNS, name + ".json")) or "{}")
    hidden = read(os.path.join(RUNS, name + ".hidden"))
    probe = read(os.path.join(RUNS, name + ".probe"))
    markers = read(os.path.join(RUNS, name + ".markers")).split()
    marks = [m for m in markers if m.startswith("marker=")]
    p = re.search(r"ℹ pass (\d+)", hidden)
    pr = re.search(r"probe: (\d+)/(\d+)", probe)
    wall = re.search(r"wall_s=(\d+)", read(os.path.join(RUNS, name + ".err")))
    sid = j.get("session_id")
    return {
        "name": name, "task": task, "arm": name.split("-")[1],
        "cost": j.get("total_cost_usd"), "wall": int(wall.group(1)) if wall else None,
        "turns": j.get("num_turns"), "denials": len(j.get("permission_denials") or []),
        "error": j.get("is_error"),
        "hidden": int(p.group(1)) if p else 0, "probe": int(pr.group(1)) if pr else 0,
        "probe_fails": [l.split(":")[0][5:].split(" ")[0] for l in probe.splitlines() if l.startswith("FAIL")],
        "npm_ok": "npm_exit=0" in read(os.path.join(RUNS, name + ".npm")),
        "commits": subprocess.run(["git", "-C", os.path.join(RUNS, name), "rev-list", "--count", "HEAD"],
                                  capture_output=True, text=True).stdout.strip(),
        "changed": len(read(os.path.join(RUNS, name + ".status")).splitlines()),
        "marker_yes": marks.count("marker=yes"), "marker_n": len(marks),
        "models": {m: round(u.get("costUSD", 0), 4) for m, u in (j.get("modelUsage") or {}).items()},
        "facts": transcript_facts(sid) if sid else {"card": "", "agents": [], "trigger": ""},
        "phases": phases(read(os.path.join(RUNS, name + ".tokens"))),
    }


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def rng(xs, fmt):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "—"
    return "%s (%s–%s)" % (fmt % statistics.median(xs), fmt % min(xs), fmt % max(xs))


names = sorted({os.path.basename(f)[:-5] for f in glob.glob(os.path.join(RUNS, "*-*-*.json"))
                if not os.path.basename(f).startswith("route-")})
rows = [run_row(n) for n in names]

print("## Per run\n")
print("| Run | Cost $ | Wall s | Turns | Hidden | Probe | npm test | Files changed | Commits | Denials | Marker log |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| %s | %.2f | %s | %s | %d/%d | %d/%d%s | %s | %d | %s | %d | %d/%d yes |" % (
        r["name"], r["cost"] or 0, r["wall"], r["turns"], r["hidden"], HIDDEN[r["task"]],
        r["probe"], PROBE[r["task"]], (" (fail: %s)" % ", ".join(r["probe_fails"])) if r["probe_fails"] else "",
        "pass" if r["npm_ok"] else "FAIL", r["changed"], r["commits"], r["denials"],
        r["marker_yes"], r["marker_n"]))

print("\n## Per class: median (range), and the verdict\n")
print("| Class | Arm | Cost $ | Wall s | Turns | Hidden | Probe | Valid runs |")
print("|---|---|---|---|---|---|---|---|")
verdicts = []
for c in CLASSES:
    arms = {a: [r for r in rows if r["task"] == c and r["arm"] == a] for a in ("plain", "skill")}
    if not arms["plain"] or not arms["skill"]:
        continue
    for a, rs in arms.items():
        valid = sum(1 for r in rs if (r["marker_yes"] == 0 if a == "plain" else r["marker_yes"] == r["marker_n"] > 0))
        print("| %s | %s | %s | %s | %s | %s | %s | %d/%d |" % (
            c, "sharaqi" if a == "skill" else a, rng([r["cost"] for r in rs], "%.2f"),
            rng([r["wall"] for r in rs], "%d"), rng([r["turns"] for r in rs], "%d"),
            rng([r["hidden"] for r in rs], "%d"), rng([r["probe"] for r in rs], "%d"), valid, len(rs)))
    P, K = arms["plain"], arms["skill"]
    min_plain_probe = min(r["probe"] for r in P)
    correct = all(r["hidden"] == HIDDEN[c] and r["npm_ok"] and r["commits"] == "1"
                  and r["probe"] >= min_plain_probe for r in K)
    ratio_c = med([r["cost"] for r in K]) / med([r["cost"] for r in P])
    ratio_t = med([r["wall"] for r in K]) / med([r["wall"] for r in P])
    limit, need_sep = RULE[c]
    sep_c = max(r["cost"] for r in K) < min(r["cost"] for r in P)
    sep_t = max(r["wall"] for r in K) < min(r["wall"] for r in P)
    met = correct and ratio_c <= limit and ratio_t <= limit and (not need_sep or (sep_c and sep_t))
    verdicts.append((c, ratio_c, ratio_t, limit, need_sep, sep_c, sep_t, correct, met))

print("\n| Class | Cost ratio (sharaqi/plain, medians) | Time ratio | Rule | Ranges separate (cost · time) | Correctness | Verdict |")
print("|---|---|---|---|---|---|---|")
for c, rc, rt, lim, need, sc, st, ok, met in verdicts:
    print("| %s | %.2f | %.2f | both ≤ %.2f%s | %s | %s | **%s** |" % (
        c, rc, rt, lim, ", ranges separate" if need else "",
        ("%s · %s" % ("yes" if sc else "no", "yes" if st else "no")) if need else "n/a",
        "equal" if ok else "NOT equal", "met" if met else "not met"))

print("\n## What sharaqi did\n")
print("| Run | Card | Agents spawned | Spawns | Reviewer trigger | Orchestrator | Double reads |")
print("|---|---|---|---|---|---|---|")
for r in rows:
    if r["arm"] != "skill":
        continue
    f, ph = r["facts"], r["phases"]
    print("| %s | %s | %s | %s | %s | %s | %s |" % (
        r["name"], f["card"] or "—", "; ".join(f["agents"]) or "none", ph["spawns"] or "—",
        f["trigger"] or "—", ph["orch"] or "—", ph["double"] or "—"))

print("\n## Cost per phase (tokens.py --phases)\n")
for r in rows:
    if r["arm"] != "skill":
        continue
    print("**%s**\n" % r["name"])
    print("| Phase | Agent | Model | Effort recorded | Requests | Output | List-price $ |")
    print("|---|---|---|---|---|---|---|")
    print("\n".join(r["phases"]["rows"]) or "(no output)")
    print()
