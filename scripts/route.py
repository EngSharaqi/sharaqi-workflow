#!/usr/bin/env python3
"""Routing policy for sharaqi v1.0: facts in, one route out.

scripts/classify.py judges the facts from the task text (in the UserPromptSubmit hook, no
model call); the Sonnet seat may correct a fact after its first reads and re-run this
script. The policy is applied here, so the same facts always give the same track, plan,
approval, executor, review and escalation. It doesn't read the repo and can't see or change
the context gate: that is hooks/context-gate.sh, on every track.

Opus appears only with an `escalate=` reason (hooks/agent-audit.sh blocks an Opus Agent call
without one): `critical` (a CRITICAL trigger: Opus reviews), `failed-twice` (checks still
fail after two repair attempts: Opus implements), `reasoning` (judgement a brief can't pin
down). Everything else runs on the Sonnet seat or a cheaper rung.

usage: route.py --track coding|noncoding|mixed|review|ops [facts]
  --critical none|auth|secrets|parsing|migration|deletion|irreversible|money|infra
                    required for coding and mixed (the code part)
  --behaviour yes|no   the change alters behaviour, logic or data shape   (default yes)
  --uncertain yes|no   cause or design unclear                           (default no)
  --files N --lines N  files touched, changed lines, estimated           (default 2, 30)
  --checks yes|no      tests or a typecheck would catch a miss           (default no)
  --shape trivial|mechanical|feature|tricky|judgement                    (default feature)
  --turns N            non-coding and ops: estimated work turns          (default 1)
  --research yes|no    non-coding: needs web sources (research tier)     (default no)
  --artifact code|doc  review: what is reviewed                          (required)
  --op install|test|deperr|git-read|commit|push|ado-read|ado-write|web|research|conflict
                       ops: the operation                                (required)
  --failed N           failed repair attempts with new evidence (default 0); code: 2 escalates
                       the executor to Opus (escalate=failed-twice); ops: 1 one rung, 2 ask
  --floor FAST|STANDARD|CRITICAL  the mode so far: a re-route never lowers it
  --session ID         log this route as a `reroute` event in the session's events log, so
                       hooks/agent-audit.sh applies it to the next Agent call
Prints `ROUTE key=value ...` and `WHY ...`; exit 2 on bad or contradictory facts.
"""
import argparse
import json
import os
import re
import sys
import time

MODES = ("FAST", "STANDARD", "CRITICAL")
SECURITY = ("auth", "secrets", "parsing")
CRITICAL = SECURITY + ("migration", "deletion", "irreversible", "money", "infra")
SHAPES = ("trivial", "mechanical", "feature", "tricky", "judgement")
INLINE_LINES = 30
BREAK_EVEN_TURNS = 3  # haiku-*, docs/architecture.md (computed for an Opus seat)
BREAK_EVEN_SONNET = 4  # sonnet-high, same table
# Ops: default rung for a delegated run, whether an implementer can run it (it has no git
# write, Web or MCP tools), and whether each run needs the user's explicit yes (rule 6).
OPS = {
    "install": ("haiku-low", True, False),
    "test": ("haiku-low", True, False),
    "deperr": ("haiku-medium", True, False),
    "git-read": ("haiku-low", True, False),
    "commit": ("haiku-low", False, True),
    "push": ("haiku-low", False, True),
    "ado-read": ("haiku-low", False, False),
    "ado-write": ("haiku-medium", False, True),
    "web": ("haiku-low", False, False),
    "research": ("sonnet-high", False, False),
    "conflict": ("sonnet-high", True, False),
}
OPS_LADDER = ("haiku-low", "haiku-medium", "haiku-high", "sonnet-high")
OPS_FIX = ("test", "deperr", "conflict")  # a fix that edits files is a code task
# Reviewer: Sonnet by default; Opus only for a CRITICAL trigger (escalate=critical).
REVIEW = {"R7": "reviewer·sonnet·low", "R7+": "reviewer·opus·medium",
          "R7+sec": "reviewer·opus·high"}
SEAT = "sonnet"
WIDE_FILES, WIDE_LINES = 3, 60  # past this, a fresh Sonnet context pays for its brief
# Research tier (non-coding with web sources): the floor the seat must meet before writing.
RESEARCH = dict(searches=6, sources=10)


class Bad(Exception):
    pass


def yes(v):
    return v == "yes"


def rung(f):
    """Executor for a code part that isn't tiny, seen from a Sonnet seat. Tests one rung
    lower; a Sonnet subagent only when the work is wide enough to pay for a fresh context,
    since inline is already Sonnet. Medium effort: at high, the e2e benchmark's implementer
    spent 17k of 38k output tokens thinking and lost to plain Opus on cost and time."""
    if f.files <= 1 and f.lines < INLINE_LINES:
        return "inline", "one file, under ~30 lines: below break-even"
    if f.shape == "judgement":
        return "R6·opus-medium", "judgement a brief can't pin down (escalate=reasoning)"
    if f.shape in ("trivial", "mechanical") and not yes(f.behaviour):
        return "R2·haiku-medium", "mechanical, no new logic"
    wide = f.files >= WIDE_FILES or f.lines >= WIDE_LINES
    if f.shape == "tricky":
        return ("R4·sonnet-medium", "tricky logic, wide enough for its own context") if wide \
            else ("inline", "tricky but small: the Sonnet seat does it")
    if yes(f.checks) and not yes(f.uncertain):
        return "R3·haiku-high", "logic with tests or a typecheck to catch a miss"
    why = "unclear cause" if yes(f.checks) else "logic without a check that catches a miss"
    return ("R4·sonnet-medium", why + ", wide enough for its own context") if wide \
        else ("inline", why + "; small enough for the Sonnet seat")


def coding(f):
    if f.critical is None:
        raise Bad("--critical is required for a code part (none, or the trigger)")
    floor = MODES.index(f.floor) if f.floor else 0
    if f.critical != "none":
        mode = 2
    elif yes(f.behaviour) or yes(f.uncertain) or f.shape in ("feature", "tricky", "judgement"):
        mode = 1
    else:
        mode = 0
    mode = max(mode, floor)
    if mode == 2 and f.critical == "none":
        raise Bad("--floor CRITICAL needs the trigger: pass --critical <trigger> again")
    tiny = (mode == 0 and f.files <= 1 and f.lines < INLINE_LINES
            and f.shape in ("trivial", "mechanical") and f.failed == 0)
    if tiny:
        return dict(tier="tiny", mode="FAST", plan="none", approval="no", executor="inline",
                    review="none", checks="diff+narrowest", escalate="none"), \
            "tiny: one file, under ~30 lines, no behaviour change, no CRITICAL trigger"
    executor, why = rung(f)
    escalate = "reasoning" if executor.startswith("R6") else "none"
    if f.failed >= 2:
        executor, escalate = "R6·opus-medium", "failed-twice"
        why = "checks still fail after two repair attempts: Opus implements the next one"
    elif f.failed == 1:
        why += "; one failed attempt: retry at this rung with the new evidence"
    if mode == 2:
        review = REVIEW["R7+sec"] if f.critical in SECURITY else REVIEW["R7+"]
        plan = "planner·opus·high" if yes(f.uncertain) else "card"
        if escalate == "none":
            escalate = "critical"
        return dict(tier="critical", mode="CRITICAL", plan=plan, approval="yes",
                    executor=executor, review=review, checks="standard+negative",
                    escalate=escalate), \
            (f"CRITICAL trigger {f.critical}: plan, approval and an Opus review at any size"
             + ("; Opus plans because the design is unclear" if plan != "card" else "")
             + f"; {why}")
    # No approval wait and no reviewer below CRITICAL: in the e2e benchmark the wait cost a
    # turn and the Sonnet reviewer found nothing (140 s on the complex task). The seat runs
    # the checks and checks the diff against the acceptance list itself.
    return dict(tier="planned", mode=MODES[mode], plan="card", approval="no",
                executor=executor, review="none", escalate=escalate,
                checks="narrowest" if mode == 0 else "tests+lint"), \
        (f"not tiny ({'behaviour changes' if yes(f.behaviour) else 'size or shape'}); {why}"
         "; below CRITICAL: no approval wait, the seat checks the diff")


def noncoding(f):
    if f.critical not in (None, "none"):
        raise Bad("a CRITICAL trigger means code or config changes: use --track coding or mixed")
    if f.floor:
        raise Bad("--floor means a code mode was set: re-route with --track coding or mixed")
    if yes(f.research):  # web tools are the seat's only: never delegated
        return dict(tier="direct", mode="-", plan="none", approval="no", executor="inline",
                    review="none", checks="links", escalate="none",
                    research="searches>=%(searches)d,sources>=%(sources)d" % RESEARCH), \
            ("research: web sources needed; inline (only the seat has web tools), with a "
             "floor of searches and sources and every cited link opened")
    delegate = (f.turns > BREAK_EVEN_TURNS and not yes(f.uncertain)
                and f.shape in ("trivial", "mechanical", "feature"))
    executor = "R8·haiku-low" if delegate else "inline"
    why = ("well-specified and past break-even: R8 Writer" if delegate
           else "inline: under break-even or needs judgement")
    return dict(tier="direct", mode="-", plan="none", approval="no", executor=executor,
                review="none", checks="none", escalate="none"), \
        why + "; review only on /sharaqi review"


def review(f):
    if f.artifact is None:
        raise Bad("--artifact code|doc is required for --track review")
    if f.floor:
        raise Bad("--floor doesn't apply to a review: pass the code's trigger with --critical")
    if f.artifact == "doc" and f.critical not in (None, "none"):
        raise Bad("a CRITICAL trigger means code: use --artifact code")
    escalate = "none"
    if f.artifact == "doc":
        r, why = REVIEW["R7"], "document review against the user's requirements"
    elif f.critical in SECURITY:
        r, why, escalate = REVIEW["R7+sec"], f"code review, CRITICAL trigger {f.critical}", \
            "critical"
    elif f.critical not in (None, "none"):
        r, why, escalate = REVIEW["R7+"], f"code review, CRITICAL trigger {f.critical}", "critical"
    else:
        r, why = REVIEW["R7"], "code review of the given diff only"
    return dict(tier="review", mode="-", plan="none", approval="no", executor="none",
                review=r, checks="none", escalate=escalate,
                scope="diff" if f.artifact == "code" else "artifact",
                fixes="ask"), why + "; read-only, fixes only after a yes"


def ops(f):
    if f.op is None:
        raise Bad("--op is required for --track ops")
    if f.critical not in (None, "none"):
        raise Bad("a CRITICAL trigger means code or config changes: use --track coding or mixed")
    if f.floor:
        raise Bad("--floor means a code mode was set: re-route with --track coding or mixed")
    rung, delegable, authz = OPS[f.op]
    i = OPS_LADDER.index(rung)
    if f.shape == "tricky":  # interacting constraints or conflicting sources, shown not guessed
        i = OPS_LADDER.index("sonnet-high")
    escalate = "none"
    if f.failed == 1:
        i = min(i + 1, len(OPS_LADDER) - 1)
        escalate = "one-rung"
    elif f.failed >= 2:
        escalate = "ask"  # one escalation per task; then the user
    rung = OPS_LADDER[i]
    limit = BREAK_EVEN_SONNET if rung.startswith("sonnet") else BREAK_EVEN_TURNS
    if escalate == "ask":
        executor, why = "ask", "failed twice at this rung: stop and ask (Opus only through R6)"
    elif not delegable:
        executor, why = "inline", "the implementer has no tool for it (git write, Web or MCP)"
    elif f.turns > limit and not yes(f.uncertain):
        executor, why = rung, "past break-even and well-specified: delegate"
    else:
        executor, why = "inline", "under break-even: inline costs less than a brief and a subagent"
    out = dict(tier="ops", mode="-", plan="none", approval="no", executor=executor,
               review="none", checks="exit-code", op=f.op, rung=rung,
               delegable="yes" if delegable else "no",
               authz="explicit-yes" if authz else "no", escalate=escalate)
    if f.op in OPS_FIX:
        out["fix"] = "reroute-coding"
    tail = "; each run needs the user's explicit yes" if authz else ""
    return out, why + tail + "; no review for a routine operation"


def route(f):
    if f.track == "ops":
        return ops(f)
    if f.track == "coding":
        return coding(f)
    if f.track == "noncoding":
        return noncoding(f)
    if f.track == "review":
        return review(f)
    out, why = coding(f)  # mixed: the facts describe the code part
    out["writing"] = "direct"
    return out, "code part: " + why + "; writing parts delivered directly, outside the plan"


def route_line(track, out):
    keys = ("tier", "mode", "plan", "approval", "executor", "review", "escalate", "checks")
    extra = [k for k in out if k not in keys]
    return ("ROUTE track=" + track + "".join(f" {k}={out[k]}" for k in keys + tuple(extra))
            + f" seat={SEAT} gate=hook")


def parse(argv):
    p = argparse.ArgumentParser(add_help=True, usage=__doc__)
    p.add_argument("--track", required=True,
                   choices=("coding", "noncoding", "mixed", "review", "ops"))
    p.add_argument("--critical", choices=("none",) + CRITICAL)
    p.add_argument("--behaviour", default="yes", choices=("yes", "no"))
    p.add_argument("--uncertain", default="no", choices=("yes", "no"))
    p.add_argument("--files", type=int, default=2)
    p.add_argument("--lines", type=int, default=INLINE_LINES)
    p.add_argument("--checks", default="no", choices=("yes", "no"))
    p.add_argument("--shape", default="feature", choices=SHAPES)
    p.add_argument("--turns", type=int, default=1)
    p.add_argument("--research", default="no", choices=("yes", "no"))
    p.add_argument("--artifact", choices=("code", "doc"))
    p.add_argument("--floor", choices=MODES)
    p.add_argument("--op", choices=tuple(OPS))
    p.add_argument("--failed", type=int, default=0)
    p.add_argument("--session")
    f = p.parse_args(argv)
    if f.files < 0 or f.lines < 0 or f.turns < 0 or f.failed < 0:
        p.error("--files, --lines, --turns and --failed can't be negative")
    if f.track != "ops" and f.op:
        p.error("--op applies only to --track ops")
    if f.track in ("noncoding", "review") and f.failed:
        p.error("--failed applies to code and ops tracks")
    if f.research == "yes" and f.track != "noncoding":
        p.error("--research applies only to --track noncoding")
    return f


def log_reroute(sid, argv, line, why):
    """Append a `reroute` event to <state>/<session>.events.jsonl. Never raises."""
    if not sid or not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
        return False
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    d = os.path.join(root, "sharaqi-state")
    try:
        os.makedirs(d, exist_ok=True)
        args = [a for i, a in enumerate(argv) if a != "--session"
                and (i == 0 or argv[i - 1] != "--session")]
        ev = {"event": "reroute", "route": line, "why": why, "args": " ".join(args),
              "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with open(os.path.join(d, sid + ".events.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    f = parse(argv)
    try:
        out, why = route(f)
    except Bad as e:
        print(f"route.py: {e}", file=sys.stderr)
        return 2
    line = route_line(f.track, out)
    print(line)
    print("WHY " + why)
    if f.session is not None and not log_reroute(f.session, argv, line, why):
        print("route.py: re-route not logged (bad session id or state dir unwritable)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
