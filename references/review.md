# Review — post-diff scan, and when to bring in a reviewer

## Post-diff scan (every mode)

Read the full diff, including untracked files. Small diffs too. For each point
below, check it or mark it n/a:

- **Scope:** every hunk serves the task. No unrelated refactor, formatting
  churn, or business-logic change in a UI-only task.
- **Unintended behaviour change:** callers of anything you changed (search
  for usages of changed functions, props, types, routes, query keys), and
  defaults and edge cases (empty, null, error, loading).
- **Authorization and data exposure:** no check removed or bypassed; no new
  data in responses, logs, URLs or client storage beyond what's needed.
- **Dependencies and config:** no new package, lockfile churn, env or build
  change that wasn't asked for.
- **Leftovers:** debug output, commented-out code, TODOs you added.
- **Repo standards:** the repo's `CLAUDE.md` and lint rules; translations
  for every locale the repo maintains, if it has i18n.

Any finding: fix it, then re-run the checks it affects. If the scan turns up
a CRITICAL trigger or a higher risk factor (triage.md), raise the mode now and
do what the new mode requires.

## Independent reviewer

The `reviewer` agent in this skill (it appears as `sharaqi:reviewer`) is
read-only: it reads the diff, runs read-only checks, and returns findings.
It costs a fresh context, so use it only when it buys something the
self-review can't.

| Mode | Reviewer |
|---|---|
| FAST | never |
| STANDARD | only when at least one holds, with the reason stated: the changed behaviour has semantic risk that your checks don't exercise; wide coupling or blast radius; after self-review you are still unsure the change is correct; the user asked for a review |
| CRITICAL | always |

Model and effort: `opus` / `medium`. Use `opus` / `high` only in CRITICAL with
a large or intricate diff (concurrency, state machines, multi-step
calculations, auth flows). Never above `high`.

Prompt it with paths and facts, not pasted code:

```
Repo: <root>   Base ref: <sha>   Mode: <mode>
Task: <one line>
Acceptance criteria: <list>
Checks already run: <command → result>
Focus: <the risk that justified this review>
Security checklist: <path to security-checklist.md> (CRITICAL only)
```

Handling the result:
- `PASS`: record it in the report.
- `FINDINGS`: you fix them in this session, then re-run the affected checks.
  Show the user any blocker-severity security finding before you fix it.
  Re-review only if a fix was itself non-trivial: at most once in STANDARD,
  twice in CRITICAL. If findings are still open after that, the user decides.
- No verdict (empty, cut off, error): spawn it once more. If that also fails,
  report that the review did not complete. Don't count it as passed.
