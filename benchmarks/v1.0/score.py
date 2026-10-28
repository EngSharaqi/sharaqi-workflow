#!/usr/bin/env python3
"""Scoring for the three-arm routing benchmark. Standard library only.

  score.py <RUNS>                           after runall.sh: route score, isolation, totals
  score.py --preflight <capture dir> <arm> <case>   one preflight check (preflight.sh)

Route score: the fields in expected.json for the arm, against the route the arm produced
(v0.9: the ROUTE line its reply printed; v1.0: the prompt hook's ROUTE from the events log,
and the reply must print the same line). Plain exposes no route: not scored. Isolation: the
stream-json init event lists the plugins and agents each run actually had.

A partial RUNS is scored, not refused: an unreadable record is listed as such, every
arm x case of every rep seen without a usable record is listed as missing, a failed run's
cost stays unknown, and the exit status is 1 whenever anything is missing or unreadable.
"""
import glob
import json
import os
import re
import sys

B = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(B, "expected.json"), encoding="utf-8") as fh:
    EXP = json.load(fh)
AGENTS = {
    "plain": set(),
    "v0.9": {"sharaqi:implementer", "sharaqi:implementer-low", "sharaqi:implementer-high",
             "sharaqi:planner", "sharaqi:reviewer", "sharaqi:reviewer-medium",
             "sharaqi:reviewer-high"},
    "v1.0": {"sharaqi:implementer", "sharaqi:planner", "sharaqi:reviewer"},
}
SEAT = {"plain": "claude-opus-5-5", "v0.9": "claude-opus-5-5", "v1.0": "claude-sonnet-5-5"}
SKILL_MARK = {"v0.9": "Opus routes, the cheapest capable rung implements",
              "v1.0": "Sonnet seat, Opus on escalation"}
ROUTE = re.compile(r"ROUTE track=\S+(?: [a-z_]+=\S+)*")
# Markdown that a reply wraps around its ROUTE line (`ROUTE …` or **ROUTE …**) sticks to the
# last value, since ROUTE matches \S+. Only backticks, asterisks and whitespace at the very end
# are dropped; nothing inside the line is touched, so a wrong value stays wrong.
TRAILING_MARKDOWN = re.compile(r"[`*\s]+$")
ARMS = ("plain", "v0.9", "v1.0")
CASES = ("1", "2", "3", "4", "5", "6", "7a", "7b", "8", "9", "10")
RUN_NAME = re.compile(r"^(plain|v0\.9|v1\.0)-(\w+)-(\d+)$")


def clean_route(line):
    """(route line without trailing Markdown delimiters, whether any were dropped)."""
    if not line:
        return None, False
    clean = TRAILING_MARKDOWN.sub("", line)
    return clean, clean != line


def fields(line):
    return dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)


def misses(arm, cid, route_line):
    want = EXP[arm][cid]
    route_line, _ = clean_route(route_line)
    got = fields(route_line) if route_line else {}
    return ["%s=%s (got %s)" % (k, v, got.get(k, "-")) for k, v in want.items() if got.get(k) != v]


def preflight(cap, arm, cid):
    reqs = []
    for f in sorted(glob.glob(os.path.join(cap, "req-*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                reqs.append(json.load(fh))
        except (OSError, ValueError):
            pass
    task = open(os.path.join(B, "cases", cid), encoding="utf-8").read().strip()
    needle = json.dumps(task[:40], ensure_ascii=False)[1:-1]  # as it appears inside JSON
    main = [d for d in reqs if needle in json.dumps(d.get("messages", []), ensure_ascii=False)]
    problems = []
    if not main:
        print("FAIL %s %s: no request carried the case text" % (arm, cid))
        return 1
    d = main[0]
    body = json.dumps(d, ensure_ascii=False)
    if d.get("model") != SEAT[arm]:
        problems.append("seat %s, want %s" % (d.get("model"), SEAT[arm]))
    listed = set(re.findall(r"sharaqi:[a-z-]+", body)) - {"sharaqi:sharaqi"}
    if listed != AGENTS[arm]:
        problems.append("agents %s" % sorted(listed))
    if arm == "plain":
        for mark in ("SHARAQI v", "/sharaqi", SKILL_MARK["v0.9"], SKILL_MARK["v1.0"]):
            if mark in body:
                problems.append("plain carries %r" % mark)
    else:
        if SKILL_MARK[arm] not in body:
            problems.append("skill text missing")
    if arm == "v1.0":
        m = ROUTE.search(body.replace("\\n", "\n"))
        if "SHARAQI v1.0" not in body or not m:
            problems.append("no hook ROUTE")
        else:
            problems += misses("v1.0", cid, m.group(0))
    print("%s %s %s%s" % ("FAIL" if problems else "PASS", arm, cid,
                          ": " + "; ".join(problems) if problems else ""))
    return 1 if problems else 0


def init_event(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") == "system" and d.get("subtype") == "init":
                    return d
    except OSError:
        pass
    return None


def load_runrecord(runs):
    """The frozen runrecord module of this RUNS (the same accounting the runs used)."""
    import importlib.util
    path = os.path.join(runs, "plugins", "v1.0", "scripts", "runrecord.py")
    spec = importlib.util.spec_from_file_location("runrecord", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return path, mod


def route_verdict(r):
    """(route verdict, format note) for one record. Route correctness is judged on the line
    without trailing Markdown; the format note says whether any had to be dropped."""
    arm, cid = r["arm"], r["case_id"]
    if arm == "plain":
        return "not exposed", "-"
    raw = (r.get("route_printed") or [None])[-1]
    printed, stripped = clean_route(raw)
    if arm == "v0.9":
        route = printed
    else:
        route, hook_stripped = clean_route(((r.get("events") or {}).get("route") or {}).get("route"))
        stripped = stripped or hook_stripped
    m = misses(arm, cid, route)
    if arm == "v1.0" and route and printed and printed != route \
            and EXP["entry"].get(cid) != "review":
        m.append("printed route differs from the hook's")
    if not route:
        fmt = "no route"
    else:
        fmt = "trailing Markdown dropped" if stripped else "clean"
    if r["status"] != "completed" and not route:
        return "FAIL: no route (run %s)" % r["status"], fmt
    return ("PASS" if not m else "FAIL: " + "; ".join(m)), fmt


def score(runs):
    rr_path, rr = load_runrecord(runs)
    paths = sorted(glob.glob(os.path.join(runs, "records", "*.json")))
    good, bad, seen, reps = [], [], set(), set()
    print("| Run | Status | $ | Wall s | Route | Route format | Isolation |")
    print("|---|---|---|---|---|---|---|")
    right = {}
    for p in paths:
        r, problems = rr.load_record(p)
        name = os.path.basename(p)[:-len(".json")]
        if r is None:
            bad.append(name)
            print("| %s | unreadable record (%s) | unknown | - | not scored | - | - |"
                  % (name, "; ".join(problems)))
            continue
        good.append(p)
        arm, cid = r["arm"], r["case_id"]
        m = RUN_NAME.match(r["run_id"] or "")
        if m:
            seen.add(r["run_id"])
            reps.add(m.group(3))
        verdict, fmt = route_verdict(r)
        if arm != "plain":
            right.setdefault(arm, [0, 0, 0])
            right[arm][0] += verdict == "PASS"
            right[arm][1] += 1
            right[arm][2] += fmt == "trailing Markdown dropped"
        init = init_event(os.path.join(runs, "out", r["run_id"] + ".jsonl")) or {}
        listed = {a for a in init.get("agents") or [] if str(a).startswith("sharaqi:")}
        iso = "ok" if listed == AGENTS[arm] else "agents %s" % sorted(listed)
        if not init:
            iso = "no init event"
        status = r["status"]
        if r.get("failure"):
            status += " (%s, rc=%s)" % (r["failure"].get("reason"), r["failure"].get("exit_code"))
        cost = r["cost"]["actual_usd"]
        print("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["run_id"], status, "%.4f" % cost if cost is not None else "unknown",
            r.get("wall_s"), verdict, fmt, iso))
    print()
    for arm, (ok, n, stripped) in right.items():
        print("Routes as expected, %s: %d/%d (route lines with trailing Markdown dropped: %d)"
              % (arm, ok, n, stripped))
    # Missing: every arm x case of every rep that any record or output file names.
    outs = [os.path.basename(f)[:-len(".jsonl")]
            for f in glob.glob(os.path.join(runs, "out", "*.jsonl"))]
    for name in outs + bad:
        m = RUN_NAME.match(name)
        if m:
            reps.add(m.group(3))
    missing = ["%s-%s-%s" % (a, c, n) for n in sorted(reps, key=int) for c in CASES
               for a in ARMS if "%s-%s-%s" % (a, c, n) not in seen]
    print("Missing runs (no usable record): %s" % (", ".join(missing) if missing else "none"))
    print("Unreadable records: %s" % (", ".join(bad) if bad else "none"))
    print()
    sys.stdout.flush()
    rc = rr.summarize(good) if good else 0
    if not good:
        print("No usable records: no totals.")
    incomplete = bool(missing or bad)
    return 1 if incomplete else rc


def main(argv):
    if argv[:1] == ["--preflight"] and len(argv) == 4:
        return preflight(*argv[1:])
    if len(argv) == 1:
        return score(argv[0])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
