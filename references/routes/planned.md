## Route: planned
1. Read only what you will edit or must diagnose; size the rest with `wc -l`/grep. A Read
   that changes a fact: re-run `python3 -I "${SKILL}/scripts/route.py" --track <t> <facts>
   --session <SESSION>` (borderline facts: `${SKILL}/references/triage.md`). The hook
   follows the latest route: an Agent call the ROUTE doesn't allow is blocked.
2. Print the plan, ≤ 8 lines, no code: `<ROUTE>` · Task · Acceptance · Edge inputs (or
   "none — why") · Decisions (spec gaps and what you chose) · Parts: <part> → <executor> ·
   <files>. `approval=yes`: stop and end with "Approve with `/sharaqi go`". `approval=no`:
   continue in the same turn.
3. Implement inline, or delegate per the delegation rules. Spec gaps: decide, test each
   decision, report it; ask only when a wrong guess can't be undone. Tests: one per
   acceptance criterion and edge input; rules on one code path share a test.
4. Verify in one command: `AFTER=$(bash "${SKILL}/scripts/snapshot.sh"); git diff --stat
   <BASE> $AFTER; <checks>; git diff <BASE> $AFTER | head -400`. Empty AFTER: scope not
   isolated, say so.
5. `review=none`: check the diff yourself against each acceptance criterion and edge input;
   fix what's missing. Checks failing after two repairs: re-route with `--failed 2`.
6. Report:
**Changed:** <file — what> · **Checks:** <command → result as observed>
**Decisions:** <spec gaps decided → the test that pins each, or "none">
**Route:** <ROUTE> · review: self | PASS | FINDINGS open <n> | UNREVIEWED · escalations: none | <trigger → model>
**Risks:** <unverified or assumed, or "none identified"> · **Waiting for you:** <commit/push, if any>
