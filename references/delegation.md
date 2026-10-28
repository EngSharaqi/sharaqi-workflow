# Delegation — rungs, agent files, slices, escalation

You (Opus) decide, diagnose, brief and verify. Cheaper rungs read, edit and
run checks. The card in SKILL.md step 1 picks the rung; this file says how to
call it and when it pays.

## Rung → call

The roles and their model and effort are `docs/model-effort-plan.md` §5; this
table maps them to calls. Effort comes from the agent file: pick the file for
the effort and pass the model. On Claude Code 2.1.312 the `haiku` alias
resolves to `claude-haiku-5-5` and its effort applies (§4); on 2.1.274 it was
Haiku 4.5 with no effort setting. What a subagent actually ran is in its
transcript: `message.model` and `effort` on each assistant entry (2.1.311
records both). Report those, not the table below.

| Role · rung | `subagent_type` | `model` | Effort (configured) |
|---|---|---|---|
| R2 Mechanic · `haiku-medium` | `implementer` | `haiku` | medium |
| R3 Builder · `haiku-high` | `implementer-high` | `haiku` | high |
| R5 Consultant · `opus-low` (a question, no implementation) | `implementer-low` | `opus` | low |
| R4 Specialist · `sonnet-high` | `implementer-high` | `sonnet` | high |
| R6 Expert · `opus-medium` | `implementer` | `opus` | medium |
| R6+ · `opus-high` | `implementer-high` | `opus` | high, only with the reason in the `▶` line |
| plan-agent (CRITICAL) | `planner` | `opus` | high (read-only) |
| R7 Reviewer, `planned` routes that changed files; `/sharaqi review` | `reviewer` | `opus` | low |
| R7+ Critical reviewer, `critical` routes | `reviewer-medium` | `opus` | medium |
| R7+ for auth/secrets/parsing | `reviewer-high` | `opus` | high |
| R8 Writer, a `direct` (non-coding) route past break-even | `implementer-low` | `haiku` | low; wording-sensitive Arabic text goes to R3 |
| Ops `haiku-low`, an `ops` route with `delegable=yes` past break-even | `implementer-low` | `haiku` | low. Commit, push, Azure DevOps and web ops are `delegable=no`: the implementer has no git write, Web or MCP tool |
| Ops `haiku-medium` | `implementer` | `haiku` | medium |
| Ops `haiku-high` | `implementer-high` | `haiku` | high |
| Ops `sonnet-high` | `implementer-high` | `sonnet` | high |

Shown with the plugin prefix (`sharaqi:implementer`). Don't pass `effort`;
if your Agent tool has the parameter and you pass it, it overrides the file
and the hook checks it. The hook blocks a call whose model and effort (from
the call, else the file) exceed the ceiling, for example any model with
`effort: xhigh`. If a session refuses the planned effort (an older installed
copy with a lower ceiling), use the next supported rung and say so in the `▶`
line; never work around the hook.

## Choosing the rung

Name the role a careful engineer would pick, then apply cheapest-first: one
rung lower when tests or another clear check will catch a miss, one higher
when nothing checks it and the logic is non-trivial (§6 rule 13). Ladder
(§5):

```
inline → haiku-medium (R2) → haiku-high (R3) → [opus-low (R5): knowledge only]
       → sonnet-high (R4) → opus-medium (R6) → opus-high (R6+)
```

Never go from `haiku-high` to Sonnet at medium or below: same capability,
five times the price. The next real rung is `sonnet-high`.

| Rung | Task shapes |
|---|---|
| `inline` | a typo, a label, a one-line known fix, a config value: one read and one edit |
| `haiku-medium` | rename a symbol across files; the same edit in many places; boilerplate on an existing example (stories, fixtures, translations of keys); config; scaffolding |
| `haiku-high` | a normal feature or a bug with a known cause **when tests or a typecheck catch a miss**; tests shaped like their neighbours |
| `opus-low` | one question that needs knowledge, not effort (which library, does this API do X); an answer, no implementation |
| `sonnet-high` | tricky logic (dates, concurrency, state, parsing), many interacting files, an unclear failure with a bounded search space, or non-trivial logic with no tests |
| `opus-medium` | judgement a brief can't pin down, after you narrowed it; large enough to pay for a fresh Opus context (below) |
| `opus-high` | as above when the reasoning is long or subtle, or the change is irreversible; state why |

Diagnosis stays with you when the search space is unbounded: find the cause
(delegate a broad search to `Explore` · `haiku` if needed), then brief the fix
with the cause in `facts`.

## Break-even: when delegating pays

`scripts/breakeven.py` computes it from `scripts/prices.json` and the usage
of a recorded delegated session (formula in docs/architecture.md). A *work
turn* is one read, edit or check run. With an Opus orchestrator, a delegated
slice pays for its brief, two extra orchestrator turns, the subagent's start
and the diff you read back once it needs more than about:

| Target | Break-even, work turns (brief 400–1600 tokens) |
|---|---|
| `haiku-*` | about 3 (2.5–3.2) |
| `sonnet-high` | about 4 (3.2–4.0) |
| `opus-*` (fresh context) | 7 or more (6.9–8.2) |

Heuristics derived from that, using a measured plain run (v0.7.1 medium
benchmark: about 250 changed lines, 12 files, 32 turns, so about 2.5–3 work
turns per file and about 8 changed lines per turn): keep it `inline` when it
is one file and under about 30 changed lines; delegate to haiku or sonnet from
about two files, about 30 changed lines, or any edit-test loop; an `opus-*`
slice needs about three files or 60 lines or more, otherwise do it inline,
which is the same model without the fixed cost. The model assumes the rung needs no
more turns than you would; rework is not in it, which is why the rung must be
able to get it right the first time.

## Slices

- **Independent → parallel.** Parallel slices must each pass their own checks
  without the other slices' changes, because they run at the same time. A
  change everything imports (a renamed field of the core type) is one slice;
  separate modules with their own tests can be split.
- **Disjoint files → parallel.** Slices that write disjoint files and don't
  need each other's result go out as several Agent calls in one message. List
  each slice's files in its brief under `Touch`; two slices never write the
  same file.
- **Overlapping files → one slice**, or slices in sequence when they need
  different rungs. A second sequential slice adds a second fixed cost, so
  merge when the smaller part is below the break-even.
- Before sending: every path appears in at most one `Touch` list. Shared
  files (an index that re-exports, a common test helper) go to one slice, and
  the other briefs list them under `Leave`.
- Run the checks once after all slices return, then search for leftovers of
  what changed (old names, removed calls). `tokens.py --phases` prints
  `WRITE_CONFLICTS` when two subagents edited the same file; it should be 0.
- More than three slices: keep each one's status (agent, rung, verified) in
  your messages, not in a file.

## Escalation

- `BLOCKED` on a wrong premise: fix the brief, resend at the same rung.
- Wrong or incomplete: a delta to the same agent (`SendMessage`), at most
  twice.
- Still wrong after two deltas: diagnose first. If it lacked effort (it
  didn't try, skipped a step), a corrected brief at the same rung; if it
  lacked capability (it didn't know), a new implementer exactly one rung up
  the ladder with a corrected brief. One escalation per slice; after that, ask
  the user. Never move down a rung mid-task; never cross the ceiling to get
  past a failure.
- Every delta and escalation gets a `▶` line and appears in the report.
