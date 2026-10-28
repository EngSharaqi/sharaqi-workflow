# Routing cases (pre-registered)

Written on 2026-10-25, before any v0.8 change to the skill, and pinned in
[HASHES.sha256](HASHES.sha256). Not edited after the first route run; results
go in [ROUTING-RESULTS.md](ROUTING-RESULTS.md).

## What is measured

Whether `/sharaqi route <task>` picks a plan decision and an executor rung a
careful engineer would accept. It measures the routing card only; nothing is
executed.

## How each case runs

- One run per case: `/sharaqi:sharaqi route ` + the case's task text.
- `claude -p --model opus --effort medium`, the v0.8 plugin loaded with
  `--plugin-dir`, in a fresh empty git repository (one commit, a README that
  says "scratch repo"). The task text carries every fact the router needs;
  the files it names don't exist, so the router can't learn more by reading.
- Recorded: the card line(s) and the one-line reason, cost and turns.

## Vocabulary

Rungs: `inline`, `haiku`, `sonnet-low`, `sonnet-medium`, `sonnet-high`,
`opus-low`, `opus-medium`, `opus-high`. A card that names several slices is
scored on its highest rung. `ask` means the router stops to ask the user
before routing.

Plan: `none`, `chat`, `plan-agent`.

## Scoring (fixed now)

- **Executor match:** the card's executor rung is in the case's acceptable set.
- **Plan match:** the card's plan value is in the case's plan set.
- **Case match:** both. The headline number is case matches out of 16.
- Mode and review are recorded and scored separately (secondary), against
  the sets below.
- Misses are reported with the reason. Labels are not changed after a run.

## Cases

| # | Shape | Task text (sent verbatim after `route `) | Mode | Plan | Executor (acceptable) | Review |
|---|---|---|---|---|---|---|
| R1 | tiny known edit | Fix the typo "Recieve" → "Receive" in the submit button label in src/components/Footer.jsx. | FAST | none | inline | self |
| R2 | clear small bug, tests exist | formatDate in src/utils/date.js shows the month one too low because it uses getMonth() without adding 1. test/date.test.js covers formatDate (npm test). Fix it and add a test for December. | FAST, STANDARD | none | inline, haiku, sonnet-low | self |
| R3 | mechanical rename, 10 files | Rename the prop `isOpen` to `open` in the 10 components under src/components/modal/ (about 40 occurrences) and their call sites. TypeScript; npm run typecheck and npm test pass today. | FAST, STANDARD | none | haiku, sonnet-low | self |
| R4 | boilerplate on a pattern | Add a Storybook story for each of the 8 components in src/components/forms/, following the existing src/components/forms/Button.stories.jsx. | FAST | none | haiku, sonnet-low | self |
| R5 | translations, small | Add the 25 Arabic translations missing from src/i18n/locales/ar.json for keys that exist in src/i18n/locales/en.json. | FAST | none | inline, haiku | self |
| R6 | medium feature, clear spec | Add an optional `notes` field (string, max 500 chars) to tasks end to end: validation in src/task.js, create/update in src/api/tasks.js, a `notesContains` filter in src/query.js, the CSV column in src/csv.js, display in src/format.js, and tests in test/ (npm test). | STANDARD | none, chat | sonnet-low, sonnet-medium | self, reviewer-sonnet |
| R7 | medium feature, input parsing | Add pagination to GET /api/orders: `page` and `pageSize` query params (pageSize default 20, max 100) in src/routes/orders.js and src/services/orderService.js, with tests in test/orders.test.js (jest). | STANDARD | none | inline, sonnet-low, sonnet-medium | reviewer-sonnet |
| R8 | ambiguous request | Add caching to the product API, it's too slow. | STANDARD | chat | ask, sonnet-medium, sonnet-high, opus-medium | self, reviewer-sonnet |
| R9 | perf investigation, unbounded | The /reports page has taken about 8 seconds to load in production since last week. Find out why and fix it. | STANDARD | none, chat | inline, ask, sonnet-high, opus-medium | self, reviewer-sonnet |
| R10 | tricky logic, interacting files | Two concurrent checkout requests can both reserve the last unit in stock. The reservation logic spans src/services/inventory.js, src/services/checkout.js and src/db/transactions.js; test/checkout.concurrency.test.js reproduces it and fails today. Fix the race. | STANDARD, CRITICAL | chat, plan-agent | sonnet-high, opus-medium, opus-high | reviewer-sonnet, reviewer-opus |
| R11 | no-test legacy code | In legacy/report_export.php (1,200 lines, no tests anywhere in the repo) change the CSV export to use semicolons instead of commas as the separator, and quote fields that contain a semicolon. | STANDARD | none | inline, sonnet-low, sonnet-medium | reviewer-sonnet |
| R12 | auth change, tiny | Require the admin role on DELETE /api/users/:id in src/routes/users.js. The requireRole middleware in src/middleware/auth.js is already used on the other admin routes; test/users.test.js covers the routes. | CRITICAL | chat, plan-agent | inline, sonnet-low | reviewer-opus |
| R13 | data migration | Write a knex migration in db/migrations/ that splits users.full_name into first_name and last_name for existing rows (Postgres), with a down migration that restores full_name. | CRITICAL | chat, plan-agent | inline, sonnet-medium, sonnet-high, opus-medium | reviewer-opus |
| R14 | CI config, tiny | Add Node 22 to the test matrix in .github/workflows/ci.yml. | CRITICAL | chat, plan-agent | inline | reviewer-opus |
| R15 | security-sensitive parsing | Add POST /api/contacts/import that accepts an uploaded CSV (max 5 MB), validates each email and imports the contacts, in a new src/routes/import.js using the existing src/services/contacts.js; tests in test/ (npm test). | CRITICAL | chat, plan-agent | sonnet-medium, sonnet-high, opus-medium | reviewer-opus |
| R16 | large: mechanical plus logic | Replace moment with date-fns in the 14 files under src/ that import it, keeping every formatted output identical; npm test covers the date formatting. Then remove moment from package.json. | CRITICAL | chat, plan-agent | sonnet-low, sonnet-medium | reviewer-opus |

## Notes on the labels

- R12, R14: one-line changes in CRITICAL areas. The labels say the change is
  inline-sized while the mode still calls for a plan and an Opus reviewer.
- R13, R15, R16 accept several rungs because a reasonable engineer could
  split the work or keep it; the label rejects only rungs clearly too weak
  (`haiku` for judgement work) or clearly too costly (`opus-high` without a
  stated reason).
- R16: dependency removal is shared infrastructure (CRITICAL). The format
  token differences between moment and date-fns are a trap, so `haiku` alone
  is too weak and anything above `sonnet-medium` is more than the job needs.
  A card with a `haiku` slice for import swaps and a `sonnet` slice for the
  format conversion scores on its highest rung.
- R8, R9: asking first is an acceptable executor because the request leaves
  open what to build.
