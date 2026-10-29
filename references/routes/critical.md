## Route: critical
Everything in a planned route, plus:
- Read `${SKILL}/references/security-checklist.md` before planning. The plan names the
  trigger, what could break, and the rollback.
- `plan=planner·opus·high`: get the plan from the planner (read-only) and show it; else you
  write it. Approval is required at any size, even inline.
- Checks: tests of the changed behaviour plus negative cases (denied role, bad input).
- Review (instead of step 5's self-check): the diff not empty, the ROUTE's Opus reviewer
  gets that diff only, with the checklist path in its prompt. Show the user any blocker
  security finding before fixing it. Confirmed findings: repair (inline when ≤ 2 edits),
  re-run the checks, re-review the repair diff; at most two repairs. Reviewer blocked by the
  context gate: don't retry or work around it; report `review: UNREVIEWED (context gate)`
  and, under Waiting for you, `/sharaqi review <BASE>..<AFTER> <trigger word>` for a new
  session.
- Never remove a check, gate, approval step or test to make the task pass.
