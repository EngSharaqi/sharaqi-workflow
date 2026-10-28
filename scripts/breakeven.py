#!/usr/bin/env python3
"""Delegate-vs-inline break-even for sharaqi, from prices.json and a recorded session.

The model (docs/architecture.md, "Break-even"):

  one work turn (a read, an edit or a check run) costs, on a thread with context C, new
  tokens d and output o:   turn = C*read + d*write + o*out
  delegating a slice adds a fixed cost on the orchestrator and the subagent's start:
      F = b*out_o + 2*turn_o(o=0) + S*write_m
          (b: brief tokens; two orchestrator turns, spawn and result; S: the subagent's first prompt)
  and each delegated work turn saves  s = turn_o - turn_m - o_m*write_o
          (the orchestrator reads the diff, about the implementer's output, when re-verifying)
  break-even:  n* = F / s   work turns; delegate a slice expected to take more than n*.

C, d, o and S are medians measured from the session's own usage lines (main thread for the
orchestrator, the implementer subagent for the cheaper model), and cache writes are priced at
the 5m/1h split each thread actually used. The brief length b is the one assumption; the
table shows n* for half and double of it. Thresholds derived from this are heuristics.

usage: breakeven.py [--config DIR --session ID] [--orchestrator MODEL] [--brief TOKENS]
"""
import argparse
import glob
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURE = (os.path.join(ROOT, "tests", "fixtures", "bench-2026-10-22"),
           "00000000-0000-4000-8000-000000000001")
TARGETS = ("claude-haiku-4-5", "claude-haiku-5-5", "claude-sonnet-5", "claude-sonnet-5-5",
           "claude-opus-5", "claude-opus-5-5")


def requests(path):
    """Final usage per request, in order."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            m = d.get("message") or {}
            if d.get("type") == "assistant" and m.get("usage"):
                out[d.get("requestId") or m.get("id")] = m["usage"]
    return list(out.values())


def profile(usages):
    """Medians of context, new tokens and output per request; the first prompt; 1h-write share."""
    ctx, new, out, w1h, wall = [], [], [], 0, 0
    for u in usages:
        cw = u.get("cache_creation_input_tokens", 0) or 0
        ctx.append((u.get("input_tokens", 0) or 0) + (u.get("cache_read_input_tokens", 0) or 0))
        new.append(cw + (u.get("input_tokens", 0) or 0))
        out.append(u.get("output_tokens", 0) or 0)
        w1h += (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
        wall += cw
    first = usages[0]
    start = sum(first.get(k, 0) or 0 for k in
                ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return {"C": statistics.median(ctx[1:] or ctx), "d": statistics.median(new[1:] or new),
            "o": statistics.median(out), "S": start, "share_1h": (w1h / wall) if wall else 0.0,
            "n": len(usages)}


def write_rate(rates, share_1h):
    return share_1h * rates["cache_write_1h"] + (1 - share_1h) * rates["cache_write_5m"]


def turn(rates, p, with_output=True):
    return (p["C"] * rates["cache_read"] + p["d"] * write_rate(rates, p["share_1h"])
            + (p["o"] * rates["output"] if with_output else 0)) / 1e6


def breakeven(prices, orch, target, po, pm, brief):
    ro, rm = prices[orch], prices[target]
    fixed = (brief * ro["output"] / 1e6 + 2 * turn(ro, po, with_output=False)
             + pm["S"] * write_rate(rm, pm["share_1h"]) / 1e6)
    save = turn(ro, po) - turn(rm, pm) - pm["o"] * write_rate(ro, po["share_1h"]) / 1e6
    return fixed, save, (fixed / save if save > 0 else float("inf"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=FIXTURE[0])
    ap.add_argument("--session", default=FIXTURE[1])
    ap.add_argument("--orchestrator", default="claude-opus-5")
    ap.add_argument("--brief", type=int, default=800)
    a = ap.parse_args()

    with open(os.path.join(HERE, "prices.json"), encoding="utf-8") as fh:
        prices = json.load(fh)["models"]
    hits = glob.glob(os.path.join(a.config, "projects", "*", a.session + ".jsonl"))
    if not hits:
        print("BREAKEVEN: unavailable (session %s not found)" % a.session)
        return 1
    main_f = hits[0]
    impl = None
    for f in sorted(glob.glob(os.path.join(main_f[:-6], "subagents", "*.jsonl"))):
        try:
            with open(f[:-6] + ".meta.json", encoding="utf-8") as mh:
                kind = json.load(mh).get("agentType", "")
        except (OSError, ValueError):
            kind = ""
        if "implementer" in kind:
            impl = f
            break
    if impl is None:
        print("BREAKEVEN: unavailable (no implementer subagent in session %s)" % a.session)
        return 1
    if a.orchestrator not in prices:
        print("BREAKEVEN: unavailable (no price row for %s)" % a.orchestrator)
        return 1
    po, pm = profile(requests(main_f)), profile(requests(impl))

    print("Measured (medians per request): orchestrator context %d, new %d, output %d, "
          "1h-write share %.0f%% (%d requests) · implementer first prompt %d, context %d, "
          "new %d, output %d (%d requests)" % (
              po["C"], po["d"], po["o"], 100 * po["share_1h"], po["n"],
              pm["S"], pm["C"], pm["d"], pm["o"], pm["n"]))
    print("Orchestrator: %s · brief %d tokens (assumption)" % (a.orchestrator, a.brief))
    print()
    print("| Target | Fixed cost $ | Saved per work turn $ | Break-even n* (work turns) | n* at brief /2 · x2 |")
    print("|---|---|---|---|---|")
    for t in TARGETS:
        if t not in prices:
            continue
        f, s, n = breakeven(prices, a.orchestrator, t, po, pm, a.brief)
        lo = breakeven(prices, a.orchestrator, t, po, pm, a.brief // 2)[2]
        hi = breakeven(prices, a.orchestrator, t, po, pm, a.brief * 2)[2]
        fmt = lambda x: "never" if x == float("inf") else "%.1f" % x
        print("| %s | %.3f | %.4f | %s | %s · %s |" % (t, f, s, fmt(n), fmt(lo), fmt(hi)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
