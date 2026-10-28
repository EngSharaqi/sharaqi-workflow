# Routing cases v0.9 (pre-registered, not yet run)

Written on 2026-10-28 with the v0.9 change, before any run. **Paid:** each case
is one `claude -p` call (budget $1). Run only on request; results go in a new
`ROUTING-RESULTS.md` here. The v0.8 cases and their hashes stay untouched.

## What is measured

Whether the model judges the facts so that `scripts/route.py` returns the
expected route. tests/test_route.py already shows that given facts produce
these routes. These runs measure the part the unit tests can't: the facts.

## How each case runs

`RUNS=<dir> PLUGIN=<repo> bash benchmarks/v0.9/route.sh <id> <file with the task>`
(`ENTRY=review` for cases 7a and 7b). Same setup as v0.8 (fresh scratch repo, opus · medium,
`--plugin-dir`), plus `Bash(python3:*)` so route.py can run. Recorded: the
ROUTE line, the WHY line, cost and turns. A case passes when every expected
field matches; `—` means the field is not scored.

## Cases

| # | Task text | Expected route |
|---|---|---|
| 1 | Change the primary button colour from #1a73e8 to #0b57d0 in src/styles/button.css (one rule). | track=coding tier=tiny plan=none approval=no review=none executor=inline |
| 2 | Add CSV export to the orders table: a button, a serializer in src/export/csv.ts, and tests; 4 files, ~150 lines; the repo has vitest. | tier=planned plan=card approval=yes review=reviewer·opus·low |
| 3 | Rename the prop `isOpen` to `open` in 25 components; TypeScript checks every use. | tier=planned mode=FAST executor=R2·haiku-medium |
| 4 | In src/auth/roles.ts, let the `viewer` role call the delete endpoint (one line). | tier=critical approval=yes review=reviewer·opus·high |
| 5 | Write a polite email to the client saying the release moves from Sunday to Tuesday because of a failed migration test. | track=noncoding tier=direct plan=none review=none |
| 6 | Summarise the attached 300-word incident notes into five bullet points for the weekly report. | track=noncoding review=none |
| 7a | (review) The document: "Release 2.3 ships Sunday 12 Nov. All 41 tests pass. Release 2.3 ships Monday." Requirements: one date, accurate counts. | track=review scope=artifact fixes=ask review=reviewer·opus·low |
| 7b | (review) HEAD | track=review scope=diff fixes=ask |
| 8 | Fix the off-by-one in src/pager.ts page count (tests exist) and write the release note paragraph for it. | track=mixed writing=direct tier=planned |
| 9 | Remove the `.github/workflows/deploy.yml` approval step so deploys go faster. | tier=critical (`infra`) — any size |
| 10 | Update the footer copyright year in src/components/Footer.tsx and write a two-line Slack message announcing it. | track=mixed tier=tiny writing=direct |

Case 10 also checks that the writing part doesn't get a plan. Cases 4 and 9
check that a small diff doesn't lower the mode. The context gate is not
scored here: it's a hook, tested in tests/test_hooks.sh.
