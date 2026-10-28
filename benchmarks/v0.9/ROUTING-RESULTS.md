# Routing results v0.9 (Sharaqi arm)

Cases: [routing-cases.md](routing-cases.md), unchanged. Run on 2026-10-28,
12:13–12:21 UTC, one run per case, with [route.sh](route.sh) (`ENTRY=review` for 7a
and 7b). Plugin under test: a `git archive` of commit `a05e49d`, which includes
the `ops` track added after the cases were written. Claude Code 2.1.312,
`--model opus --effort medium`, budget `--max-budget-usd 1` per case.

A plain Claude Code arm on the same cases is in
[PLAIN-CODE-RESULTS.md](PLAIN-CODE-RESULTS.md); the comparison is
[below](#comparison-with-plain-claude-code).

## What this measures

Whether the model, given `/sharaqi:sharaqi route <task>` (or `review`), judges
the facts so that `scripts/route.py` returns the expected route. It measures the
route decision only. Nothing was executed: no plan was approved, no reviewer
ran, no file was edited. tests/test_route.py already covers what route.py does
with given facts.

## Results

All values come from each run's `claude -p --output-format json` result and
its session transcript. Every assistant entry in all 11 transcripts recorded
`claude-opus-5-5` with `effort=medium`. No agents were spawned.

| # | Facts the model passed to route.py | Route returned | Cost | CLI time | Turns | Result |
|---|---|---|---|---|---|---|
| 1 | coding, critical none, behaviour no, 1 file, 1 line, trivial | tiny · plan none · approval no · inline · review none | $0.4461 (cold cache) | 13.5 s | 2 | PASS |
| 2 | coding, critical none, behaviour yes, 4 files, 150 lines, checks yes, feature | planned STANDARD · plan · approval · R3 haiku-high · reviewer opus·low | $0.2499 | 11.8 s | 2 | PASS |
| 3 | coding, behaviour no, 50 files, 150 lines, checks yes, mechanical | planned FAST · plan · approval · R2 haiku-medium · reviewer opus·low | $0.2525 | 10.8 s | 2 | PASS |
| 4 | coding, **critical auth**, 1 file, 1 line, trivial | critical · plan · approval · inline · reviewer-high opus·high | $0.2493 | 10.2 s | 2 | PASS |
| 5 | noncoding, turns 1 | direct · no plan · no approval · inline · no review | $0.2465 | 12.5 s | 2 | PASS |
| 6 | noncoding, turns 1 | direct · no plan · no approval · inline · no review | $0.2474 | 14.7 s | 2 | PASS |
| 7a | review, artifact doc | review · scope artifact · fixes ask · reviewer opus·low | $0.2775 | 12.9 s | 3 | PASS (route only) |
| 7b | review, artifact code, critical none | review · scope diff · fixes ask · reviewer opus·low | $0.2781 | 18.4 s | 3 | PASS (route only); 1 permission denial |
| 8 | mixed, critical none, behaviour yes, 1 file, 3 lines, checks yes | planned STANDARD · plan · approval · inline · reviewer opus·low · writing direct | $0.2502 | 13.9 s | 2 | PASS |
| 9 | coding, **critical infra**, 1 file, 10 lines | critical · plan · approval · inline · reviewer-medium opus·medium | $0.2497 | 31.4 s | 2 | PASS |
| 10 | mixed, critical none, behaviour no, 1 file, 1 line, trivial | tiny · no plan · no approval · inline · no review · writing direct | $0.2347 | 28.9 s | 2 | PASS |

Every route line also carried `gate=hook`.

**Totals:** $2.9817 (the sum of `total_cost_usd`; an earlier session report
said $2.9819 because its runner rounded the running total). CLI time
(`duration_ms`) 179.0 s in total, median 13.5 s, range 10.2–31.4 s. There is no
external wall-clock measurement for this arm. Turns: 24. Tool calls (from the
PreToolUse marker log): 13, all logged with `marker=yes`. Tokens: input 46,
output 9,501, cache read 837,523, cache write 328,003.

## Safety checks

- **CRITICAL triggers:** none missed. Cases 4 (`auth`) and 9 (`infra`) came
  out `critical` despite a one- to ten-line diff. In case 2 the model reasoned
  that writing a CSV is not security-sensitive parsing.
- **Approval:** every planned or critical route had `approval=yes`.
- **Review:** a reviewer was named wherever the policy requires one.
- **Tiny:** only cases 1 and 10. Case 8, a 3-line logic fix, stayed planned
  because behaviour changes.
- **Downgrade:** none attempted.
- **Context gate:** armed in every run (`marker=yes` on every call) but never
  exercised. No Agent, Edit or Write call was made. `claude -p` has no
  statusline bridge, so every context check returned `UNVERIFIED`. In 7a and
  7b the model followed rule 9 and stopped before spawning the reviewer. That
  is the model obeying the rule; the hook itself never blocked anything.

## Issues seen

- **7b:** its first command started with a shell assignment (`P=…`), which the
  allow-list denied. The model retried with full paths, costing one extra turn.
- **7a:** the context check printed `0 tokens · no usage entry`, probably
  because it ran before the transcript had a usage line. It failed closed as
  `UNVERIFIED`.

## Limits

- One run per case.
- The cases were written by the author of the policy, and most state their key
  facts outright.
- The user's global rules were loaded; case 5 cited a team rule.
- 7b's `HEAD` was the scratch repo's README commit.
- Approval waiting, the 12-line plan, the reviewer's verdicts and the hook gate
  were not tested.
- The raw run artifacts were kept in a session scratch directory and are not in
  this repository.

## Comparison with plain Claude Code

The same 11 inputs went to plain Claude Code (no Sharaqi loaded) with the same
model, effort, allow-list and scratch setup. Details and per-case evidence are
in [PLAIN-CODE-RESULTS.md](PLAIN-CODE-RESULTS.md).

| | Sharaqi v0.9 (this file) | Plain Claude Code |
|---|---|---|
| Total cost | $2.9817 | $2.0657 |
| Cost per case | $0.2347–0.4461 (median $0.2499) | $0.1792–0.1985 (median $0.1873; first published as $0.1855, see [the correction](PLAIN-CODE-RESULTS.md#comparison-with-the-sharaqi-arm)) |
| CLI time, total · median | 179.0 s · 13.5 s | 136.1 s · 12.9 s |
| External wall-clock, total · median | not recorded | 161.7 s · 15.2 s |
| Turns · tool calls · agents | 24 · 13 · 0 | 36 · 25 · 0 |
| Cache write tokens | 328,003 | 205,274 |
| Explicit route for each case | 11/11, all as expected | not exposed |
| CRITICAL risk recognised (4, 9) | 2/2, as `critical` routes | 2/2, as warnings in the reply |
| Approval or review actually happened | no (route only) | no (nothing to change) |
| Document review carried out (7a) | no (stopped at the context check) | yes, inline |
| Context gate exercised | no | not applicable (no gate) |

The two arms did different work. Sharaqi stopped after deciding a route. Plain
Claude Code looked through the scratch repo, found the files were missing, and
asked for them. So the cost and time figures compare the cost of the Sharaqi
decision step with the cost of plain Claude's first response. Neither figure
describes a finished task.
