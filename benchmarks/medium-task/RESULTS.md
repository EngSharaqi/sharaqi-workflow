# Medium-task benchmark: results — 2026-10-22

Protocol: [PROTOCOL.md](PROTOCOL.md), written before the first run and
unchanged (`shasum -a 256 -c HASHES.sha256`: 22/22 OK after all runs).
Tables below come from [summarize.py](summarize.py) over the run outputs.
Claude Code 2.1.274, `--model opus --effort medium` (resolved to
`claude-opus-5`), plugin v0.7.1 loaded from one frozen snapshot in both arms.
Total spent: $7.83.

## Per run

| Run | Cost $ | Wall s | Turns | Hidden /16 | Probe /8 | npm test | Files changed | Commits | Denials | Marker log |
|---|---|---|---|---|---|---|---|---|---|---|
| plain-1 | 0.99 | 156 | 32 | 16 | 8 | pass | 12 | 1 | 1 | 0/31 yes |
| plain-2 | 0.97 | 147 | 32 | 16 | 8 | pass | 12 | 1 | 1 | 0/31 yes |
| plain-3 | 0.92 | 159 | 26 | 16 | 8 | pass | 12 | 1 | 1 | 0/25 yes |
| skill-1 | 1.40 | 208 | 36 | 16 | 8 | pass | 13 | 1 | 1 | 35/35 yes |
| skill-2 | 1.71 | 296 | 38 | 16 | 8 | pass | 12 | 1 | 0 | 46/46 yes |
| skill-3 | 1.84 | 314 | 37 | 16 | 8 | pass | 13 | 1 | 1 | 41/41 yes |

Run order was skill-1, plain-1, skill-2, plain-2, skill-3, plain-3. Cost is
Claude Code's `total_cost_usd`; wall time is measured around the `claude -p`
call. "Commits 1" is the fixture commit: no run committed. The marker log
confirms the validity condition: the ceiling hook was inert on every plain
call and active on every sharaqi call.

## Per arm: median (range)

| Arm | Cost $ | Wall s | Turns | Hidden /16 | Probe /8 | Succeeded |
|---|---|---|---|---|---|---|
| plain | 0.97 (0.92–0.99) | 156 (147–159) | 32 (26–32) | 16 (16–16) | 8 (8–8) | 3/3 |
| sharaqi | 1.71 (1.40–1.84) | 296 (208–314) | 37 (36–38) | 16 (16–16) | 8 (8–8) | 3/3 |

Pre-registered rule: a metric favours an arm only if the ranges don't
overlap.

| Metric | Verdict |
|---|---|
| Cost | **plain cheaper** (ranges don't overlap; median 1.77× with sharaqi) |
| Wall time | **plain faster** (ranges don't overlap; median 1.9× longer with sharaqi) |
| Turns | **plain fewer** (ranges don't overlap) |
| Hidden tests | no difference: 16/16 in all six runs |
| Edge probe | no difference: 8/8 in all six runs |
| Success | 3/3 in both arms |

## What the skill did

| Run | Cost per model (Claude Code) | Mode | Route | Agents spawned | References read | Skill bytes |
|---|---|---|---|---|---|---|
| skill-1 | claude-opus-5 $1.3992 | STANDARD | inline ("14 small files, all already read; a brief plus re-verification would cost more") | none | none | 8,666 |
| skill-2 | claude-opus-5 $1.6138, claude-sonnet-5 $0.0998 | STANDARD | inline | `sharaqi:reviewer` · sonnet | review.md | 12,119 |
| skill-3 | claude-opus-5 $1.7451, claude-sonnet-5 $0.0907 | STANDARD | inline ("8 small files already in context; a brief would cost more than the edit") | `sharaqi:reviewer` · sonnet | review.md | 12,119 |

- Triage matched the pre-registered expectation (STANDARD) in all three runs.
- The skill never delegated the implementation. Its break-even rule judged a
  brief plus re-verification dearer than editing 14 small files it had
  already read. So this run measures orchestration overhead again, not
  delegation.
- In runs 2 and 3 the Sonnet reviewer was spawned on the "diff over ~150
  changed lines" trigger (both diffs about 239 lines). Both returned PASS
  with no findings, at $0.09–0.10 each. Run 1 had a diff of the same size
  (265 lines) and no reviewer: the trigger was applied inconsistently.
- `tokens.py` reproduced Claude Code's cost exactly for every sharaqi run.
  For plain runs it is $0.0013 lower: Claude Code also reports one small
  `claude-haiku-4-5` call that doesn't appear in the session transcript.

Where the extra cost comes from (medians of the `tokens.py` main-thread rows):

| | plain | sharaqi |
|---|---|---|
| Opus requests | 10 | 13 |
| Opus output tokens | 12,795 | 20,794 |
| Opus cache writes | 40,497 | 70,291 |
| Opus cache reads | 481,293 | 760,903 |

More requests, each re-reading a larger context (skill text, the step-1
record, the self-review), and more written prose.

## Quality

Both arms passed every hidden test and every edge probe in every run,
including the P7 trap (`averageRating` of only unrated items). The edge-input
advantage seen on the cart toy task, where the plain run returned NaN, did
not appear here: on this task plain Opus handled every probed input.

## Permission denials

Five of six runs (both arms) tried to read files with a shell `for` loop
(`for f in src/*.js; do cat -n "$f"; done`), which the allow-list doesn't
match, and fell back to other reads. Same allow-list in both arms, so it
affects both; it added a turn where it happened.

## Deviations

- The first attempt to launch runs 2–6 failed before calling Claude (a shell
  quoting error in the loop that called `run.sh`; no run started, nothing
  spent). Relaunched with the same order and harness.
- `summarize.py` was written after PROTOCOL.md (it reads the outputs; it
  doesn't affect the runs) and isn't in `HASHES.sha256`.

## Conclusion

On this medium task the plain prompt was cheaper (median $0.97 vs $1.71),
faster (156 s vs 296 s) and equally correct (16/16 hidden, 8/8 edge probe in
all runs). sharaqi triaged correctly and reported accurately, but chose not to
delegate, so it paid orchestration overhead and, in two runs, a reviewer that
found nothing. The claim that sharaqi is cheaper is not supported by this
benchmark. Whether delegation pays on a larger task, where the break-even
rule would hand work to a cheaper model, is still unmeasured.

## Next version (not applied)

Listed, not applied, per the protocol. Each would need its own measurement.

1. **Size trigger for the reviewer.** A diff that is mostly a mechanical
   rename with tests covering the behaviour triggered a reviewer by line
   count alone. Candidate rule for any repo: count only non-mechanical
   changed lines, or skip the size trigger when the changed behaviour has
   tests. Hypothesis, unmeasured.
2. **Apply triggers consistently.** Run 1 skipped a reviewer its own table
   called for. Candidate: print the trigger check (`Reviewer: yes/no — <which
   trigger>`) on the Route line, so the decision is explicit.
3. **Overhead on the inline path.** On inline STANDARD tasks the skill wrote
   about 60 % more output than plain and re-read a larger context. The
   step-1 statement and the report are the candidates to shorten; any cut
   must keep the edge-input line, which paid off on the cart task.
4. **A task large enough to cross the break-even**, to measure delegation
   itself.
