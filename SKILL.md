---
name: sharaqi
description: >-
  Risk-scaled workflow for a development task, run in the main session. Assess
  risk before editing and again on the actual diff, pick FAST, STANDARD or
  CRITICAL, verify in proportion, bring in an independent read-only reviewer
  only when the risk justifies it, and finish with an evidence-based report.
  Delegates to subagents only when there is a concrete benefit. Use when the
  user runs /sharaqi do <task> or /sharaqi setup.
argument-hint: "do <task> | setup"
disable-model-invocation: true
---

# sharaqi — do the task, scale the checks to the risk

You do the work yourself, in this session. The skill adds three things and no
pipeline: a risk assessment before and after editing, review in proportion to
that risk, and an honest completion report.

Arguments: `$ARGUMENTS`
Session: `${CLAUDE_SESSION_ID}`
Skill folder: `${CLAUDE_SKILL_DIR}`

| Argument | Do |
|---|---|
| `do <task>` (or just `<task>`) | steps 1–6 below |
| `setup` | one-time settings help: follow `${CLAUDE_SKILL_DIR}/references/setup.md` |

## Rules

1. **Main session first.** No planner, PRD, task cards or builder handoffs.
   Spawn a subagent only for a reason listed in
   `${CLAUDE_SKILL_DIR}/references/delegation.md`, and say the reason in one
   line before spawning it.
2. **Keep to the requested scope.** Change what was asked. A UI-only task does
   not change business logic, API calls or data handling. Problems you notice
   outside the scope go in the report, not in the diff.
3. **Evidence, not claims.** Say a command or test passed only if you ran it in
   this task and saw the result. Keep verified facts, assumptions and unknowns
   apart. Tests, scanners and reviewers lower risk. They never prove a change
   correct or secure, so don't word it as if they did.
4. **Nothing leaves the machine without an explicit yes, each time, for that
   exact action:** commit, push, PR, publishing, email, writing to an issue
   tracker or code host. Prepare it; ask; don't do it. This rule is advice to
   you; `/sharaqi setup` can add permission rules that make Claude Code ask.
5. **Cheap context.** Don't read or search `vendor/`, `node_modules/`, build
   output, `.git/`, lockfiles or `*.min.*` unless the task names them. Read
   line ranges of large files. Pipe long command output through `| tail -40`.
   Run targeted tests, not the whole suite, unless the risk calls for it. Don't
   re-read a file whose content hasn't changed since you last read it. Use a
   browser or screenshots only when no cheaper check can verify a criterion.

## Step 1 — Understand

Record `started` (`date -u +%Y-%m-%dT%H:%M:%SZ`) and `base_ref`
(`git rev-parse HEAD`, if it is a git repo). Read only what you need to
locate the change. State the task in one line and list its acceptance criteria
from the user's words. If a criterion is missing and the answer would change
what you build, ask with AskUserQuestion. Don't invent product requirements.

## Step 2 — Assess risk before editing

Pick FAST, STANDARD or CRITICAL with
`${CLAUDE_SKILL_DIR}/references/triage.md`. Print one line, e.g.
`Mode: STANDARD — shared hook used by 4 screens, no tests cover it`.

- **FAST**: edit directly.
- **STANDARD**: if the work has more than a few steps, write a short plan in
  chat (≤ 10 lines: intent, acceptance criteria, files, constraints,
  verification). No plan files.
- **CRITICAL**: write that plan, and get the user's approval before any
  risky or consequential action (data migration, deletion, auth or permission
  changes, dependency changes, anything irreversible).

## Step 3 — Implement

Make the change in this session, following the repo's existing patterns and
its `CLAUDE.md`.

## Step 4 — Verify

Run the checks that triage.md lists for the mode, using the repo's own
commands (lint, typecheck, targeted tests, build). If no relevant check exists,
or one can't run here, say so. Never substitute a guess.

## Step 5 — Reassess on the actual diff, then review

Read the real diff: `git diff <base_ref>` plus untracked files from
`git status --porcelain`. Work through the post-diff scan in
`${CLAUDE_SKILL_DIR}/references/review.md`. It adds to the step 2 assessment
and never replaces it: the mode can go up after the diff, never down.

Then review as the final mode requires (review.md): FAST and STANDARD
self-review, STANDARD adds an independent reviewer when justified, CRITICAL
always gets the read-only `reviewer` agent plus
`${CLAUDE_SKILL_DIR}/references/security-checklist.md`. Fix the findings
yourself and re-run the checks they affect.

## Step 6 — Report

Token data: run this script, which only reads the local session transcript
(try `python3`, then `python`, then `py`):

```
python3 -I "${CLAUDE_SKILL_DIR}/scripts/tokens.py" --session "${CLAUDE_SESSION_ID}" --since "<started>"
```

Final message, in the user's language, at most ~15 lines:

```
**Changed:** <files and what changed in each, one line per file>
**Checks:** <command → result as observed> · or "not run — <reason>"
**Mode:** <FAST|STANDARD|CRITICAL> (<escalated after diff: why>, if it was)
**Review:** self-review | reviewer <model/effort> → <verdict, findings fixed/open>
**Delegation:** none | <agent model/effort — reason>
**Acceptance criteria:** <each: met / partly / not met — evidence>
**Risks & unknowns:** <what is unverified or assumed, or "none identified">
**Tokens:** <the script's SUMMARY lines exactly as printed> · or "unavailable — <reason>"
**Waiting for you:** <commit / push / PR, if any>
```

Report only numbers the script printed. If it fails or finds no transcript,
write `unavailable` and don't estimate. Its dollar figure is the transcript
priced at API list rates, not your bill.
