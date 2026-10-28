# Turn audit: v0.7 cart toy run — 2026-10-22

What each turn of the v0.7 skill arm did, against the plain arm, from the two
session transcripts of the v0.7 round in
[2026-10-22-cart-toy.md](2026-10-22-cart-toy.md). The aim: find overhead that
any repo would pay, and remove only that.

## Turns versus requests

Claude Code's `num_turns` was 10 (skill) and 7 (plain). The transcripts hold 8
and 6 assistant API requests. The audit counts requests, since each one re-reads
the cached context and is what costs money. Costs below are recomputed from each
request's usage at `claude-opus-5` rates; they add up to Claude Code's own
figures ($0.5897 and $0.3923, plus $0.0011 for one Haiku call in the plain arm).

## Skill arm, request by request

| # | What it did | Output tok | Cost $ |
|---|---|---|---|
| 1 | Step 1 command (start time, HEAD, status, diff hash) and `ls -a; cat package.json`, in parallel | 243 | 0.2051 |
| 2 | `ls -R src test` and Read `src/cart.js` | 270 | 0.0729 |
| 3 | Read `test/cart.test.js` | 159 | 0.0334 |
| 4 | Task, acceptance criteria and edge-input line; Mode/Route; Edit `src/cart.js` | 1,837 | 0.0731 |
| 5 | Edit `test/cart.test.js` | 286 | 0.0510 |
| 6 | Edit `test/cart.test.js` | 913 | 0.0519 |
| 7 | Step 4: `git status --porcelain; git diff --stat; npm test` | 117 | 0.0385 |
| 8 | Self-review (five points, a paragraph each) and the report | 1,316 | 0.0638 |
| | **Total** | **5,141** | **0.5897** |

## Plain arm, request by request

| # | What it did | Output tok | Cost $ |
|---|---|---|---|
| 1 | Read `src/cart.js` and `test/cart.test.js`, in parallel | 332 | 0.1911 |
| 2 | Edit `src/cart.js` | 407 | 0.0587 |
| 3 | Edit `test/cart.test.js` | 647 | 0.0435 |
| 4 | Edit `test/cart.test.js` | 275 | 0.0367 |
| 5 | `npm test` | 193 | 0.0313 |
| 6 | Report | 213 | 0.0310 |
| | **Total** | **2,067** | **0.3923** |

## Where the $0.20 gap comes from

| Source | Skill | Plain | Gap $ |
|---|---|---|---|
| Output tokens | 5,141 | 2,067 | +0.077 |
| Cache reads (two more requests over a larger context) | 348,845 | 233,923 | +0.057 |
| Cache writes (SKILL.md, plus tool output of the extra requests) | 28,668 | 22,361 | +0.063 |

The extra requests are 1 and 3. The plain arm read both files the task names
in its first request. The skill arm ran step 1 first, then waited for
`ls -R` before reading the test file, although the task named it.

The extra output is the step-1 statement (request 4) and the self-review
(request 8): about 2,000 tokens of prose more than the plain arm wrote. That
text is where the edge-input line caught the NaN case the plain arm shipped,
so its content stays. Its length is the overhead.

## Changes made in v0.7.1

Each is justified for any repo, not for this task.

1. **Step 1 runs in the same turn as Reads of the files the task names.** The
   step-1 command depends on nothing the reads return and the reads depend on
   nothing it returns, so issuing them together saves a round trip whenever a
   task names a file. When it names none, nothing changes.
2. **Self-review is one line per point.** Output costs five times input on
   Opus. The checklist's value is that every point is considered; a paragraph
   per point adds cost, not coverage.

SKILL.md stayed net-neutral: 8,669 → 8,666 bytes (other sentences shortened
without dropping a rule).

## Rejected ideas

| Idea | Why rejected |
|---|---|
| Merge the exploratory `ls -R` into step 1 | In an unfamiliar repo the listing is how the model finds the files; removing it trades one request for wrong guesses. Kept as observed. |
| Tell the skill where tests usually live (`test/`) | Fits this fixture, not every repo. Overfitting. |
| Drop the step-1 command on small tasks | It records the base and the dirty state; without it a dirty tree's changes get reviewed and reported as the task's. |
| Drop the edge-input line or the self-review on STANDARD | They produced the one measured benefit (no NaN). |
| Shorten the STANDARD report format | It is ~10 lines of output once per task; the self-review prose was the larger cost, and the format carries the evidence. |
| Skip `git status; git diff --stat` in step 4 | One chained command, no extra request; it confirms only the intended files changed. |
| Count on fewer edits to the test file | Two edits to the test file happened in both arms; that's the model's editing, not the skill. |

## Not measured

The effect of these two changes. They were made after this run and are
measured only by the medium-task benchmark, which wasn't designed around them.
