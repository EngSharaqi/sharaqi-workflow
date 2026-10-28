#!/usr/bin/env python3
"""Token usage for one sharaqi task, read from the local session transcript.

Reads the usage Claude Code records for the main thread and its subagents since
--since, and prices each request at API list rates for its exact model id (scripts/prices.json). The dollar
figure is an API-equivalent estimate, not a bill: subscription plans are not
charged per token. A model whose price row isn't verified against Claude Code's
own cost is marked "estimate (price unverified for <model>)" on each line that
shows it. Nothing is compared with a hypothetical baseline.

usage: tokens.py --session <id> --since <ISO-8601 UTC> [--lang en|ar] [--phases]
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import date, datetime

# USD per million tokens per model id, the date the table was last checked, and the
# model ceiling the hook enforces: all in prices.json next to this script.
PRICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json")
RATE_KEYS = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")
DATE_SUFFIX = re.compile(r"-\d{8}$")
# --context: the prompt-side usage fields, the model's [1m]-style suffix, and session ids as
# hooks/session-hints.sh accepts them (they name a state file).
CONTEXT_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
CONTEXT_SUFFIX = re.compile(r"\[[^\]]*\]$")
CONTEXT_SESSION = re.compile(r"[A-Za-z0-9_-]+")


def load_prices():
    with open(PRICES_FILE, encoding="utf-8") as fh:
        p = json.load(fh)
    return (date.fromisoformat(p["checked"]), int(p.get("stale_after_days", 90)), p["models"])


def model_key(model, table):
    """The table key for a transcript model id, or None. Exact id, or id plus a date
    suffix (claude-haiku-4-5-20251001). No family guessing: claude-opus-5 and
    claude-opus-5-5 are priced differently, and an unknown version stays unpriced."""
    m = (model or "").lower()
    m = DATE_SUFFIX.sub("", m)
    return m if m in table else None


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def split_usage(u):
    """Tokens per category. `ttl` is False when the request wrote cache but recorded no
    5m/1h breakdown; those writes are counted (and priced) as 5m."""
    cc = u.get("cache_creation")
    cc = cc if isinstance(cc, dict) else {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5m = cc.get("ephemeral_5m_input_tokens")
    if w5m is None:
        w5m = (u.get("cache_creation_input_tokens", 0) or 0) - w1h
    return {
        "in": u.get("input_tokens", 0) or 0,
        "w5m": w5m or 0,
        "w1h": w1h,
        "read": u.get("cache_read_input_tokens", 0) or 0,
        "out": u.get("output_tokens", 0) or 0,
        "ttl": not (w5m or w1h) or any(k in cc for k in (
            "ephemeral_1h_input_tokens", "ephemeral_5m_input_tokens")),
    }


def cost_parts(rates, t):
    """USD per category, in RATE_KEYS order (input, write 5m, write 1h, read, output)."""
    long = rates.get("long_context")
    if long and t["in"] + t["w5m"] + t["w1h"] + t["read"] > long["over_prompt_tokens"]:
        rates = long
    return [t[k] * rates[r] / 1_000_000
            for k, r in zip(("in", "w5m", "w1h", "read", "out"), RATE_KEYS)]


def cost(rates, t):
    return sum(cost_parts(rates, t))


def m_tok(n):
    n = int(n)
    if abs(n) >= 1_000_000:
        return "`%.2fM`" % (n / 1_000_000)
    if abs(n) >= 1_000:
        return "`%dK`" % round(n / 1_000)
    return "`%d`" % n


def find_transcript(session):
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    hits = glob.glob(os.path.join(root, "projects", "*", session + ".jsonl"))
    return hits[0] if hits else None


def result_size(content):
    """Characters of text in a tool_result's content (a string or a list of blocks), and
    whether it held an image. Characters, not tokens: the transcript has no per-result count."""
    if isinstance(content, str):
        return len(content), False
    chars, image = 0, False
    for b in content if isinstance(content, list) else []:
        if isinstance(b, dict) and b.get("type") == "text":
            chars += len(b.get("text") or "")
        elif isinstance(b, dict) and b.get("type") == "image":
            image = True
    return chars, image


def tool_label(name, i, cwd):
    """A short name for a tool call that never prints command arguments (they can hold
    secrets): the program name for Bash, the path for file tools, the agent type for Agent."""
    if name == "Bash":
        # Skip VAR=value prefixes: the value can be a token.
        words = [w for w in str(i.get("command") or "").split() if "=" not in w]
        return "Bash %s" % (os.path.basename(words[0].strip("'\"")) if words else "?")
    if i.get("file_path"):
        return "%s %s" % (name, short_path(i["file_path"], cwd))
    if name in ("Agent", "Task"):
        return "%s %s" % (name, i.get("subagent_type") or "?")
    return name


def read_file(path, role, since, requests, acts=None):
    """Usage per request into `requests`. With `acts` (a dict), also what the thread did:
    its Read calls, the files it edited, its Agent calls grouped by assistant message, the
    effort its requests recorded, and its working directory; and for --phases: its requests
    in order, its compaction boundaries, the size of each tool result, and the prompts it
    sent to subagents."""
    if acts is not None:
        acts.update(reads=[], writes=set(), spawns={}, efforts=[], cwd=None, first=None,
                    order=[], compacts=[], results=[], prompts=[], tools={})
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            kind = d.get("type")
            if kind != "assistant" and (acts is None or kind not in ("user", "system")):
                continue
            ts = d.get("timestamp")
            if not ts:
                continue
            try:
                when = parse_ts(ts)
            except (TypeError, ValueError):
                if kind == "assistant":
                    raise
                continue  # a bad timestamp on a non-usage line never fails the report
            if when < since:
                continue
            if acts is not None and d.get("type") == "system" \
                    and d.get("subtype") == "compact_boundary":
                acts["compacts"].append(ts)
                continue
            if acts is not None and d.get("type") == "user":
                content = (d.get("message") or {}).get("content")
                for c in content if isinstance(content, list) else []:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        chars, image = result_size(c.get("content"))
                        acts["results"].append(
                            (acts["tools"].get(c.get("tool_use_id"), "?"), chars, image))
                continue
            if d.get("type") != "assistant":
                continue
            msg = d.get("message") or {}
            if acts is not None:
                acts["cwd"] = acts["cwd"] or d.get("cwd")
                acts["first"] = acts["first"] or ts
                eff = d.get("effort")
                if isinstance(eff, dict):
                    eff = eff.get("level")
                if msg.get("usage") and eff:
                    acts["efforts"].append(str(eff))
                for c in msg.get("content") or []:
                    if not isinstance(c, dict) or c.get("type") != "tool_use":
                        continue
                    i = c.get("input") or {}
                    if not isinstance(i, dict):
                        i = {}
                    acts["tools"][c.get("id")] = tool_label(c.get("name"), i, acts["cwd"])
                    if c.get("name") in ("Agent", "Task"):
                        sent, to = i.get("prompt"), i.get("subagent_type") or "?"
                    elif c.get("name") == "SendMessage":
                        sent, to = i.get("message"), "SendMessage"
                    else:
                        sent = None
                    if isinstance(sent, str):
                        acts["prompts"].append((to, len(sent)))
                    if c.get("name") == "Read" and i.get("file_path"):
                        acts["reads"].append((i["file_path"], i.get("offset"), i.get("limit")))
                    elif c.get("name") in ("Edit", "Write", "MultiEdit") and i.get("file_path"):
                        acts["writes"].add(i["file_path"])
                    elif c.get("name") in ("Agent", "Task"):
                        acts["spawns"].setdefault(msg.get("id") or d.get("uuid"), []).append(
                            i.get("subagent_type") or "?")
            usage = msg.get("usage")
            if not usage:
                continue
            # One API response is written as several lines; output_tokens grows
            # across them, so the last line carries the complete usage.
            key = (path, d.get("requestId") or msg.get("id") or d.get("uuid"))
            if acts is not None and key not in requests:
                acts["order"].append((key, ts))
            requests[key] = (role, msg.get("model"), split_usage(usage))


def phase_kind(role):
    for kind in ("implementer", "reviewer", "planner"):
        if kind in role:
            return kind
    return "orchestrator" if role == "main" else "subagent"


def short_path(p, cwd):
    if cwd and p.startswith(cwd.rstrip("/") + "/"):
        return p[len(cwd.rstrip("/")) + 1:]
    return os.path.basename(p)


def print_phases(threads, requests, table):
    """Cost per phase (orchestrator, each implementer, each reviewer ...), parallel spawns,
    and double reads, for benchmarks and audits. Paths are printed relative to the session's
    working directory, or as a bare file name."""
    print()
    print("PHASES:")
    print("| Phase | Agent | Model | Effort recorded | Requests | Output | List-price $ |")
    print("|---|---|---|---|---|---|---|")
    counts, total = {}, 0.0
    rows = []
    for path, role, acts in threads:
        reqs = [(m, t) for (p, _), (_, m, t) in requests.items() if p == path]
        if not reqs:
            continue
        kind = phase_kind(role)
        counts[kind] = counts.get(kind, 0) + 1
        label = kind if kind == "orchestrator" else "%s #%d" % (kind, counts[kind])
        models = sorted({model_key(m, table) or (m or "?") for m, _ in reqs})
        usd = sum(cost(table[model_key(m, table)], t) for m, t in reqs if model_key(m, table))
        effs = sorted(set(acts["efforts"])) or ["none"]
        out = sum(t["out"] for _, t in reqs)
        total += usd
        rows.append((label, role, ", ".join(models), "/".join(effs), len(reqs), out, usd))
    for label, role, models, effs, n, out, usd in rows:
        print("| %s | %s | %s | %s | %d | %s | %.4f |" % (label, role, models, effs, n, f"{out:,}", usd))
    orch = next((r for r in rows if r[0] == "orchestrator"), None)
    if orch:
        print("ORCHESTRATOR: %d requests · output %s · %.0f%% of list price"
              % (orch[4], f"{orch[5]:,}", 100 * orch[6] / total if total else 0))
    main_acts = threads[0][2]
    spawns = [v for v in main_acts["spawns"].values()]
    n_spawn = sum(len(v) for v in spawns)
    widest = max((len(v) for v in spawns), default=0)
    print("SPAWNS: %d agent calls · %d in parallel (largest batch in one message: %d)"
          % (n_spawn, sum(len(v) for v in spawns if len(v) > 1), widest))
    cwd = main_acts["cwd"]
    main_files = {p for p, _, _ in main_acts["reads"]}
    handoff = sorted({short_path(p, cwd) for _, _, acts in threads[1:]
                      for p, _, _ in acts["reads"] if p in main_files})
    rereads = []
    for _, role, acts in threads:
        seen = {}
        for r in acts["reads"]:
            seen[r] = seen.get(r, 0) + 1
        rereads += ["%s (%s ×%d)" % (short_path(r[0], cwd), phase_kind(role), n)
                    for r, n in sorted(seen.items(), key=lambda kv: str(kv[0])) if n > 1]
    print("DOUBLE_READS: handoff %d%s · re-read in one thread %d%s" % (
        len(handoff), (" (" + ", ".join(handoff) + ")") if handoff else "",
        len(rereads), (" (" + ", ".join(rereads) + ")") if rereads else ""))
    # Slices must write disjoint files (references/routes/delegate.md); the orchestrator
    # fixing a file after an implementer is a delta, not a conflict, so only subagent
    # threads count.
    writers = {}
    for _, _, acts in threads[1:]:
        for p in acts["writes"]:
            writers[p] = writers.get(p, 0) + 1
    clash = sorted(short_path(p, cwd) for p, n in writers.items() if n > 1)
    print("WRITE_CONFLICTS: %d%s" % (len(clash), (" (" + ", ".join(clash) + ")") if clash else ""))
    print_composition(threads, requests, table)


# Measured vs computed, for the lines below: token counts are what each request recorded;
# dollars are computed from them at list rates; tool results and prompts are characters
# (the transcript has no per-result token count); nothing is estimated or filled in.
SPLIT = (("in", "input"), ("w5m", "write 5m"), ("w1h", "write 1h"), ("w?", "write TTL?"),
         ("read", "read"), ("out", "output"))


def print_composition(threads, requests, table):
    """Cost by token category per phase, cache TTL, tool results and subagent prompts of the
    orchestrator, and cache rebuilds in the orchestrator's thread."""
    # Indented lines, not a "| " table: benchmarks/v0.8/summarize.py takes every "| " row
    # after PHASES: as a phase row.
    print()
    print("COST_SPLIT (tokens as recorded · share of the phase's list-price $):")
    counts = {}
    ttl = {"w5m": 0, "w1h": 0, "w?": 0, "n?": 0}
    for path, role, acts in threads:
        reqs = [(m, t) for (p, _), (_, m, t) in requests.items() if p == path]
        if not reqs:
            continue
        kind = phase_kind(role)
        counts[kind] = counts.get(kind, 0) + 1
        label = kind if kind == "orchestrator" else "%s #%d" % (kind, counts[kind])
        tok = dict.fromkeys((k for k, _ in SPLIT), 0)
        usd = dict.fromkeys(tok, 0.0)
        priced = True
        for m, t in reqs:
            w = "w5m" if t["ttl"] else "w?"
            if not t["ttl"]:
                ttl["n?"] += 1
            for k, src in (("in", "in"), (w, "w5m"), ("w1h", "w1h"), ("read", "read"),
                           ("out", "out")):
                tok[k] += t[src]
            fam = model_key(m, table)
            if fam is None:
                priced = False
                continue
            for k, v in zip(("in", w, "w1h", "read", "out"), cost_parts(table[fam], t)):
                usd[k] += v
        for k in ("w5m", "w1h", "w?"):
            ttl[k] += tok[k]
        total = sum(usd.values())
        cells = ["%s %s (%s)" % (name, f"{tok[k]:,}", "%.0f%%" % (100 * usd[k] / total)
                                 if priced and total else "$ n/a: model unpriced")
                 for k, name in SPLIT]
        print("  %s: %s" % (label, " · ".join(cells)))
    print("CACHE_TTL: tokens written 1h %s · 5m %s · TTL not recorded %s (%d requests, priced as 5m)"
          % (f"{ttl['w1h']:,}", f"{ttl['w5m']:,}", f"{ttl['w?']:,}", ttl["n?"]))

    main = threads[0][2]
    res = main["results"]
    by = {}
    for label, chars, _ in res:
        tool = label.split(" ")[0]
        n, c = by.get(tool, (0, 0))
        by[tool] = (n + 1, c + chars)
    images = sum(1 for _, _, image in res if image)
    sub_res = [r for _, _, acts in threads[1:] for r in acts["results"]]
    if not res:
        # No tool_result entries is "not in the transcript", never "zero output".
        print("TOOL_OUTPUTS (orchestrator, characters not tokens): not recorded (%d tool calls, "
              "no tool results in the transcript)" % len(main["tools"]))
    else:
        print("TOOL_OUTPUTS (orchestrator, characters not tokens): %d results · %s chars · %s%s"
              % (len(res), f"{sum(c for _, c, _ in res):,}",
                 " · ".join("%s %d/%s" % (k, n, f"{c:,}") for k, (n, c)
                            in sorted(by.items(), key=lambda kv: -kv[1][1])),
                 " · %d with an image (not counted)" % images if images else ""))
        print("  largest: " + " · ".join("%s %s" % (l, f"{c:,}") for l, c, _ in
                                        sorted(res, key=lambda r: -r[1])[:3]))
    if len(threads) > 1:
        print("  subagents: " + ("%d results · %s chars" % (
            len(sub_res), f"{sum(c for _, c, _ in sub_res):,}") if sub_res else "not recorded"))
    sent = main["prompts"]
    n_spawn = sum(len(v) for v in main["spawns"].values())
    if sent:
        shown = " · ".join("%s %s" % (to, f"{n:,}") for to, n in sent)
        shown += " | total %s" % f"{sum(n for _, n in sent):,}"
    elif n_spawn or len(threads) > 1:
        shown = "not recorded (no prompt text in the transcript)"
    else:
        shown = "none sent"
    print("AGENT_PROMPTS (written by the orchestrator, part of its output; characters): " + shown)

    # A rebuild: a request whose cache read covers less than half of the previous request's
    # prompt (input + cache write + cache read), so most of the previous prefix was written
    # again. The cause shown is what the transcript records between the two requests.
    seq = [(ts, requests[k][1], requests[k][2]) for k, ts in main["order"] if k in requests]
    rebuilds = []
    for (pts, pmodel, pt), (ts, model, t) in zip(seq, seq[1:]):
        prev = pt["in"] + pt["w5m"] + pt["w1h"] + pt["read"]
        if prev == 0 or t["read"] * 2 >= prev:
            continue
        gap = int((parse_ts(ts) - parse_ts(pts)).total_seconds())
        if any(parse_ts(pts) < parse_ts(c) <= parse_ts(ts) for c in main["compacts"]):
            why = "after compaction"
        elif model != pmodel:
            why = "model changed (%s → %s)" % (pmodel, model)
        else:
            why = "no compaction or model change recorded"
        rebuilds.append("%s +%ds, %s, rewrote %s" % (ts, gap, why, f"{t['w5m'] + t['w1h']:,}"))
    print("CACHE_REBUILDS (orchestrator; read < half of the previous prompt): %d of %d requests"
          " after the first · compactions recorded %d"
          % (len(rebuilds), max(len(seq) - 1, 0), len(main["compacts"])))
    for r in rebuilds[:5]:
        print("  " + r)
    if len(rebuilds) > 5:
        print("  (%d more)" % (len(rebuilds) - 5))


def load_context():
    """(max_pct, warn_pct, fallback_window) from the `context` block of prices.json."""
    with open(PRICES_FILE, encoding="utf-8") as fh:
        c = json.load(fh)["context"]
    vals = tuple(c[k] for k in ("max_pct", "warn_pct", "fallback_window"))
    if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in vals):
        raise ValueError("context thresholds must be positive integers")
    return vals


def state_dir():
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(root, "sharaqi-state")


def bare_model(model):
    """A model id without a trailing [...] suffix: claude-opus-5-5[1m] -> claude-opus-5-5."""
    return CONTEXT_SUFFIX.sub("", model)


def last_usage(path):
    """(tokens, model) of the last main-thread assistant entry that has usage, or None.
    Tokens are the prompt side of that request: input + cache write + cache read. A field that
    is present but not a non-negative integer raises ValueError, so the caller fails closed."""
    found = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or d.get("type") != "assistant" or d.get("isSidechain"):
                continue
            msg = d.get("message")
            u = msg.get("usage") if isinstance(msg, dict) else None
            if not isinstance(u, dict):
                continue
            tokens = 0
            for k in CONTEXT_KEYS:
                v = u.get(k) or 0
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    raise ValueError("usage field %s is not a count" % k)
                tokens += v
            found = (tokens, msg.get("model"))
    return found


def fmt_pct(tokens, window):
    """Percent to one decimal, rounded down so a shown value never crosses a threshold."""
    tenths = tokens * 1000 // window
    return "%d.%d" % (tenths // 10, tenths % 10)


def context_unverified(tokens, fallback, reason):
    print("CONTEXT UNVERIFIED · %d tokens · ~%s%% if the window were %d (estimate) · %s"
          % (tokens, fmt_pct(tokens, fallback), fallback, reason))
    return 5


def context_mode(session, transcript):
    """`CONTEXT ...` line for one session and exit code: 0 OK, 3 WARN, 4 STOP, 5 unverified.
    The window is taken only from the statusline bridge file written for this session, never
    from the model name, and its model must match the transcript's."""
    try:
        max_pct, warn_pct, fallback = load_context()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("CONTEXT UNVERIFIED · - tokens · - · price table %s has no usable context block (%s)"
              % (PRICES_FILE, e))
        return 5
    if session is not None and not CONTEXT_SESSION.fullmatch(session):
        return context_unverified(0, fallback, "session id has characters outside A-Za-z0-9_-")
    if transcript is None and session is not None:
        transcript = find_transcript(session)
    if transcript is None:
        return context_unverified(0, fallback, "no transcript found for session %s" % session)
    if not os.path.isfile(transcript):
        return context_unverified(0, fallback, "transcript not found")
    if session is None:
        session = os.path.splitext(os.path.basename(transcript))[0]
        if not CONTEXT_SESSION.fullmatch(session):
            return context_unverified(0, fallback, "session id has characters outside A-Za-z0-9_-")
    try:
        found = last_usage(transcript)
    except (OSError, ValueError) as e:
        return context_unverified(0, fallback, "transcript unreadable (%s)" % e.__class__.__name__)
    if found is None:
        return context_unverified(0, fallback, "no usage entry in transcript")
    tokens, model = found
    if not isinstance(model, str) or not model:
        return context_unverified(tokens, fallback, "transcript entry has no model")

    bridge = os.path.join(state_dir(), session + ".ctx")
    try:
        with open(bridge, encoding="utf-8") as fh:
            b = json.load(fh)
    except FileNotFoundError:
        declared = benchmark_window()
        if isinstance(declared, int):
            return context_status(tokens, declared, max_pct, warn_pct,
                                  "window declared (benchmark mode, SHARAQI_CONTEXT_WINDOW, %s)"
                                  % model)
        return context_unverified(tokens, fallback, declared or
                                  "no statusline bridge file for this session (references/setup.md)")
    except (OSError, ValueError):
        return context_unverified(tokens, fallback, "bridge file unreadable or not JSON")
    window = b.get("window") if isinstance(b, dict) else None
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        return context_unverified(tokens, fallback, "bridge file has no positive window size")
    bmodel = b.get("model")
    if not isinstance(bmodel, str) or bare_model(bmodel) != bare_model(model):
        return context_unverified(tokens, fallback,
                                  "model mismatch (transcript %s, bridge %s)" % (model, bmodel))
    return context_status(tokens, window, max_pct, warn_pct,
                          "window verified (statusline, %s)" % model)


def benchmark_window():
    """The window a headless benchmark declares, or a reason string (None: not asked for).
    Benchmark mode is SHARAQI_BENCHMARK=1 plus SHARAQI_CONTEXT_WINDOW=<tokens>: `claude -p`
    has no statusline, so the window can't be verified there. The thresholds stay the same;
    the line says the window was declared, never that it was verified."""
    raw = os.environ.get("SHARAQI_CONTEXT_WINDOW")
    if os.environ.get("SHARAQI_BENCHMARK") != "1":
        return ("no statusline bridge file for this session (references/setup.md); "
                "SHARAQI_CONTEXT_WINDOW applies only with SHARAQI_BENCHMARK=1") if raw else None
    if raw is None:
        return "benchmark mode needs SHARAQI_CONTEXT_WINDOW (the window in tokens)"
    if not re.fullmatch(r"[1-9][0-9]{3,8}", raw.strip()):
        return "SHARAQI_CONTEXT_WINDOW is not a token count (1000 or more)"
    return int(raw)


def context_status(tokens, window, max_pct, warn_pct, source):
    if tokens * 100 >= max_pct * window:
        status, code = "STOP", 4
    elif tokens * 100 >= warn_pct * window:
        status, code = "WARN", 3
    else:
        status, code = "OK", 0
    print("CONTEXT %s%% · %d/%d tokens · %s · %s"
          % (fmt_pct(tokens, window), tokens, window, source, status))
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session")
    ap.add_argument("--since")
    ap.add_argument("--lang", choices=("en", "ar"), default="en")
    ap.add_argument("--phases", action="store_true",
                    help="also print cost per phase, parallel spawns and double reads")
    ap.add_argument("--context", action="store_true",
                    help="print the main session's context fill and exit 0 OK, 3 WARN, 4 STOP, "
                         "5 unverified (needs the statusline bridge file)")
    ap.add_argument("--transcript", help="with --context: the session transcript (.jsonl)")
    a = ap.parse_args()

    if a.context:
        if a.session is None and a.transcript is None:
            ap.error("--context needs --session or --transcript")
        return context_mode(a.session, a.transcript)
    if a.transcript is not None:
        ap.error("--transcript is only used with --context")
    if a.session is None or a.since is None:
        missing = [f for f, v in (("--session", a.session), ("--since", a.since)) if v is None]
        ap.error("the following arguments are required: %s" % ", ".join(missing))

    since = parse_ts(a.since)
    try:
        checked, stale_days, table = load_prices()
    except (OSError, ValueError, KeyError) as e:
        print("TOKENS: unavailable (price table %s unreadable: %s)" % (PRICES_FILE, e))
        return 1
    main_file = find_transcript(a.session)
    if not main_file:
        print("TOKENS: unavailable (transcript for session %s not found)" % a.session)
        return 1

    requests = {}
    threads = [(main_file, "main", {})]
    read_file(main_file, "main", since, requests, threads[0][2])
    sub_dir = os.path.join(main_file[:-len(".jsonl")], "subagents")
    for f in sorted(glob.glob(os.path.join(sub_dir, "*.jsonl"))):
        role = "subagent"
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as mh:
                role = json.load(mh).get("agentType") or role
        except (OSError, ValueError):
            pass
        threads.append((f, role, {}))
        read_file(f, role, since, requests, threads[-1][2])

    if not requests:
        print("TOKENS: unavailable (no usage recorded since %s)" % a.since)
        return 1

    groups, unknown = {}, 0
    for role, model, t in requests.values():
        fam = model_key(model, table)
        if fam is None:
            unknown += 1
            continue
        g = groups.setdefault((role, fam), {"calls": 0, "in": 0, "write": 0,
                                            "read": 0, "out": 0, "cost": 0.0})
        g["calls"] += 1
        g["in"] += t["in"]
        g["write"] += t["w5m"] + t["w1h"]
        g["read"] += t["read"]
        g["out"] += t["out"]
        g["cost"] += cost(table[fam], t)

    def flag(fam):
        if table[fam].get("verified") is True:
            return ""
        return " estimate (price unverified for %s)" % fam

    print("| Role | Model | Calls | Input | Cache write | Cache read | Output | List-price $ |")
    print("|---|---|---|---|---|---|---|---|")
    for (role, fam), g in sorted(groups.items(), key=lambda kv: -kv[1]["cost"]):
        print("| %s | %s | %d | %s | %s | %s | %s | %.4f%s |" % (
            role, fam, g["calls"], f"{g['in']:,}", f"{g['write']:,}",
            f"{g['read']:,}", f"{g['out']:,}", g["cost"], flag(fam)))
    total = sum(g["in"] + g["write"] + g["read"] + g["out"] for g in groups.values())
    out = sum(g["out"] for g in groups.values())
    usd = sum(g["cost"] for g in groups.values())
    calls = sum(g["calls"] for g in groups.values())
    sub = sum(g["calls"] for (role, _), g in groups.items() if role != "main")
    print()
    print("TOTAL_TOKENS: %s (output %s)" % (f"{total:,}", f"{out:,}"))
    print("REQUESTS: %d (subagent %d)" % (calls, sub))
    unverified = sorted({fam for (_, fam) in groups if flag(fam)})
    print("LIST_PRICE_USD: %.4f (API list rates; not a bill)%s"
          % (usd, "".join(" ·" + flag(f) for f in unverified)))
    if unknown:
        print("UNPRICED_REQUESTS: %d (model not recognised; not in the totals)" % unknown)
    age = (date.today() - checked).days
    stale = age > stale_days
    print("PRICES_CHECKED: %s (%d days ago%s)"
          % (checked.isoformat(), age, "; STALE" if stale else ""))
    print()
    print("SUMMARY:")
    if a.lang == "ar":
        line = ("التوكنز: %s (منها output %s) · %d طلب (%d من subagents) · بسعر الـ API `$%.2f` تقريبًا (مش فاتورة)"
                % (m_tok(total), m_tok(out), calls, sub, usd))
        if unknown:
            line += " · %d طلب بنموذج مش معروف مش محسوب" % unknown
        if stale:
            line += " · ⚠️ جدول الأسعار آخر مراجعة له %s، ممكن يكون قديم" % checked.isoformat()
        line += "".join(" ·" + flag(f) for f in unverified)
    else:
        line = ("Tokens: %s (output %s) · %d requests (%d subagent) · about `$%.2f` at API list rates (not a bill)"
                % (m_tok(total), m_tok(out), calls, sub, usd))
        if unknown:
            line += " · %d requests from an unrecognised model not counted" % unknown
        if stale:
            line += " · ⚠️ price table last checked %s, may be out of date" % checked.isoformat()
        line += "".join(" ·" + flag(f) for f in unverified)
    print(line)

    by_model = {}
    for (_, fam), g in groups.items():
        m = by_model.setdefault(fam, {"calls": 0, "tok": 0, "cost": 0.0})
        m["calls"] += g["calls"]
        m["tok"] += g["in"] + g["write"] + g["read"] + g["out"]
        m["cost"] += g["cost"]
    parts = ["%s %s · %d · `$%.2f`%s" % (fam, m_tok(m["tok"]), m["calls"], m["cost"], flag(fam))
             for fam, m in sorted(by_model.items(), key=lambda kv: -kv[1]["cost"])]
    label = "حسب الموديل (توكنز · طلبات · $)" if a.lang == "ar" else "By model (tokens · requests · $)"
    print("%s: %s" % (label, " | ".join(parts)))
    if a.phases:
        threads[1:] = sorted(threads[1:], key=lambda t: t[2].get("first") or "")
        print_phases(threads, requests, table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
