#!/usr/bin/env python3
"""Token usage for one sharaqi task, read from the local session transcript.

Reads the usage Claude Code records for the main thread and its subagents since
--since, and prices each request at API list rates for its model. The dollar
figure is an API-equivalent estimate, not a bill: subscription plans are not
charged per token. Nothing is compared with a hypothetical baseline.

usage: tokens.py --session <id> --since <ISO-8601 UTC> [--lang en|ar]
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime

# USD per million tokens: input, cache write 5m, cache write 1h, cache read, output.
# Source: platform.claude.com/docs/en/about-claude/pricing, checked 2026-10-22.
PRICES = {
    "opus": (4.00, 5.00, 8.00, 0.20, 20.00),
    "sonnet": (2.00, 2.50, 4.00, 0.10, 10.00),
    "haiku": (0.10, 0.125, 0.20, 0.01, 0.50),       # prompt <= 100k tokens
    "haiku-long": (0.50, 0.625, 1.00, 0.05, 2.50),  # prompt > 100k tokens
    "fable": (10.00, 12.50, 20.00, 0.25, 50.00),
}


def family(model):
    m = (model or "").lower()
    for name in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if name in m:
            return "fable" if name == "mythos" else name
    return None


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def split_usage(u):
    cc = u.get("cache_creation") or {}
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
    }


def cost(fam, t):
    if fam == "haiku" and t["in"] + t["w5m"] + t["w1h"] + t["read"] > 100_000:
        fam = "haiku-long"
    p = PRICES[fam]
    return (t["in"] * p[0] + t["w5m"] * p[1] + t["w1h"] * p[2]
            + t["read"] * p[3] + t["out"] * p[4]) / 1_000_000


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


def read_file(path, role, since, requests):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            msg = d.get("message") or {}
            usage = msg.get("usage")
            ts = d.get("timestamp")
            if not usage or not ts or parse_ts(ts) < since:
                continue
            # One API response is written as several lines; output_tokens grows
            # across them, so the last line carries the complete usage.
            key = (path, d.get("requestId") or msg.get("id") or d.get("uuid"))
            requests[key] = (role, msg.get("model"), split_usage(usage))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--lang", choices=("en", "ar"), default="en")
    a = ap.parse_args()

    since = parse_ts(a.since)
    main_file = find_transcript(a.session)
    if not main_file:
        print("TOKENS: unavailable (transcript for session %s not found)" % a.session)
        return 1

    requests = {}
    read_file(main_file, "main", since, requests)
    sub_dir = os.path.join(main_file[:-len(".jsonl")], "subagents")
    for f in sorted(glob.glob(os.path.join(sub_dir, "*.jsonl"))):
        role = "subagent"
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as mh:
                role = json.load(mh).get("agentType") or role
        except (OSError, ValueError):
            pass
        read_file(f, role, since, requests)

    if not requests:
        print("TOKENS: unavailable (no usage recorded since %s)" % a.since)
        return 1

    groups, unknown = {}, 0
    for role, model, t in requests.values():
        fam = family(model)
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
        g["cost"] += cost(fam, t)

    print("| Role | Model | Calls | Input | Cache write | Cache read | Output | List-price $ |")
    print("|---|---|---|---|---|---|---|---|")
    for (role, fam), g in sorted(groups.items(), key=lambda kv: -kv[1]["cost"]):
        print("| %s | %s | %d | %s | %s | %s | %s | %.4f |" % (
            role, fam, g["calls"], f"{g['in']:,}", f"{g['write']:,}",
            f"{g['read']:,}", f"{g['out']:,}", g["cost"]))
    total = sum(g["in"] + g["write"] + g["read"] + g["out"] for g in groups.values())
    out = sum(g["out"] for g in groups.values())
    usd = sum(g["cost"] for g in groups.values())
    calls = sum(g["calls"] for g in groups.values())
    sub = sum(g["calls"] for (role, _), g in groups.items() if role != "main")
    print()
    print("TOTAL_TOKENS: %s (output %s)" % (f"{total:,}", f"{out:,}"))
    print("REQUESTS: %d (subagent %d)" % (calls, sub))
    print("LIST_PRICE_USD: %.4f (API list rates; not a bill)" % usd)
    if unknown:
        print("UNPRICED_REQUESTS: %d (model not recognised)" % unknown)
    print()
    print("SUMMARY:")
    if a.lang == "ar":
        print("التوكنز: %s (منها output %s) · %d طلب (%d من subagents) · بسعر الـ API `$%.2f` تقريبًا (مش فاتورة)"
              % (m_tok(total), m_tok(out), calls, sub, usd))
    else:
        print("Tokens: %s (output %s) · %d requests (%d subagent) · about `$%.2f` at API list rates (not a bill)"
              % (m_tok(total), m_tok(out), calls, sub, usd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
