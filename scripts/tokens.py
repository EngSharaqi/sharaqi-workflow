#!/usr/bin/env python3
"""Token and cost report for one sharaqi run.

Reads the real usage Claude Code records in the session transcript (main thread +
subagents), prices every request at its actual model, and compares it with the
same work done entirely on Opus 5.5 at medium effort:

- model saving  = the same tokens re-priced at Opus rates, minus the actual cost
                  (measured: only the price per token changes);
- effort saving = output tokens rescaled from the effort each request really ran
                  at to medium, at Opus rates (estimated with EFFORT_OUTPUT below;
                  negative when a step ran at high, which costs more than medium).

usage: tokens.py --session <id> --since <ISO-8601 UTC> [--run-dir <dir>] [--task <slug>] [--lang en|ar]
"""
import argparse
import csv
import glob
import json
import os
import sys
from datetime import datetime, timezone

# USD per million tokens: input, cache write 5m, cache write 1h, cache read, output.
# Source: platform.claude.com/docs/en/about-claude/pricing, checked 2026-10-22.
PRICES = {
    "opus": (4.00, 5.00, 8.00, 0.20, 20.00),
    "sonnet": (2.00, 2.50, 4.00, 0.10, 10.00),
    "haiku": (0.10, 0.125, 0.20, 0.01, 0.50),       # prompt <= 100k tokens
    "haiku-long": (0.50, 0.625, 1.00, 0.05, 2.50),  # prompt > 100k tokens
    "fable": (10.00, 12.50, 20.00, 0.25, 50.00),
}
BASELINE = "opus"
BASELINE_EFFORT = "medium"

# Output + thinking tokens relative to medium effort. An estimate, not a published
# Anthropic figure: effort mainly changes how much a model thinks and writes, so
# input tokens are left as they were. Tune these if your own runs show otherwise.
EFFORT_OUTPUT = {"low": 0.6, "medium": 1.0, "high": 1.5, "xhigh": 2.0, "max": 2.6}
# Effort a model runs at when the transcript does not record one.
DEFAULT_EFFORT = {"opus": "medium", "sonnet": "high", "haiku": "medium", "fable": "high"}


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


def haiku_long(fam, t):
    return fam == "haiku" and t["in"] + t["w5m"] + t["w1h"] + t["read"] > 100_000


def cost(fam, t):
    if haiku_long(fam, t):
        fam = "haiku-long"
    p = PRICES[fam]
    return (t["in"] * p[0] + t["w5m"] * p[1] + t["w1h"] * p[2]
            + t["read"] * p[3] + t["out"] * p[4]) / 1_000_000


def at_baseline_effort(t, effort):
    """Same request with its output rescaled to what BASELINE_EFFORT would write."""
    f = EFFORT_OUTPUT[BASELINE_EFFORT] / EFFORT_OUTPUT.get(effort, 1.0)
    return dict(t, out=t["out"] * f)


def usd(x):
    return ("-$%.2f" if x < 0 else "$%.2f") % abs(x)


def summary(lang, total_tok, actual, base, by_model, by_effort, saved_tok):
    saved = base - actual
    pct = (saved / base * 100) if base else 0.0
    m = lambda x: "`%s`" % usd(x)  # backticks keep amounts left-to-right in RTL text
    if lang == "ar":
        lines = [
            "التوكنز: إجمالي %s · التكلفة الفعلية %s" % (m_tok(total_tok), m(actual)),
            "لو كل الشغل ده اتعمل بـ Opus 5.5 medium: %s تقريبًا" % m(base),
            "وفّرنا %s (`%.1f%%`) ≈ %s توكن بسعر Opus" % (m(saved), pct, m_tok(saved_tok)),
            "منها: موديلات أرخص %s (محسوبة) · effort أقل %s (تقديري)" % (m(by_model), m(by_effort)),
        ]
        if by_effort < 0:
            lines.append("الـ effort بالسالب: خطوات اشتغلت على high وده أغلى من medium.")
    else:
        lines = [
            "Tokens: %s total · actual cost %s" % (m_tok(total_tok), m(actual)),
            "All of it on Opus 5.5 medium: about %s" % m(base),
            "Saved %s (`%.1f%%`) ≈ %s tokens at Opus rates" % (m(saved), pct, m_tok(saved_tok)),
            "Of which: cheaper models %s (measured) · lower effort %s (estimated)" % (m(by_model), m(by_effort)),
        ]
        if by_effort < 0:
            lines.append("Effort is negative: some steps ran at high, which costs more than medium.")
    return lines


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


def read_file(path, role, since, seen, rows):
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
            # One API response is written as several lines that repeat its usage.
            key = (path, d.get("requestId") or msg.get("id") or d.get("uuid"))
            if key in seen:
                continue
            seen.add(key)
            rows.append((role, msg.get("model"), d.get("effort") or "", split_usage(usage)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--run-dir")
    ap.add_argument("--task", default="")
    ap.add_argument("--lang", choices=("en", "ar"), default="en")
    a = ap.parse_args()

    since = parse_ts(a.since)
    main_file = find_transcript(a.session)
    if not main_file:
        print("TOKENS: transcript for session %s not found" % a.session)
        return 1

    rows, seen = [], set()
    read_file(main_file, "dispatcher (main)", since, seen, rows)
    sub_dir = os.path.join(main_file[:-len(".jsonl")], "subagents")
    for f in sorted(glob.glob(os.path.join(sub_dir, "*.jsonl"))):
        role = "subagent"
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as mh:
                role = json.load(mh).get("agentType") or role
        except (OSError, ValueError):
            pass
        read_file(f, role, since, seen, rows)

    groups = {}
    unknown = 0
    long_haiku = {}
    for role, model, effort, t in rows:
        fam = family(model)
        if fam is None:
            unknown += 1
            continue
        effort = (effort or DEFAULT_EFFORT.get(fam, "medium")).lower()
        if haiku_long(fam, t):
            long_haiku[role] = long_haiku.get(role, 0) + 1
        g = groups.setdefault((role, fam, effort), {
            "calls": 0, "tok": 0, "out": 0, "cost": 0.0, "same": 0.0, "base": 0.0})
        g["calls"] += 1
        g["tok"] += sum(t.values())
        g["out"] += t["out"]
        g["cost"] += cost(fam, t)
        g["same"] += cost(BASELINE, t)
        g["base"] += cost(BASELINE, at_baseline_effort(t, effort))

    total_tok = sum(g["tok"] for g in groups.values())
    actual = sum(g["cost"] for g in groups.values())
    same = sum(g["same"] for g in groups.values())
    base = sum(g["base"] for g in groups.values())
    saved = base - actual
    pct = (saved / base * 100) if base else 0.0
    by_model = same - actual
    by_effort = base - same
    # Opus/medium tokens the saved dollars would have bought, at this run's token mix.
    saved_tok = int(total_tok * saved / base) if base else 0

    print("| Role | Model | Effort | Calls | Tokens | Output | Cost $ | Opus-medium $ |")
    print("|---|---|---|---|---|---|---|---|")
    for (role, fam, effort), g in sorted(groups.items(), key=lambda kv: -kv[1]["cost"]):
        print("| %s | %s | %s | %d | %s | %s | %.4f | %.4f |" % (
            role, fam, effort, g["calls"], f"{g['tok']:,}", f"{g['out']:,}", g["cost"], g["base"]))
    print()
    print("TOTAL_TOKENS: %s" % f"{total_tok:,}")
    print("ACTUAL_COST_USD: %.4f" % actual)
    print("OPUS_MEDIUM_BASELINE_USD: %.4f (estimate)" % base)
    print("SAVED_USD: %.4f (%.1f%%)" % (saved, pct))
    print("  FROM_CHEAPER_MODELS_USD: %.4f (measured: same tokens at Opus rates = %.4f)" % (by_model, same))
    print("  FROM_LOWER_EFFORT_USD: %.4f (estimated, output scaled by %s)" % (
        by_effort, ", ".join("%s %.1f" % kv for kv in EFFORT_OUTPUT.items() if kv[0] in ("low", "medium", "high"))))
    print("SAVED_OPUS_EQUIVALENT_TOKENS: %s" % f"{saved_tok:,}")
    print("HAIKU_OVER_100K: %d%s" % (sum(long_haiku.values()), (" (" + ", ".join(
        "%s %d" % kv for kv in sorted(long_haiku.items())) + ")") if long_haiku else ""))
    if unknown:
        print("UNPRICED_REQUESTS: %d (model not recognised)" % unknown)
    print()
    print("SUMMARY:")
    for line in summary(a.lang, total_tok, actual, base, by_model, by_effort, saved_tok):
        print(line)

    if a.run_dir:
        ledger = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(a.run_dir))), "ledger.csv")
        header = ["date", "project", "task", "tokens", "actual_usd", "opus_medium_usd",
                  "saved_pct", "saved_models_usd", "saved_effort_usd"]
        if os.path.exists(ledger):
            with open(ledger, encoding="utf-8") as fh:
                first = fh.readline().strip()
            if first != ",".join(header):  # older format: keep it beside the new one
                os.replace(ledger, ledger[:-4] + "-v1.csv")
        new = not os.path.exists(ledger)
        with open(ledger, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(header)
            w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        os.path.basename(os.path.dirname(os.path.abspath(a.run_dir))),
                        a.task, total_tok, "%.4f" % actual, "%.4f" % base, "%.1f" % pct,
                        "%.4f" % by_model, "%.4f" % by_effort])
        print("LEDGER: %s" % ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
