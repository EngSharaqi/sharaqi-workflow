# Triage — when the table in SKILL.md step 1 isn't enough

The tracks, facts and tiers are in SKILL.md step 1; `scripts/route.py` turns
the facts into the route. This file is for facts the tables leave unclear.

The mode is about blast radius: what a mistake would break, for whom, and how
hard it is to undo. It is not about the words in the task. "Price", "cart" or
"money" in a pure calculation in small, scoped code is STANDARD; code that
charges a card, pays out or calls a payment system is CRITICAL.

Who implements is a separate choice (delegation.md): a CRITICAL one-line
permission fix can be done inline, and a FAST 40-file rename can go to
`haiku`. Size is a signal, not the measure.

## Risk factors

| Factor | Lower | Higher |
|---|---|---|
| Semantic risk | wording, styling, layout, isolated pure code | behaviour users or other code depend on; data shape; state, concurrency |
| Uncertainty | cause and fix are clear | unclear cause, several plausible designs, unfamiliar code |
| Coupling | one component or file, no shared callers | shared hooks, services, types, utilities, API contracts |
| Test coverage | tests or a type check exercise the changed behaviour | nothing automated checks it |
| Blast radius | one screen, easy to revert | many screens, users, tenants or stored data; external systems; hard to revert |

FAST: every factor is low. STANDARD: at least one is moderate or high and no
CRITICAL trigger applies. CRITICAL: a trigger from the SKILL.md table applies.

## Borderline cases

| Change | Mode | Why |
|---|---|---|
| Fix the discount math in a cart-total function | STANDARD | pure calculation, scoped, tests can pin it |
| Call the payment provider with the new total | CRITICAL | real-money side effect, external system |
| Rename a field the compiler checks everywhere | FAST | compiler covers every caller |
| Rename a field that is also stored or sent over an API | CRITICAL if stored data or a public contract changes, else STANDARD | data shape and external callers |
| Parse a date from a form field | STANDARD | input handling without a security sink |
| Parse an uploaded file, or build SQL / shell / HTML from input | CRITICAL | security-sensitive parsing |
| Change a shared utility with many callers | STANDARD; the reviewer is told to check the callers | coupling, not risk class |
| Change a button colour or a font size in one CSS file | `tiny` (FAST) | one file, no behaviour change; no plan, no reviewer |
| One-line fix of an off-by-one in a loop | STANDARD (`--behaviour yes`) | small, but behaviour changes: plan and reviewer |
| One-line change to a role check | CRITICAL (`auth`) | size never lowers the mode |
| Bump a dependency, change CI or deploy config | CRITICAL | widely shared infrastructure |

## Track borderlines

| Task | Track | Why |
|---|---|---|
| Draft an email or a report; summarise a thread | `noncoding` | nothing executable changes |
| Write a test plan; run the existing tests and report | `noncoding` | no code changes |
| Write the README section for a feature | `noncoding` | documentation text, not executable |
| Fix a bug and write the release note for it | `mixed` | the fix takes the code route; the note is written directly |
| Add a script that generates the monthly report | `coding` | the output is a script |
| Edit CI config or a dependency list "just as text" | `coding`, `--critical infra` | executable project config |

## When unsure

- `tiny` or not → not tiny (`--behaviour yes`). Tiny skips the plan and the
  reviewer, so it must be clearly true.
- `noncoding` or `mixed` → `mixed` when anything executable may change.
- STANDARD or CRITICAL → CRITICAL only if the doubt is whether a CRITICAL
  trigger applies. A domain word alone is not a trigger.
- Requirements unclear in a way that changes what you'd build → ask; don't
  pick a mode to cover the gap.
