# Delegation — who does each part, on which model and effort

You (Opus, the orchestrator) think: size the task, diagnose, plan when needed,
write briefs, read diffs. Cheaper models do the typing: reading files,
editing, running checks. The many tool turns are where tokens go, and on Opus
each turn re-reads a large context. That is what delegation saves, and only
when the brief is short and the work is more than a few tool calls.

## The rule: cheapest that gets it right the first time

Pick the lowest rung that will do the job correctly in one pass. A failed
attempt plus rework costs more than starting one rung higher.

| Rung | Use for |
|---|---|
| **inline** (you, no subagent) | you already know the exact edit and it's about 3 tool calls or fewer: a colour, a font size, a string, a one-line fix in a file you've read. Starting a subagent costs more than the edit |
| `implementer` · `haiku` · `low` | mechanical work on a pattern the repo already shows: renames, translation keys, boilerplate, a test shaped like its neighbours, moving code without changing it |
| `implementer` · `haiku` · `medium` | the same, across several files, or with small choices (which existing helper fits) |
| `implementer` · `sonnet` · `low` | a clear, well-specified change in one area that needs reading the surrounding code |
| `implementer` · `sonnet` · `medium` | the default for real feature and bug work: several files, decisions within a clear brief, new tests |
| `implementer` · `opus` · `medium` | only a slice that needs judgement a brief can't pin down (intricate state, concurrency, a tricky algorithm), after the plan has narrowed it |

Other agents:

| Job | Agent · model · effort |
|---|---|
| Broad search: many files or naming conventions, and you only need the conclusion | `Explore` · `haiku` · `low`; `sonnet` · `medium` when the search needs judgement |
| A plan that is genuinely hard (open design across modules, migration strategy) and you'd otherwise guess | `Plan` · `opus` · `high`. The only use of `high` outside a CRITICAL review. Say why |
| Independent review | `reviewer`, model and effort from review.md |

Diagnosis stays with you: when a bug's cause is unclear, find the cause
first (delegate the broad search if there is one), then delegate the fix with
the cause in `<facts>`.

## Ceiling — never crossed

- Never `fable`, in any call, for any reason.
- Never above `opus` · `high`. `high` only for `Plan` as above, or the
  CRITICAL reviewer case in review.md.
- `sonnet` and `haiku` never above `medium`.
- Every Agent call names `model` and `effort`. A call without `model`
  inherits this session's model. While `/sharaqi` is active, a hook blocks it.

## Announce every delegation

Before each Agent call, one line:

```
▶ <agent> · <model> · effort <effort> — <why this rung>
```

When it returns, one line:

```
◀ <agent> · <model> · effort <effort> — <DONE|PARTIAL|BLOCKED>, <what it changed or found>
```

Rework (`SendMessage` to the same agent) gets its own `▶` line, marked
`rework`. Every delegation appears in the final report.

## Escalation

- Implementer returns `BLOCKED` on a wrong premise: fix the brief and resend.
- Wrong or incomplete work: send a delta to the same agent, at most twice.
  Still wrong: if the remaining fix is small, do it inline; otherwise start a
  new implementer one rung higher with a corrected brief. Never retry the
  same rung a third time.
- Never raise a rung above the ceiling to get past a failure. Ask the user.

## Several slices

- Run slices **one at a time** in dependency order, and check each before the
  next. A later brief can then rely on what the earlier one landed.
- Run slices in parallel (several Agent calls in one message) only when they
  touch disjoint files and none needs another's result. Run the checks once,
  after all of them return.
- More than three slices: keep a short progress file in the session's scratch
  or temp directory (outside the repo): each slice, its agent and rung, its
  status, what you verified. Update it as each slice lands.
- After the last slice, run the checks on the whole change once more and
  search for leftovers of what the plan changed (old names, removed calls).
