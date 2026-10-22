# Triage — FAST, STANDARD or CRITICAL

Assess before editing (step 2) from what the task asks and what you've read so
far. Reassess on the actual diff (step 5): a new risk factor raises the mode,
nothing lowers it.

The mode is about risk. Who implements is a separate choice
(delegation.md): a CRITICAL one-line permission fix can be done inline, and a
FAST 40-file rename can go to `haiku`.

Size is a signal, not the measure. A one-line change to a permission check is
CRITICAL. A 300-line rename with full test coverage can be FAST.

## Risk factors

| Factor | Lower | Higher |
|---|---|---|
| Semantic risk | wording, styling, layout, isolated pure code | behaviour users or other code depend on; data shape; state, concurrency, calculations |
| Uncertainty | cause and fix are clear | unclear cause, several plausible designs, unfamiliar code |
| Coupling | one component or file, no shared callers | shared hooks, services, types, utilities, API contracts |
| Test coverage | tests or a type check exercise the changed behaviour | nothing automated checks it |
| Blast radius | one screen, easy to revert | many screens, users, tenants, or stored data; hard to revert |

## Modes

**FAST**: every factor is low. The task is clear and bounded, and a mistake
would be visible and cheap to undo. Typical: copy or translation change, a
style fix, a small fix whose cause is known, a rename the compiler checks.
- Verify: inspect the diff; run the narrowest relevant check if one exists
  (lint or typecheck of the touched files, one targeted test).
- Review: self-review only (review.md, post-diff scan).

**STANDARD**: the default for real feature and bug work: at least one factor
is moderate or high, and no CRITICAL trigger applies.
- Verify: targeted tests for the changed behaviour, plus lint, typecheck or
  build of the affected part. When the behaviour changes and the repo has test
  infrastructure, add or update a test.
- Review: self-review, plus an independent reviewer when review.md's
  criteria justify one. Say why you did or didn't use one.

**CRITICAL**: any trigger below applies.
- Authentication, authorization, roles, permissions, tenant isolation.
- Money, billing, pricing calculations.
- Data deletion, migrations, bulk updates, irreversible state changes.
- Secrets, credentials, tokens, encryption, session handling.
- Untrusted input reaching SQL, shell, HTML, file paths or deserialization.
- File upload or download.
- Adding, removing or upgrading a dependency; build, CI or deployment config.
- Production configuration or anything acting on a live system.

For CRITICAL:
- Verify: STANDARD checks, plus negative cases where feasible (unauthorized
  user, invalid input, other tenant's id).
- Review: the read-only `reviewer` agent is mandatory, and so is
  security-checklist.md.
- Approval: the user approves before any risky or consequential action, as in
  SKILL.md step 2.

## When unsure

- FAST or STANDARD → STANDARD. It costs little, because a reviewer still needs
  a reason.
- STANDARD or CRITICAL → CRITICAL if the doubt is whether the change touches a
  CRITICAL trigger. Otherwise STANDARD.
- Requirements unclear in a way that changes what you'd build → ask; don't pick
  a mode to cover the gap.
