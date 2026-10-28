# Three-arm routing benchmark: Plain · v0.9 · v1.0

Prepared 2026-10-28. **Results of the first paid round: [RESULTS.md](RESULTS.md).** The
checks below were made before it, against a local stand-in for the API (no request left the
machine, nothing was billed). Running `runall.sh` is paid and needs a separate yes.

Run note: `preflight.sh` checks that the plain arm's requests don't contain `/sharaqi`, and
the run directory's path appears in every request. Use a `RUNS` path without `/sharaqi` in
it (`~/sharaqi-bench/…` fails case 7b as a false positive).

## What it measures, and what it can't

The same 11 routing cases as v0.9, text unchanged, through three arms: the cost, time and
turns of each arm's response, and for the two Sharaqi arms whether the route is the
expected one. It is a **routing** benchmark: no file can be edited (no Edit or Write tool),
no plan is approved, and each case runs in an empty scratch repo. It says nothing about
task completion, code quality, or end-to-end time on a real task, and a result here is not
evidence for or against the 40% target on real work.

## Arms

| | A · Plain | B · v0.9 | C · v1.0 |
|---|---|---|---|
| Prompt | case text verbatim | `/sharaqi:sharaqi route <case>` (`review` for 7a, 7b) | same as B |
| Plugin | none; `sharaqi@skills-dir` disabled | `--plugin-dir plugins/v0.9` = `git archive a05e49d` | `--plugin-dir plugins/v1.0` = this working tree, frozen by `prepare.sh` |
| Seat (verified, capture) | `claude-opus-5-5` · medium | `claude-opus-5-5` · medium | `claude-sonnet-5-5` · medium (skill frontmatter) |
| Main skill | — | SKILL.md 18,487 B | SKILL.md 1,672 B + the route's steps from the prompt hook |
| Sharaqi agents listed | none | 7 | 3 (implementer, reviewer, planner) |
| Routing | — | the model judges facts, runs route.py | prompt hook: scripts/classify.py → route.py, no model call |

Same for every arm: Claude Code 2.1.312; `--model opus --effort medium`; `--max-budget-usd 1`;
`--permission-mode default`; allow-list `Read Glob Grep Agent Bash(git:*) Bash(ls:*)
Bash(wc:*) Bash(grep:*) Bash(python3:*)`; a new scratch git repo per run holding one commit
of a `# scratch repo` README; stdin from `/dev/null`; the PreToolUse marker log
(`benchmarks/v0.8/marker-log.sh`); `--output-format stream-json --verbose`; environment
`SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000`, which only v1.0 reads.

## Cases

`cases/1` … `cases/10`, `cases/7a`, `cases/7b`: byte-identical to the inputs of the v0.9
run (`cases.sha256`; `prepare.sh` refuses to start if they differ). They equal the table in
`benchmarks/v0.9/routing-cases.md` without the `(review)` prefix of 7a and 7b, which the
Sharaqi arms express through the `review` entry. Expected routes: `expected.json`, read by
both `score.py` and `tests/test_classify.py`.

## Revisions

- B: commit `a05e49d32918b5716066f573db7df11fa6c45c1c` (the tree of the published v0.9
  routing results). `prepare.sh` writes the hash to `plugins/v0.9.id`.
- C: `plugins/v1.0.id` = `worktree-tree:<git tree hash>` of the working tree at prepare
  time (`scripts/snapshot.sh`); any edit changes it, so take the id from your own
  `prepare.sh` run. The copy is `git archive` of that tree, re-hashed after extraction and
  required to equal it; tracked files deleted from the working tree are not in it. The v0.9
  copy is re-hashed against `a05e49d`'s tree the same way.

## Gate configuration

v1.0 runs headless, where no statusline reports the context window. Benchmark mode
declares one: `SHARAQI_CONTEXT_WINDOW=200000` (stricter than the 1,000,000 Claude Code
reported in `modelUsage.contextWindow` for `claude-opus-5-5` in the v0.9 runs). The 35% /
40% thresholds don't change, and the gate's output says the window was declared, not
verified. v0.9 has no benchmark mode: its gate and its own context rule stop it before any
Agent call, as they did in the published run. That is v0.9's preserved behaviour, not a
harness fault.

## Order and number

`runall.sh`: case by case; within a case the arm order rotates (plain, v0.9, v1.0 → v0.9,
v1.0, plain → v1.0, plain, v0.9 …). `REPS` rounds (default 1; 3 is what the council asked
for). Stops at the first run that fails, has no result event or costs over $1, and before a
run that could pass `CAP_USD` (default $12 per round). Never retries, never skips a case.

## Measurement (identical for every arm)

`scripts/runrecord.py` from the frozen v1.0 snapshot, one JSON record per run:

- **Cost**: `total_cost_usd` from the run's result event (Claude Code's own figure; it
  already includes subagents). Per model: `modelUsage` tokens and `costUSD`. A transcript
  estimate at `scripts/prices.json` rates is kept beside it with the difference and is
  never added to it. On the 22 published runs the estimate matched: v0.9 to the cent
  ($0.000000), Plain within $0.00013 per run, the small Haiku call `modelUsage` reports
  and the transcript doesn't.
- **Time**: wall clock around the process (`Time::HiRes`), and Claude Code's `duration_ms`.
- **Route**: v0.9 the ROUTE line printed in its reply; v1.0 the prompt hook's ROUTE from
  `<config>/sharaqi-state/<session>.events.jsonl`, which the reply must echo.
- **Delegation and escalation**: Agent calls from the transcript (parallel = several in one
  message), subagent threads, and for v1.0 every Agent call and gate decision from the
  events log (model, effort, escalate reason, allowed or blocked, with the reason class).
- Unknown values are null and listed in the record's `unknown`; no price is assumed.
- **Failed runs**: the record is written to a temp file, validated, then renamed into
  `records/`; an existing record is never overwritten. A timeout, crash, empty or
  malformed output, or a record that won't build gets a `no-result` record (reason, exit
  code, end of the error log, cost null) and `run.sh` exits 1. A success event from a
  process that exited non-zero is `error`, not `completed`. `score.py` scores a partial
  RUNS: unreadable records and every missing arm × case are listed, and it exits 1.
- **Route format**: trailing backticks, asterisks and whitespace after a ROUTE line are
  dropped before scoring and reported in their own column; nothing inside the line is.
- A median or total with no cost observation prints `unknown`, never `0.0000`.

## Criteria

- **Route**: every field in `expected.json` for the arm matches (plain: not scored).
- **Safety**: cases 4 and 9 route `critical` with an Opus reviewer and `escalate=critical`
  (v1.0) or the R7+ reviewer (v0.9); nothing is edited (no tool can).
- **Isolation**: the init event lists exactly the arm's sharaqi agents (none for plain).
- **Reviews (7a, 7b)**: whether a review was carried out, and by which model, is recorded,
  not scored.
- A failed or incomplete run stops the benchmark and is reported as such.

## Deviations from the published v0.9 and Plain runs

1. `Agent` added to the allow-list of **all three** arms, so a route that names a reviewer
   (7a, 7b) can run it instead of being refused silently.
2. stdin from `/dev/null` in all arms. Without it `claude -p` waits 3 s for stdin
   ("no stdin data received in 3s"), seen with the stand-in API; this affects wall clock
   only, and probably most of Plain's published wall − CLI gap (25.6 s over 11 runs).
3. `stream-json` output for all arms (B used `json`); it carries the same result event.
4. Interleaved, rotating order (the published runs did all of B, then all of A).
5. Wall clock recorded for B too (not recorded in the published run).
6. v1.0's expected reviewer model differs from v0.9's: that is the policy change, not a
   changed case.
7. v1.0's facts come from a deterministic classifier, not the model, so its route score
   measures the classifier, which the unit tests already cover; the classifier was written
   with these 11 cases visible. The paid run measures cost, time and whether the model
   follows the injected route.
8. `benchmarks/v0.9/PLAIN-CODE-RESULTS.md` says the plain prompts of 7a and 7b included
   `(review)`. The plain transcripts show they did not (`7a`: `The document: "…"`, `7b`:
   `HEAD`). This kit uses those transcript-verified texts.

## Commands

```bash
export RUNS=/path/outside/the/repo/sharaqi-bench-$(date +%Y%m%d-%H%M)
bash benchmarks/v1.0/prepare.sh          # free: freezes plugins/v0.9 and plugins/v1.0
bash benchmarks/v1.0/preflight.sh        # free: 33 launches against a local capture server
REPS=1 bash benchmarks/v1.0/runall.sh    # PAID: 33 calls, ≤ $1 each, stops at CAP_USD
python3 -I benchmarks/v1.0/score.py "$RUNS"
```

One arm and case only (paid): `RUNS=… bash benchmarks/v1.0/run.sh v1.0 4 1`.

**Cost to expect, one round**: about $2.1 (A) + $3.0 (B), from the published runs, plus C,
which is not known. That is not a prediction for C. `CAP_USD` stops the run at $12
per round.

## Checked before writing this (no paid call)

With the stand-in API (`capture.py`, or a scripted version during development) on Claude
Code 2.1.312:

- `preflight.sh`: 33/33 launches pass, with the seat model, skill text, agent listing,
  hook ROUTE (v1.0, all 11 as expected), and no sharaqi in plain.
- The first request at an equal tool set: plain 72,234 B, v0.9 96,747 B (+24,513), v1.0
  75,408 B (+3,174). That is bytes, not tokens.
- v1.0 headless without benchmark mode: the gate blocks every Agent call
  (`unverified-window`), which is the v0.9 failure. With it, the gate allows them.
- An Opus Agent call without `escalate:` is blocked; with `escalate:critical` it runs as
  `claude-opus-5-5` · high. A Sonnet reviewer runs as `claude-sonnet-5-5` · low.
- A background Agent call (the tool's default) hands its result to a turn on the session
  model (`claude-opus-5-5`), so the hook requires `run_in_background: false`. With it, the
  main thread stayed on `claude-sonnet-5-5` for every turn, and two foreground calls in one
  message started 0.01 s apart (parallel).
- A plain "yes" after a plan runs on the session's model, not the skill's: the approval
  path is `/sharaqi go`.
- `score.py` on the 22 published runs: v0.9 routes 11/11, totals $2.9817 and $2.0657, as
  published.
