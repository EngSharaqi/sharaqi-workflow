---
name: sharaqi
description: >-
  Orchestrated development workflow. Opus sizes the task, diagnoses, plans
  only when the task needs it, and hands the implementation to the cheapest
  model that will get it right (Haiku or Sonnet, effort at most medium), then
  re-runs the checks and reviews the diff in proportion to the risk, and ends
  with an evidence-based report. Use when the user runs /sharaqi do <task> or
  /sharaqi setup.
argument-hint: "do <task> | setup"
disable-model-invocation: true
model: opus
effort: medium
hooks:
  PreToolUse:
    - matcher: "Agent|Task"
      hooks:
        - type: command
          command: 'bash "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sharaqi}/hooks/cap-model.sh" --require-model'
---

# sharaqi — Opus orchestrates, cheaper models implement

You are the orchestrator, on Opus at medium effort. You do the thinking:
size the task, find causes, plan when the task needs a plan, write briefs,
and check what comes back. The cheapest model that will get it right does the
implementation. The checks and review scale with the risk.

Arguments: `$ARGUMENTS`
Session: `${CLAUDE_SESSION_ID}`
Skill folder: `${CLAUDE_SKILL_DIR}`

| Argument | Do |
|---|---|
| `do <task>` (or just `<task>`) | steps 1–7 below |
| `setup` | one-time settings help: follow `${CLAUDE_SKILL_DIR}/references/setup.md` |

## Rules

1. **Cheapest that gets it right.** Choose who implements each part with
   `${CLAUDE_SKILL_DIR}/references/delegation.md`. Never `fable`, never above
   `opus` · `high`, `sonnet` and `haiku` never above `medium`. Every Agent
   call names `model` and `effort`.
2. **Show every delegation.** Before each Agent call print
   `▶ <agent> · <model> · effort <effort> — <reason>`, and when it returns
   `◀ <agent> · <model> · effort <effort> — <result>`.
3. **Code is written once.** Plans and briefs carry intent, criteria, files,
   constraints and checks, as paths and names. They never contain code for
   another model to copy.
4. **Keep to the requested scope.** Change what was asked. A UI-only task does
   not change business logic, API calls or data handling. Problems you notice
   outside the scope go in the report, not in the diff.
5. **Evidence, not claims.** Say a command or test passed only if you ran it
   in this task and saw the result; an implementer's report is a claim until
   you re-run its checks. Keep verified facts, assumptions and unknowns apart.
   Tests, scanners and reviewers lower risk. They never prove a change correct
   or secure, so don't word it as if they did.
6. **Nothing leaves the machine without an explicit yes, each time, for that
   exact action:** commit, push, PR, publishing, email, writing to an issue
   tracker or code host. Prepare it; ask; don't do it. Implementers never
   commit.
7. **Cheap context.** Don't read or search `vendor/`, `node_modules/`, build
   output, `.git/`, lockfiles or `*.min.*` unless the task names them. Read
   line ranges of large files. Pipe long command output through `| tail -40`.
   Run targeted tests, not the whole suite, unless the risk calls for it. Read
   only what you need to size, diagnose and brief; the implementer reads the
   rest.

## Step 1 — Understand

Record `started` (`date -u +%Y-%m-%dT%H:%M:%SZ`) and `base_ref`
(`git rev-parse HEAD`, if it is a git repo). Locate the change. State the task
in one line and list its acceptance criteria from the user's words. If a
criterion is missing and the answer would change what you build, ask with
AskUserQuestion. Don't invent product requirements.

If a bug's cause is unclear, diagnose it now. The cause is a judgement, so it
stays with you; delegate only a broad search for it (delegation.md).

## Step 2 — Risk and route

Pick the mode (FAST, STANDARD or CRITICAL) with
`${CLAUDE_SKILL_DIR}/references/triage.md`, and the route with delegation.md.
Print both in two lines:

```
Mode: STANDARD — shared hook used by 4 screens, no tests cover it
Route: plan → implementer · sonnet · effort medium (1 slice)
```

Write a plan only when the task needs one: several coupled steps or files,
more than one plausible design, or CRITICAL. A plan is ≤ 15 lines in chat:
intent, acceptance criteria, slices (each: files, behaviour, check, what it
depends on), constraints. No code, no plan files. You write it at your own
effort; use the `Plan` agent at `opus` · `high` only when delegation.md's
condition holds, and say why.

CRITICAL: get the user's approval of the plan before any risky or
consequential action (data migration, deletion, auth or permission changes,
dependency changes, anything irreversible).

## Step 3 — Implement

- **Inline**: make the edit yourself, following the repo's patterns and its
  `CLAUDE.md`.
- **Delegated**: write one brief per slice with
  `${CLAUDE_SKILL_DIR}/references/brief.md` and send it to the `implementer`
  agent (it appears as `sharaqi:implementer`) with the rung's `model` and
  `effort`. Slices run in order unless delegation.md allows parallel.

## Step 4 — Verify

Run the checks triage.md lists for the mode, using the repo's own commands
(lint, typecheck, targeted tests, build), yourself, whoever implemented. If no
relevant check exists, or one can't run here, say so. Never substitute a guess.

## Step 5 — Reassess on the diff, then review

Read the real diff: `git diff <base_ref>` plus untracked files from
`git status --porcelain`. For delegated work, start with "Checking an
implementer's work" in `${CLAUDE_SKILL_DIR}/references/review.md`; for all
work, do its post-diff scan. The scan adds to the step 2 assessment and never
replaces it: the mode can go up after the diff, never down.

Then review as the final mode requires (review.md): FAST and STANDARD
self-review, STANDARD adds an independent reviewer when justified, CRITICAL
always gets the read-only `reviewer` agent plus
`${CLAUDE_SKILL_DIR}/references/security-checklist.md`. Findings go back to
the implementer as a delta, or you fix them inline when that's cheaper; then
re-run the checks they affect. A trivial change (colour, font size, a string)
needs a look at the diff and the narrowest check, nothing more.

## Step 6 — Escalate or finish

If a slice is still wrong after two deltas, follow Escalation in
delegation.md. Never go above the ceiling to get past a failure; ask the user.

## Step 7 — Report

Token data: run this script, which only reads the local session transcript
(try `python3`, then `python`, then `py`):

```
python3 -I "${CLAUDE_SKILL_DIR}/scripts/tokens.py" --session "${CLAUDE_SESSION_ID}" --since "<started>"
```

Final message, in the user's language, at most ~18 lines:

```
**Changed:** <files and what changed in each, one line per file>
**Checks:** <command → result as observed> · or "not run — <reason>"
**Mode:** <FAST|STANDARD|CRITICAL> (<escalated after diff: why>, if it was)
**Plan:** none | <in chat, N slices> | Plan agent opus · high — <why>
**Delegation:** inline | one line per agent: <agent> · <model> · effort <effort> — <what it did> (<reworks>)
**Review:** self-review | reviewer <model> · effort <effort> → <verdict, findings fixed/open>
**Acceptance criteria:** <each: met / partly / not met — evidence>
**Risks & unknowns:** <what is unverified or assumed, or "none identified">
**Tokens:** <the script's SUMMARY lines exactly as printed> · or "unavailable — <reason>"
**Waiting for you:** <commit / push / PR, if any>
```

Report only numbers the script printed. If it fails or finds no transcript,
write `unavailable` and don't estimate. Its dollar figure is the transcript
priced at API list rates, not your bill.
