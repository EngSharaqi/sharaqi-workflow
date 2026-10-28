#!/usr/bin/env python3
"""Routing policy for sharaqi: facts in, one route out.

The orchestrator judges the facts from the task text (and wc / git status); this script
applies the policy, so the same facts always give the same track, plan, approval, executor
and review. It doesn't read the repo and can't see or change the context gate: that is
hooks/context-gate.sh, on every track. Thresholds follow references/delegation.md
(break-even ~3 work turns, inline under ~30 changed lines in one file).

usage: route.py --track coding|noncoding|mixed|review|ops [facts]
  --critical none|auth|secrets|parsing|migration|deletion|irreversible|money|infra
                    required for coding and mixed (the code part)
  --behaviour yes|no   the change alters behaviour, logic or data shape   (default yes)
  --uncertain yes|no   cause or design unclear                           (default no)
  --files N --lines N  files touched, changed lines, estimated           (default 2, 30)
  --checks yes|no      tests or a typecheck would catch a miss           (default no)
  --shape trivial|mechanical|feature|tricky|judgement                    (default feature)
  --turns N            non-coding and ops: estimated work turns          (default 1)
  --artifact code|doc  review: what is reviewed                          (required)
  --op install|test|deperr|git-read|commit|push|ado-read|ado-write|web|research|conflict
                       ops: the operation                                (required)
  --failed N           ops: failed attempts at the current rung, with new evidence (default 0)
  --floor FAST|STANDARD|CRITICAL  the mode so far: a re-route never lowers it
Prints `ROUTE key=value ...` and `WHY ...`; exit 2 on bad or contradictory facts.
"""
import argparse
import sys

MODES = ("FAST", "STANDARD", "CRITICAL")
SECURITY = ("auth", "secrets", "parsing")
CRITICAL = SECURITY + ("migration", "deletion", "irreversible", "money", "infra")
SHAPES = ("trivial", "mechanical", "feature", "tricky", "judgement")
INLINE_LINES = 30
BREAK_EVEN_TURNS = 3  # haiku-*, references/delegation.md
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
REVIEW ={"R7": "reviewer·opus·low", "R7+": "reviewer-medium·opus·medium",
          "R7+sec": "reviewer-high·opus·high"}


class Bad(Exception):
    pass


def yes(v):
    return v == "yes"


def rung(f):
    """Executor for a code part that isn't tiny. Tests one rung lower, none one higher."""
    if f.files <= 1 and f.lines < INLINE_LINES:
        return "inline", "one file, under ~30 lines: below break-even"
    if f.shape == "judgement":
        return "R6·opus-medium", "judgement a brief can't pin down"
    if f.shape == "tricky":
        return "R4·sonnet-high", "tricky logic"
    if f.shape in ("trivial", "mechanical") and not yes(f.behaviour):
        return "R2·haiku-medium", "mechanical, no new logic"
    if yes(f.checks) and not yes(f.uncertain):
        return "R3·haiku-high", "logic with tests or a typecheck to catch a miss"
    return "R4·sonnet-high", ("unclear cause" if yes(f.checks)
                              else "logic without a check that catches a miss")


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
    tiny = (mode == 0 and f.files <= 1 and f.lines < INLINE_LINES
            and f.shape in ("trivial", "mechanical"))
    if tiny:
        return dict(tier="tiny", mode="FAST", plan="none", approval="no", executor="inline",
                    review="none", checks="diff+narrowest"), \
            "tiny: one file, under ~30 lines, no behaviour change, no CRITICAL trigger"
    executor, why = rung(f)
    if mode == 2:
        review = REVIEW["R7+sec"] if f.critical in SECURITY else REVIEW["R7+"]
        return dict(tier="critical", mode="CRITICAL", plan="card", approval="yes",
                    executor=executor, review=review, checks="standard+negative"), \
            f"CRITICAL trigger {f.critical}: plan, approval and R7+ review at any size; {why}"
    return dict(tier="planned", mode=MODES[mode], plan="card", approval="yes",
                executor=executor, review=REVIEW["R7"],
                checks="narrowest" if mode == 0 else "tests+lint"), \
        f"not tiny ({'behaviour changes' if yes(f.behaviour) else 'size or shape'}); {why}"


def noncoding(f):
    if f.critical not in (None, "none"):
        raise Bad("a CRITICAL trigger means code or config changes: use --track coding or mixed")
    if f.floor:
        raise Bad("--floor means a code mode was set: re-route with --track coding or mixed")
    delegate = (f.turns > BREAK_EVEN_TURNS and not yes(f.uncertain)
                and f.shape in ("trivial", "mechanical", "feature"))
    executor = "R8·haiku-low" if delegate else "inline"
    why = ("well-specified and past break-even: R8 Writer" if delegate
           else "inline: under break-even or needs judgement")
    return dict(tier="direct", mode="-", plan="none", approval="no", executor=executor,
                review="none", checks="none"), why + "; review only on /sharaqi review"


def review(f):
    if f.artifact is None:
        raise Bad("--artifact code|doc is required for --track review")
    if f.floor:
        raise Bad("--floor doesn't apply to a review: pass the code's trigger with --critical")
    if f.artifact == "doc" and f.critical not in (None, "none"):
        raise Bad("a CRITICAL trigger means code: use --artifact code")
    if f.artifact == "doc":
        r, why = REVIEW["R7"], "document review against the user's requirements"
    elif f.critical in SECURITY:
        r, why = REVIEW["R7+sec"], f"code review, CRITICAL trigger {f.critical}"
    elif f.critical not in (None, "none"):
        r, why = REVIEW["R7+"], f"code review, CRITICAL trigger {f.critical}"
    else:
        r, why = REVIEW["R7"], "code review of the given diff only"
    return dict(tier="review", mode="-", plan="none", approval="no", executor="none",
                review=r, checks="none", scope="diff" if f.artifact == "code" else "artifact",
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
        escalate = "ask"  # one escalation per task (delegation.md); then the user, or R6
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
    p.add_argument("--artifact", choices=("code", "doc"))
    p.add_argument("--floor", choices=MODES)
    p.add_argument("--op", choices=tuple(OPS))
    p.add_argument("--failed", type=int, default=0)
    f = p.parse_args(argv)
    if f.files < 0 or f.lines < 0 or f.turns < 0 or f.failed < 0:
        p.error("--files, --lines, --turns and --failed can't be negative")
    if f.track != "ops" and (f.op or f.failed):
        p.error("--op and --failed apply only to --track ops")
    return f


def main(argv=None):
    f = parse(sys.argv[1:] if argv is None else argv)
    try:
        out, why = route(f)
    except Bad as e:
        print(f"route.py: {e}", file=sys.stderr)
        return 2
    keys = ("tier", "mode", "plan", "approval", "executor", "review", "checks")
    extra = [k for k in out if k not in keys]
    print("ROUTE track=" + f.track + "".join(f" {k}={out[k]}" for k in keys + tuple(extra))
          + " gate=hook")
    print("WHY " + why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
