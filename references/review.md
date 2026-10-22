# Review — checking delegated work, post-diff scan, and the reviewer

## Checking an implementer's work

An implementer's `DONE` and its check results are claims. Before accepting:

1. **Tests first.** If the diff touches existing tests, read those hunks
   before trusting any green run. A weakened assertion, an added skip or a
   deleted test shrinks what the checks measure. Unbriefed test edits are a
   finding.
2. **Re-run the checks yourself**: the brief's commands, in the working tree.
3. **Read the diff against the brief**: scope creep, scope shortfall, and
   judgement calls it made that you need to understand and accept or reject.
4. **Implementer sweep**: generated code fails in ways green checks can't
   see. Look for:
   - hardcoded success or fixture data on a path that should do real work;
   - catch-all error handling that returns a default instead of failing;
   - imports, methods or signatures that don't exist in the installed
     version;
   - a second way to do what the file already does (new client, error idiom,
     logging style);
   - speculative surface: parameters, flags or abstractions with no caller;
   - guards for cases the code's own contract already excludes;
   - dead weight: unused imports, unreachable branches, comments restating
     the line below;
   - tests that assert internals or mock the project's own functions.

Then the post-diff scan below. Depth scales with the change: a colour or
font-size change from a `haiku` implementer needs a look at the diff and the
narrowest check, not the sweep.

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

Any finding: send it back to the implementer as a delta (brief.md, Rework),
or fix it inline when that's cheaper, then re-run the checks it affects. If the scan turns up
a CRITICAL trigger or a higher risk factor (triage.md), raise the mode now and
do what the new mode requires.

## Independent reviewer

The `reviewer` agent in this skill (it appears as `sharaqi:reviewer`) is
read-only: its only tools are Read, Grep and Glob, so it can't run commands
or change files. It reads a diff file you write, and returns findings. It
costs a fresh context, so use it only when it buys something the self-review
can't.

| Mode | Reviewer |
|---|---|
| FAST | never |
| STANDARD | only when at least one holds, with the reason stated: the changed behaviour has semantic risk that your checks don't exercise; wide coupling or blast radius; after self-review you are still unsure the change is correct; the user asked for a review |
| CRITICAL | always |

Model and effort:

| Mode | Reviewer model · effort |
|---|---|
| STANDARD | `sonnet` · `medium` — you have already read the diff; this is a second, independent pass |
| CRITICAL | `opus` · `medium`; `opus` · `high` only for a large or intricate diff (concurrency, state machines, multi-step calculations, auth flows) |

Never above `opus` · `high`. Announce it with the `▶`/`◀` lines in
delegation.md.

Pass `model` and `effort` explicitly in the Agent call, even though the agent
file sets them: the plugin's cap hook can only check values it can see.

First write the full diff, untracked files included, to a file outside the
repo:

```
d="${TMPDIR:-/tmp}/sharaqi-<session>.diff"
git diff <base_ref> > "$d"
git ls-files --others --exclude-standard -z | xargs -0 -I{} git diff --no-index /dev/null {} >> "$d"
```

(`git diff --no-index` exits 1 when files differ; that is expected.) Then
prompt it with paths and facts, not pasted code:

```
Repo: <root>   Diff: <path to the diff file>   Mode: <mode>
Task: <one line>
Acceptance criteria: <list>
Checks already run: <command → result>
Focus: <the risk that justified this review>
Security checklist: <path to security-checklist.md> (CRITICAL only)
```

Handling the result:
- `PASS`: record it in the report.
- `unverified` points: run the commands it names yourself if they are cheap
  and relevant, and report the result. Otherwise list them under risks.
- `FINDINGS`: send them to the implementer as a delta, or fix them inline
  when that's cheaper, then re-run the affected checks.
  Show the user any blocker-severity security finding before you fix it.
  Re-review only if a fix was itself non-trivial: at most once in STANDARD,
  twice in CRITICAL. Rewrite the diff file before each re-review. If findings
  are still open after that, the user decides.
- No verdict (empty, cut off, error): spawn it once more. If that also fails,
  report that the review did not complete. Don't count it as passed.
