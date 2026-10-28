#!/usr/bin/env python3
"""One JSON record per benchmark run, and a summary across records. Standard library only.

Cost accounting (the same for every arm):
- actual_usd is Claude Code's own `total_cost_usd` from the run's result event. It already
  includes subagents, so nothing is added to it.
- per-model tokens and costUSD come from the result's `modelUsage` (also Claude Code's).
- transcript_estimate_usd prices each request found in the main transcript and its
  subagents/ files once (by file and requestId) at scripts/prices.json rates. It is an
  estimate, shown next to actual_usd with the difference, never summed with it.
- A value the run didn't record is null and named in `unknown`; no price is assumed for it.
- A run with no usable result event (timeout, crash, empty or malformed output) gets a
  `failure` record: status `no-result`, actual_usd null, the exit code and the end of the
  error log. It is never counted as completed or as zero cost.

usage:
  runrecord.py record --result <claude -p output: .json or stream .jsonl> --run-id <id>
                      --arm <plain|v0.9|v1.0> --version <label> [--case <id>]
                      [--started <ISO>] [--finished <ISO>] [--wall-s <s>] [--config-dir <dir>]
                      [--exit-code <rc>]
  runrecord.py failure  (the same options, plus --error-log <file> [--reason <why>])
  runrecord.py validate <record.json>          exit 1 unless it is a complete record
  runrecord.py summarize <record.json>...      Markdown table per arm
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tokens  # noqa: E402

ROUTE = re.compile(r"ROUTE track=\S+(?: [a-z_]+=\S+)*")
ROLE_KIND = {"implementer": "execution", "reviewer": "review", "planner": "planning"}


def load_result(path):
    """The result event of a `claude -p` run: a JSON object, or the last result line of
    stream-json output."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        d = json.loads(text)
        if isinstance(d, dict) and d.get("type") == "result":
            return d  # a stream holding only its init event is not a result
    except ValueError:
        pass
    res = None
    for line in text.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("type") == "result":
            res = d
    if res is None:
        raise ValueError("no result event in %s" % path)
    return res


def config_dir(arg):
    return arg or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def find_main(cfg, sid):
    hits = glob.glob(os.path.join(cfg, "projects", "*", sid + ".jsonl"))
    return hits[0] if hits else None


def route_from_text(path):
    """ROUTE lines the main thread printed (a v0.9 run shows its route in its reply)."""
    found = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or d.get("type") != "assistant":
                continue
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "text":
                    found += ROUTE.findall(c.get("text") or "")
    return found


def events(cfg, sid):
    path = os.path.join(cfg, "sharaqi-state", sid + ".events.jsonl")
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    out.append(d)
    except OSError:
        return None
    return out


def transcript_view(main_file):
    """Requests (deduplicated), models per role, Agent calls and parallel groups."""
    since = tokens.parse_ts("2000-01-01T00:00:00Z")
    requests, threads = {}, []
    acts = {}
    tokens.read_file(main_file, "main", since, requests, acts)
    threads.append(("main", acts))
    sub_dir = os.path.join(main_file[:-len(".jsonl")], "subagents")
    subagents = []
    for f in sorted(glob.glob(os.path.join(sub_dir, "*.jsonl"))):
        role = "subagent"
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as mh:
                role = json.load(mh).get("agentType") or role
        except (OSError, ValueError):
            pass
        a = {}
        tokens.read_file(f, role, since, requests, a)
        threads.append((role, a))
        subagents.append(role)
    return requests, threads, subagents


def estimate(requests):
    """(usd, unpriced request count) at prices.json rates."""
    _, _, table = tokens.load_prices()
    usd, unpriced = 0.0, 0
    for _, model, t in requests.values():
        key = tokens.model_key(model, table)
        if key is None:
            unpriced += 1
            continue
        usd += tokens.cost(table[key], t)
    return usd, unpriced


def record(a):
    res = load_result(a.result)
    cfg = config_dir(a.config_dir)
    unknown = []
    sid = res.get("session_id")
    rec = {
        "run_id": a.run_id, "arm": a.arm, "version": a.version, "case_id": a.case,
        "session_id": sid, "started_at": a.started, "finished_at": a.finished,
        "wall_s": a.wall_s, "cli_duration_ms": res.get("duration_ms"),
        "api_duration_ms": res.get("duration_api_ms"), "num_turns": res.get("num_turns"),
        "is_error": res.get("is_error"), "subtype": res.get("subtype"),
        "terminal_reason": res.get("terminal_reason"),
        "permission_denials": len(res.get("permission_denials") or []),
    }
    for k in ("started_at", "finished_at", "wall_s"):
        if rec[k] is None:
            unknown.append(k)

    mu = res.get("modelUsage") if isinstance(res.get("modelUsage"), dict) else None
    per_model = {}
    for m, u in (mu or {}).items():
        per_model[m] = {
            "input": u.get("inputTokens"), "output": u.get("outputTokens"),
            "cache_read": u.get("cacheReadInputTokens"),
            "cache_write": u.get("cacheCreationInputTokens"),
            "cache_write_5m": u.get("cacheCreationEphemeral5mInputTokens"),
            "cache_write_1h": u.get("cacheCreationEphemeral1hInputTokens"),
            "cost_usd": u.get("costUSD"), "cost_basis": u.get("costBasis"),
        }
    if mu is None:
        unknown.append("tokens_by_model")
    actual = res.get("total_cost_usd")
    cost = {"actual_usd": actual, "actual_source": "claude -p total_cost_usd (includes subagents)",
            "by_model": per_model, "transcript_estimate_usd": None,
            "estimate_label": "prices.json list rates; an estimate, not added to actual_usd",
            "reconciliation_delta_usd": None, "unpriced_requests": None}
    if actual is None:
        unknown.append("actual_usd")
    rec["cost"] = cost

    main_file = find_main(cfg, sid) if sid else None
    ev = events(cfg, sid) if sid else None
    if main_file is None:
        unknown += ["transcript", "models", "delegation"]
        rec["models"] = rec["delegation"] = None
    else:
        requests, threads, subagents = transcript_view(main_file)
        usd, unpriced = estimate(requests)
        cost["transcript_estimate_usd"] = round(usd, 6)
        cost["unpriced_requests"] = unpriced
        if actual is not None:
            cost["reconciliation_delta_usd"] = round(actual - usd, 6)
        models = {"orchestration": [], "execution": [], "review": [], "planning": [],
                  "other_subagent": []}
        for (path, _), (role, model, _) in requests.items():
            kind = "orchestration" if role == "main" else \
                ROLE_KIND.get(role.split(":")[-1], "other_subagent")
            if model and model not in models[kind]:
                models[kind].append(model)
        rec["models"] = models
        spawns = threads[0][1].get("spawns") or {}
        groups = [len(v) for v in spawns.values()]
        rec["delegation"] = {
            "agent_calls": sum(groups),
            "parallel_groups": sum(1 for g in groups if g > 1),
            "max_parallel": max(groups) if groups else 0,
            "subagent_threads": len(subagents),
            "subagent_types": sorted(set(subagents)),
        }
        rec["route_printed"] = route_from_text(main_file)

    if ev is None:
        rec["events"] = None
        if a.arm != "plain":
            unknown.append("events")
    else:
        routes = [e for e in ev if e.get("event") == "route"]
        agents = [e for e in ev if e.get("event") == "agent"]
        gates = [e for e in ev if e.get("event") == "gate"]
        rec["events"] = {
            "route": routes[-1] if routes else None,
            "route_errors": sum(1 for e in ev if e.get("event") == "route-error"),
            "agent_calls_logged": len(agents),
            "agent_calls_blocked": sum(1 for e in agents if e.get("decision") == "block"),
            "escalations": [{k: e.get(k) for k in ("subagent_type", "model", "effort",
                                                   "escalate", "decision")}
                            for e in agents if "opus" in (e.get("model") or "")],
            "gate": {d: sum(1 for e in gates if f"{e.get('decision')}:{e.get('class')}" == d)
                     for d in sorted({f"{e.get('decision')}:{e.get('class')}" for e in gates})},
        }
    rec["tests"] = None  # a routing case runs no tests; an end-to-end runner fills this in
    rec["repairs"] = None
    unknown += ["tests", "repairs"]
    rec["exit_code"] = a.exit_code
    if res.get("is_error"):
        status = "error"
    elif res.get("subtype") not in (None, "success"):
        status = res.get("subtype")
    elif a.exit_code not in (None, 0):
        status = "error"  # a success event from a process that failed is not a success
    else:
        status = "completed"
    rec["status"] = status
    rec["unknown"] = unknown
    return rec


TIMEOUT_RC = 142  # 128 + SIGALRM: run.sh's `perl -e 'alarm N; exec ...'` limit


def failure(a):
    """A record for a run that produced no usable result event. Every measured value is null;
    only what the harness itself saw (exit code, wall clock, error log) is kept."""
    size = None
    try:
        size = os.path.getsize(a.result)
    except OSError:
        pass
    if a.reason:
        reason = a.reason
    elif a.exit_code == TIMEOUT_RC:
        reason = "timeout"
    elif not size:
        reason = "empty-output"
    else:
        try:
            load_result(a.result)
            reason = "record-failed"  # the event is there; building the record broke
        except (OSError, ValueError):
            reason = "no-result-event"
    tail = None
    if a.error_log:
        try:
            with open(a.error_log, encoding="utf-8", errors="replace") as fh:
                tail = fh.read()[-2000:]
        except OSError:
            pass
    rec = {
        "run_id": a.run_id, "arm": a.arm, "version": a.version, "case_id": a.case,
        "session_id": None, "started_at": a.started, "finished_at": a.finished,
        "wall_s": a.wall_s, "cli_duration_ms": None, "api_duration_ms": None,
        "num_turns": None, "is_error": True, "subtype": None, "terminal_reason": None,
        "permission_denials": None, "exit_code": a.exit_code,
        "cost": {"actual_usd": None, "actual_source": "none: the run produced no result event",
                 "by_model": {}, "transcript_estimate_usd": None,
                 "estimate_label": "not computed for a failed run",
                 "reconciliation_delta_usd": None, "unpriced_requests": None},
        "models": None, "delegation": None, "events": None, "tests": None, "repairs": None,
        "failure": {"reason": reason, "exit_code": a.exit_code, "result_file": a.result,
                    "result_bytes": size, "error_log_tail": tail},
        "status": "no-result",
        "unknown": ["actual_usd", "tokens_by_model", "cli_duration_ms", "num_turns",
                    "transcript", "models", "delegation", "events", "tests", "repairs"],
    }
    for k in ("started_at", "finished_at", "wall_s"):
        if rec[k] is None:
            rec["unknown"].append(k)
    return rec


REQUIRED = ("run_id", "arm", "case_id", "status", "cost", "unknown")


def check_record(r):
    """Problems that make a record unusable for scoring; [] when it is complete."""
    if not isinstance(r, dict):
        return ["not a JSON object"]
    bad = ["missing %s" % k for k in REQUIRED if k not in r]
    if bad:
        return bad
    if r["arm"] not in ("plain", "v0.9", "v1.0"):
        bad.append("arm %r" % r["arm"])
    if not isinstance(r["status"], str) or not r["status"]:
        bad.append("status %r" % r["status"])
    cost = r["cost"]
    if not isinstance(cost, dict) or "actual_usd" not in cost:
        bad.append("missing cost.actual_usd")
    elif cost["actual_usd"] is not None and (
            isinstance(cost["actual_usd"], bool) or
            not isinstance(cost["actual_usd"], (int, float))):
        bad.append("cost.actual_usd %r" % cost["actual_usd"])
    elif cost["actual_usd"] is None and "actual_usd" not in (r["unknown"] or []):
        bad.append("null cost not listed in unknown")
    return bad


def load_record(path):
    """(record, []) or (None, [problems]); never raises on a bad file."""
    try:
        with open(path, encoding="utf-8") as fh:
            r = json.load(fh)
    except (OSError, ValueError) as e:
        return None, ["unreadable: %s" % e.__class__.__name__]
    bad = check_record(r)
    return (None, bad) if bad else (r, [])


def median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def usd(x):
    return "unknown" if x is None else "%.4f" % x


def summarize(paths):
    recs = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                r = json.load(fh)
            if not isinstance(r, dict) or not r.get("arm") or "actual_usd" not in r["cost"]:
                raise ValueError("no arm or cost.actual_usd")
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("runrecord: skipped %s (%s)" % (p, e.__class__.__name__), file=sys.stderr)
            continue
        recs.append(r)
    arms = {}
    for r in recs:
        arms.setdefault(r["arm"], []).append(r)
    print("| Arm | Runs | Completed | Cost $ (CLI) | Median $ | Wall s total · median | "
          "CLI s total | Turns | Agent calls | Opus escalations | Gate blocks | Unknown cost |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arm, rs in arms.items():
        costs = [r["cost"]["actual_usd"] for r in rs]
        walls = [r.get("wall_s") for r in rs]
        cli = [r.get("cli_duration_ms") for r in rs]
        known = [c for c in costs if c is not None]
        ev = [r.get("events") or {} for r in rs]
        gate_blocks = sum(v for e in ev for k, v in (e.get("gate") or {}).items()
                          if k.startswith("block"))
        print("| %s | %d | %d | %s | %s | %s · %s | %.1f | %d | %d | %d | %d | %d |" % (
            arm, len(rs), sum(1 for r in rs if r["status"] == "completed"),
            usd(sum(known) if known else None), usd(median(known)),
            "%.1f" % sum(w for w in walls if w is not None) if any(w is not None for w in walls)
            else "n/a", "%.1f" % median(walls) if median(walls) is not None else "n/a",
            sum(c for c in cli if c) / 1000, sum(r.get("num_turns") or 0 for r in rs),
            sum((r.get("delegation") or {}).get("agent_calls", 0) for r in rs),
            sum(len(e.get("escalations") or []) for e in ev), gate_blocks,
            len(costs) - len(known)))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(usage=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("record", "failure"):
        r = sub.add_parser(name)
        r.add_argument("--result", required=True)
        r.add_argument("--run-id", required=True)
        r.add_argument("--arm", required=True, choices=("plain", "v0.9", "v1.0"))
        r.add_argument("--version", required=True)
        r.add_argument("--case")
        r.add_argument("--started")
        r.add_argument("--finished")
        r.add_argument("--wall-s", type=float)
        r.add_argument("--config-dir")
        r.add_argument("--exit-code", type=int)
        if name == "failure":
            r.add_argument("--error-log")
            r.add_argument("--reason")
    v = sub.add_parser("validate")
    v.add_argument("path")
    s = sub.add_parser("summarize")
    s.add_argument("records", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "summarize":
        return summarize(a.records)
    if a.cmd == "validate":
        r, bad = load_record(a.path)
        if r is None:
            print("runrecord: %s: %s" % (a.path, "; ".join(bad)), file=sys.stderr)
            return 1
        return 0
    if a.cmd == "failure":
        print(json.dumps(failure(a), indent=2, ensure_ascii=False))
        return 0
    try:
        rec = record(a)
    except (OSError, ValueError) as e:
        print("runrecord: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
