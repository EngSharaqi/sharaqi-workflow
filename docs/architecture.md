# Architecture and design decisions

How sharaqi is built, why, and what the measurements changed along the way.
The README has the short version.

## v1.0 (experimental): Sonnet seat, Opus on escalation

From the LLM council of 2026-10-28: as long as Opus is the main loop, every feature the
plugin adds costs more than plain Opus. v1.0 changes the seat. **Routing measured, tasks
not**: on the 11-case three-arm routing benchmark v1.0 cost 54.9% less than plain Claude
Code and took 36.5% less wall clock, with 11/11 routes
([benchmarks/v1.0/RESULTS.md](../benchmarks/v1.0/RESULTS.md)). No finished task has been
measured on v1.0.

```
/sharaqi do <task>
  UserPromptSubmit hook (hooks/route-prompt.sh → scripts/classify.py, no model call)
    text → facts (each stated or assumed) → scripts/route.py → ROUTE line
    + BASE snapshot when the route plans + only this route's steps (references/routes/)
  Sonnet 5.5 · medium (SKILL.md frontmatter; 1,672 B)
    tiny / direct / ops: does it; planned / critical: plan, stop, wait for /sharaqi go
    executors: inline · haiku (R2, R3, R8) · sonnet-high (R4, only when wide)
    reviewer: Sonnet · low; Opus · medium/high only for a CRITICAL trigger
  Opus, only with escalate=critical | failed-twice | reasoning (hooks/agent-audit.sh)
```

| What changed | Why | Verified how |
|---|---|---|
| `model: sonnet` in the skill | the seat's cache reads dominate cost (v0.4 audit, council) | stand-in API: every request of the `/sharaqi` turn is `claude-sonnet-5-5` · medium |
| Routing in a prompt hook | v0.9 spent a full Opus turn judging facts and running route.py | `additionalContext` reaches the model on a `/plugin:skill` prompt (stand-in API); 11/11 cases route as registered (tests) |
| SKILL.md 18,487 B → 1,672 B; per-route steps injected (119–1,358 B per file) | the skill text was paid on every turn | first request +24,513 B over plain in v0.9, +3,174 B in v1.0 (stand-in API, equal tool set) |
| 7 agents → 3 (`implementer`, `reviewer`, `planner`) | the variants differed only in name and effort; the Agent tool takes `effort` per call (2.1.312) | `diff` of the files; the per-call effort reaches the subagent request |
| Opus needs `escalate:<reason>` in the call's description | Opus must be auditable | hook blocks without it; logs every call |
| `run_in_background: false` required | a background agent's result returns on a turn that runs on the session model (Opus) | stand-in API: background → `claude-opus-5-5` turn; foreground → Sonnet throughout; two foreground calls in one message started 0.01 s apart |
| `/sharaqi go` approves a plan | the skill's model lasts only its own turn; a plain "yes" runs on Opus | stand-in API, `--resume`: the follow-up request was `claude-opus-5-5` |
| Benchmark mode for the gate | `claude -p` has no statusline, so v0.9's gate blocked every Agent call | gate tests; stand-in run with and without it |
| Gate re-reads a missing transcript | on the first tool call of a headless session the transcript doesn't exist yet | stand-in run: the first Agent call was blocked before, allowed after |
| `▶`/`◀` lines, token receipt only with `--debug` | they were paid at the seat's output rate on every run | tests: no route's steps contain them unless debug |
| `scripts/runrecord.py` | one record per run, the same accounting for every arm | the 22 published runs: transcript estimate equals Claude Code's cost (v0.9 exactly, plain within $0.00013) |

**Classifier limits.** `scripts/classify.py` matches phrases, not meaning. Its unknowns
fall to the safe side (behaviour changes, no checks, coding track, so plan and approval),
and the seat corrects an `assumed` fact after its first reads by re-running route.py; a
CRITICAL trigger can't be dropped. The 11 benchmark cases were visible while its rules
were written. Of 15 prompts written afterwards, the first version misrouted three, two of
them unsafe (a `DROP TABLE` without the deletion trigger; "instead of the email" taken
as a writing task). Both are fixed and in the tests; more such misses are likely.

**Break-even thresholds** (`route.py`: ~3 work turns for haiku, inline under ~30 lines in
one file) were computed for an Opus seat. With a Sonnet seat inline turns cost less, so the
true break-even is probably higher. Not re-measured.

**Not verified**: an interactive session end to end (the hooks are the same; the gate
there uses the statusline bridge); Sonnet 5.5 prices against Claude Code's `costUSD`
(`prices.json` keeps `verified: false`; on the benchmark the estimate ran ~$0.0025 per run
above the CLI cost); any cost or time saving on a finished task.

## The shape (v0.9)

```
/sharaqi do <task>
  └─ Opus (orchestrator, medium effort)
       1. understand and route, in one turn: base commit, dirty state, line counts of
          the named paths, and scripts/route.py on the judged facts → one ROUTE line:
          track | tier | plan | approval | executor | review; a plan only when planned/critical
       2. implement: inline, or briefs to implementer agents (parallel when files are disjoint)
       3. verify: re-run the checks itself (with the reviewer, in parallel, when one is due)
       4. self-review the delta, one line per point
       5. report: template only, plus a token receipt after delegation
/sharaqi route <task>   → the ROUTE line and one reason line; nothing else runs
/sharaqi review [target] → read-only review of a diff or a document; asks before any fix
```

Everything a FAST task needs is in `SKILL.md` (7,638 bytes in v0.8, down
from 8,666). Each file in `references/` is read only when its row applies:
`delegation.md` and `brief.md` only when the route names a delegated rung.

## Routing (v0.9)

One decision, made once, in the orchestrator's first turn. Opus judges the
facts from the task text and cheap signals (line counts, `git status`), never
from reading files it will hand off; `scripts/route.py` applies the policy to
those facts in the same first command, so equal facts give an equal route:

```
ROUTE track=coding tier=planned mode=STANDARD plan=card approval=yes executor=R3·haiku-high review=reviewer·opus·low checks=tests+lint gate=hook
WHY not tiny (behaviour changes); logic with tests or a typecheck to catch a miss
```

| Input | Where it shows |
|---|---|
| Track: coding, non-coding, mixed (the code part), review | non-coding gets no plan and no review; mixed routes only its code part |
| CRITICAL trigger | tier `critical` at any size: plan, approval, R7+ reviewer |
| One file, < ~30 lines, no behaviour change, trivial/mechanical | tier `tiny`: no plan, no approval, no reviewer; diff check and the narrowest check |
| Anything else that changes code | tier `planned`: plan ≤ 12 lines, approval, reviewer Opus · low |
| Change size, mechanical vs judgement, tests | executor rung, via the break-even below |
| Track `ops` and `--op` (install, test, git, commit, push, Azure DevOps, web, conflict) | tier `ops`: no plan, no reviewer; `rung` is the model if delegated, `executor=inline` below break-even or when the implementer lacks the tool (`delegable=no`); `authz=explicit-yes` for commit, push and Azure DevOps writes, separate from the model; a fix that edits files re-routes as code |

The context gate is not part of the route: hooks/context-gate.sh gates every
Agent, Edit and Write call of a `/sharaqi` run, whatever the track.

The rung ladder, cheapest first (`docs/model-effort-plan.md` §5, since
v0.8): `inline` (tiny known edit), `haiku-medium` (R2), `haiku-high` (R3, with
tests), `sonnet-high` (R4), `opus-medium` (R6), `opus-high` (R6+); `opus-low`
(R5) answers questions only. Task-shape examples per rung are in
[references/delegation.md](../references/delegation.md). Routing accuracy
is measured offline against 16 pre-registered cases
([benchmarks/v0.8/routing-cases.md](../benchmarks/v0.8/routing-cases.md)).
The v0.9 tracks and tiers have their own cases, written but not yet run
([benchmarks/v0.9/routing-cases.md](../benchmarks/v0.9/routing-cases.md)).

### Break-even economics

`scripts/breakeven.py` computes when delegating a slice costs less than
doing it on the Opus orchestrator. A *work turn* is one read, edit or check
run. With prices `r` from `scripts/prices.json`:

```
turn(thread)  = C·r_read + d·r_write + o·r_out          C context re-read, d new tokens, o output
fixed cost  F = b·r_out(orch) + 2·turn(orch, no output) + S·r_write(target)
saving/turn s = turn(orch) − turn(target) − o_target·r_write(orch)
break-even n* = F / s     (work turns; delegate a slice expected to need more)
```

`b` is the brief, the two orchestrator turns are the spawn and the result,
`S` is the subagent's first prompt, and the last term of `s` is the diff the
orchestrator reads back once per delegated turn of output. `C`, `d`, `o` and
`S` are medians measured from the usage of the one recorded delegated session
in `tests/fixtures/bench-2026-10-22` (orchestrator: context 51,447, new
1,193, output 436 tokens per request, all cache writes 1-hour; implementer:
first prompt 12,829, context 14,912, new 911, output 329). Cache writes are
priced at the 5m/1h split each thread used. `b` = 800 tokens is the one
assumption; the script prints `n*` at half and double of it.

| Orchestrator → target | n* (b = 400 · 800 · 1600) |
|---|---|
| claude-opus-5 → claude-haiku-4-5 | 2.5 · 2.7 · 3.2 |
| claude-opus-5 → claude-sonnet-5 | 3.2 · 3.5 · 4.0 |
| claude-opus-5 → claude-opus-5 (fresh context) | 6.9 · 7.3 · 8.2 |
| claude-opus-5-5 → claude-sonnet-5 | 4.6 · 5.1 · 6.0 |
| claude-opus-5-5 → claude-opus-5 | 28.1 · 29.9 · 33.4 |

(`python3 scripts/breakeven.py [--orchestrator claude-opus-5-5]`; a test pins
the first column's middle values.) The plain arm of the v0.7.1 medium
benchmark took 32 turns for 12 changed files, about 2.5–3 turns per file, so
the heuristics in delegation.md read: inline for one file and about two work
turns; haiku or sonnet from about two files or any edit-test loop; an Opus
implementer only for about three files or more. They are heuristics: one
session's medians, one task shape. The model leaves out rework (a rung that
fails costs its turns plus the next rung's), the extra turns a weaker model
may need, and effort (more thinking is more output). Those are why the rule
says *the cheapest rung that gets it right*, not the cheapest rung.

### Why effort lives in agent files

The Agent tool on Claude Code 2.1.274 has a `model` parameter and no
`effort` (the per-invocation `effort` parameter needs 2.1.292 or later,
per the subagent docs). The docs say an agent file's `effort:` overrides the
session's effort. A captured run on 2026-10-25 checked what actually runs:
`claude -p --model opus --effort medium` spawning probe agents, with the
`effort` field each subagent request recorded in its transcript.

| Agent file (model / effort) | Call's `model` | Ran as | Effort recorded |
|---|---|---|---|
| sonnet / low | sonnet | claude-sonnet-5 | low |
| sonnet / high | sonnet | claude-sonnet-5 | high |
| opus / high | opus | claude-opus-5 | high |
| sonnet / low | opus | claude-opus-5 | low |
| opus / high | sonnet | claude-sonnet-5 | high |
| haiku / low | haiku | claude-haiku-4-5 | none |
| sonnet / high | haiku | claude-haiku-4-5 | none |

So the file sets the effort, the call sets the model, and `--effort` on the
session doesn't override the file. Three implementer files (`implementer-low`,
`implementer` = medium, `implementer-high`) cover every rung; the `haiku`
alias resolved to Haiku 4.5 on 2.1.274, which has no effort setting, so the
two haiku rungs were one. On 2.1.312 `haiku` resolves to `claude-haiku-5-5`
and its effort applies (model-effort-plan.md §4), which is why v0.8 routes
R2 and R3 to Haiku. `planner` (opus, high, read-only) replaces the built-in Plan
agent, whose effort sharaqi couldn't set. The hook reads the named file's
`effort:` and blocks a pair over the ceiling (a file or call
effort of `xhigh` or `max`); a test parses delegation.md's rung table and checks
every pair through the hook. `CLAUDE_CODE_EFFORT_LEVEL`, when set, overrides
the file (docs); the hook can't see that.

## Decisions

### Opus decides, cheaper models type

Most of the cost of an agentic task is the orchestrating model re-reading
its context on every turn, not the tokens a worker writes. So the expensive
model does what needs judgement (sizing, diagnosis, planning, reading diffs),
and a cheaper model does what needs typing (edits across many files, test
loops). The first measurement backs the second half: the Sonnet implementer
cost $0.07 of a $1.49 run
([2026-10-22-cart-toy.md](../benchmarks/2026-10-22-cart-toy.md)).

### Delegate only past a break-even

Delegation is not free: a brief, the worker's own context, and Opus
re-verifying the result. Until v0.7.1 the threshold was a guess (inline for
about three files or fewer), and on the medium benchmark it kept every run
inline. Since v0.8 it is derived from prices and measured usage (Break-even
economics, above) and still labelled a heuristic.

### Mode by blast radius, not by domain words

v0.6 rated a 20-line cart calculation CRITICAL because it touched money, and
paid for a mandatory Opus reviewer. v0.7 rates by what a mistake would break
and how hard it is to undo: cart-total math is STANDARD, charging a card is
CRITICAL. The mode can go up after the diff, never down.

### No code in briefs

In v0.4 the planner wrote code into task cards for cheaper models to copy.
The code was written twice and reviewed as a third thing. Briefs now carry
pointers (paths, names, the pattern to follow), the acceptance criteria, the
edge inputs and the real check commands. A signature or a one-line example is
allowed when prose can't pin a detail down.

### An implementer's "done" is a claim

The orchestrator re-runs the checks and reads the diff. Its report states
only what it ran and saw. Tests and reviewers lower risk; the report never
calls them proof.

### Edge inputs as a line, not a reviewer

In the first measurement the plain run shipped a NaN total for a missing
coupon value and the skill's Opus reviewer caught it. A reviewer subagent is
an expensive way to find that. v0.7 moved the catch into one line of step 1
(the invalid inputs the changed code must handle) and one point of the
self-review. In the v0.7 run that line caught the same case with no reviewer.

### Read-only reviewer by construction

The reviewer agent's tools are Read, Grep and Glob. Claude Code enforces
that; the prompt doesn't have to. It gets the diff in its prompt because it
can't run `git diff`.

### A model ceiling the hook enforces

`hooks/cap-model.sh` blocks an Agent call that names a blocked model (Fable,
Mythos), an effort above the cap, or, during a run, no model at all (it would
inherit the session's model). The ceiling lives in `scripts/prices.json`;
the script's fallback copy is kept equal by a test.

Effort: until v0.7.1 the hook could check effort only when a call carried
one, which the Agent tool on 2.1.274 never does. Since v0.8 it falls back to
the `effort:` of the named sharaqi agent file, which is what that subagent
runs at (Why effort lives in agent files, above). What it still can't see:
the effort of non-sharaqi agents, and `CLAUDE_CODE_EFFORT_LEVEL`.

### Hooks inert outside a run

Plugin hooks load in every session. In v0.6 that meant the ceiling hook
checked Agent calls in sessions that never ran sharaqi, including the plain
arm of the first benchmark. Since v0.7, `session-hints.sh` writes a
per-session marker when a prompt starts with `/sharaqi`, and the global hook
does nothing without it. The marker is removed at `SessionEnd`, refreshed by
follow-up prompts, and ignored after 24 hours without a prompt (a crashed
session never reaches `SessionEnd`).

### Fail open globally, closed inside a run

A global hook that fails closed on malformed input would block every Agent
call in every session. So the plugin hook allows malformed input with a
warning, and the skill's own hook (active only in a session that ran the
skill) blocks it. Without jq or Python, keys are matched as text: clear
violations are blocked, anything uncertain is allowed with a warning.

### A receipt, not a savings claim

v0.4's report re-priced its own pipeline against an imagined baseline and
called the difference savings. `tokens.py` now prices only what the
transcript recorded, per exact model id, and says it's an API list-price
estimate, not a bill. A row in `prices.json` is `verified` only after it
reproduced Claude Code's own cost on a recorded session; other rows are
printed as estimates.

## History, with the measurements behind each change

### v0.4: a fixed pipeline

An Opus planner wrote cards with code in them, cheaper models built them, an
Opus reviewer checked every run. The author reported one real task costing
about 8× more and taking about 20× longer than doing it directly. That run
predates this repository's benchmarks; no transcript of it is included here.

### v0.5: the main session does everything

No planner, no cards, no handoff. Review scaled by risk. Fast, but nothing
was delegated, so cheaper models saved nothing.

### v0.6: delegation with briefs

Measured once on a small task (Claude Code 2.1.274, `opus` = `claude-opus-5`,
one run per arm):

| | Plain | v0.6 |
|---|---|---|
| Cost | $0.61 | $1.49 |
| Wall time | 39 s | 245 s |
| Turns | 7 | 19 |
| Hidden tests | 9/9 | 9/9 |

Opus orchestrator $1.17, Opus reviewer $0.25, Sonnet implementer $0.07.
Orchestration overhead cost dollars; delegation saved cents. The plain arm
had the plugin's hook active, and two of the skill's commands were blocked.

### v0.7: overhead cut

Small tasks inline with no reference reads, triage by blast radius, the
edge-input line, one-command steps. Same task, rerun:

| | Plain | v0.7 |
|---|---|---|
| Cost | $0.39 | $0.59 |
| Wall time | 42 s | 87 s |
| Turns | 7 | 10 |
| Skill text loaded | — | 8,669 bytes |
| Hidden tests | 9/9 | 9/9 |
| Missing or text coupon value | NaN | clear error |

The plain arm alone moved from $0.61 to $0.39 between rounds, so single runs
are noisy. A turn-by-turn audit of this run is in
[2026-10-22-turn-audit.md](../benchmarks/2026-10-22-turn-audit.md).

### v0.9: adaptive routing

v0.8 reviewed every change at Opus · low, a colour tweak included, and
planned every task. v0.9 routes by track and tier: tiny code changes and
ordinary non-coding work skip the plan, the approval wait and the reviewer;
CRITICAL work keeps all three at any size. The policy moved from prose into
`scripts/route.py`, so its decisions are unit-tested (tests/test_route.py); the
facts it receives are still the model's judgement, which only live route runs
measure (benchmarks/v0.9/routing-cases.md). `/sharaqi review [target]` is an
explicit, read-only review of code or a document.

### v0.7.1: gaps closed, a medium task measured

Marker hardening, the text fallback's failure mode, verified price rows, two
audit-driven SKILL.md changes, and the first medium-task benchmark
([RESULTS.md](../benchmarks/medium-task/RESULTS.md)): a rename plus a
feature across 12 files of a small library, pre-registered, three runs per
arm.

| Median (range) | Plain | v0.7.1 |
|---|---|---|
| Cost | $0.97 ($0.92–0.99) | $1.71 ($1.40–1.84) |
| Wall time | 156 s (147–159) | 296 s (208–314) |
| Hidden tests | 16/16 in every run | 16/16 in every run |
| Edge probe | 8/8 in every run | 8/8 in every run |

The skill triaged STANDARD every time and kept the work inline: its
break-even rule judged a brief dearer than editing files it had already read.
So delegation was never exercised, and the overhead was the orchestrator's
extra turns and prose, plus a Sonnet reviewer in two runs that found nothing.
On this task, unlike the cart task, plain Opus also handled every edge input.

What this leaves open: whether delegation pays on a task large enough to
cross the break-even. Candidate changes the runs suggest are listed, not
applied, under "Next version" in RESULTS.md.
