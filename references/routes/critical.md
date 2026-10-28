## Route: critical
Everything in a planned route, plus:
- Read `${SKILL}/references/security-checklist.md` before planning. The plan names the
  trigger, what could break, and the rollback.
- `plan=planner·opus·high`: get the plan from the planner (read-only) and show it; else you
  write it. Approval is required at any size, even inline.
- Checks: tests of the changed behaviour plus negative cases (denied role, bad input).
- Review: always, by the ROUTE's Opus reviewer, with the checklist path in its prompt.
  Show the user any blocker security finding before fixing it.
- Never remove a check, gate, approval step or test to make the task pass.
