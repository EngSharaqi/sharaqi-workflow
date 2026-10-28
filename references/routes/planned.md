## Route: planned
1. Read only what you will edit or must diagnose; size the rest with `wc -l`/grep. A Read
   that changes a fact: re-run `python3 -I "${SKILL}/scripts/route.py" --track <t> <facts>`
   (borderline facts: `${SKILL}/references/triage.md`).
2. Print the plan, ≤ 8 lines, no code, then stop and wait:
   `<ROUTE>` · Task · Acceptance · Edge inputs (or "none — why") · Parts: <part> → <executor>
   · <files> · then "Approve with `/sharaqi go`".
3. After `/sharaqi go`: implement inline, or delegate per the delegation rules. Add a test per
   edge input when the repo has tests.
4. Verify in one command: `AFTER=$(bash "${SKILL}/scripts/snapshot.sh"); git diff --stat
   <BASE> $AFTER; <checks>; git diff <BASE> $AFTER | head -400`. Empty AFTER: scope not
   isolated, say so.
5. Diff not empty: the ROUTE's reviewer gets that diff only. Confirmed findings: repair
   (inline when ≤ 2 edits), re-run the checks, re-review the repair diff; at most two repairs.
   Checks still failing after two: re-route with `--failed 2` (Opus implements).
   Reviewer call blocked by the context gate: don't retry or work around it; report
   `review: UNREVIEWED (context gate)` and, under Waiting for you, the command for a new
   session: `/sharaqi review <BASE>..<AFTER>` (+ the CRITICAL trigger word, if any).
6. Report:
**Changed:** <file — what> · **Checks:** <command → result as observed>
**Route:** <ROUTE> · review: PASS | FINDINGS open <n> | UNREVIEWED · escalations: none | <trigger → model>
**Risks:** <unverified or assumed, or "none identified"> · **Waiting for you:** <commit/push, if any>
