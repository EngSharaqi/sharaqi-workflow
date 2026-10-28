# Medium-task benchmark: protocol (pre-registered)

Written on 2026-10-22, before the first run. Not edited after it. Anything
that changes during the runs is logged in [RESULTS.md](RESULTS.md) under
"Deviations", not here. `HASHES.sha256` pins the fixture, hidden tests,
probe, task text and harness as they were when this file was written.

## Question

On a task big enough for delegation to have a chance, does `/sharaqi do`
(v0.7.1) cost less, take less time, or produce a better result than a plain
prompt to the same model?

## Task

A dependency-free Node library ([fixture/](fixture/)): 8 source files and 6
test files, 313 lines, 18 passing tests (`npm test`). Domain: a reading list.
No words that suggest money, auth, data deletion or other CRITICAL triggers.

The prompt is [task.txt](task.txt), identical in both arms. It asks for:

1. A mechanical rename across most files: field `pages` → `pageCount`, plus
   `totalPages`, `averagePages`, `minPages`/`maxPages` and the sort key.
2. A feature spanning six files: an optional `rating` (integer 1–5) in
   validation, CSV import/export, formatting, filtering, sorting and a new
   `averageRating`.
3. Tests for the new behaviour, `npm test` passing, no commit.

Expected sharaqi triage, decided now: **STANDARD** (logic and feature work in
a small library, no CRITICAL trigger). The route is not predicted; it is
recorded.

## Ground truth

**Hidden tests** ([hidden/hidden.test.js](hidden/hidden.test.js), 16 tests,
H1–H16): only behaviour task.txt states. Copied into the run's tree after
the run, executed with `node --test`, then removed. Validated before any run:
16/16 on a reference solution written for this purpose (kept outside the
repo), 2/16 on the untouched fixture.

**Edge probe** ([probe.mjs](probe.mjs), 8 cases): inputs task.txt does not
spell out. A case passes only if the feature it probes exists. Validated: 8/8
on the reference, 0/8 on the fixture, 6/8 on a deliberately naive variant.

| Case | Category | Input | Pass |
|---|---|---|---|
| P1 | wrong type | `createItem` with `rating: "4"` | throws, or stores the number `4` |
| P2 | wrong type | `rating: NaN` | throws |
| P3 | wrong type | CSV rating cell `abc` | `parseCsv` throws |
| P4 | negative | CSV rating cell `-3` | `parseCsv` throws |
| P5 | missing | CSV round trip of an unrated item | rating comes back `null` |
| P6 | empty | `averageRating([])` | `null` or throws |
| P7 | empty | `averageRating` of only unrated items | `null` or throws (the trap: copying `averagePages`' `items.length === 0` check gives NaN) |
| P8 | missing | `formatItem` of an unrated item | text contains none of `null`, `undefined`, `NaN`, `rated` |

`null` is the pass value for P6 and P7 because the fixture's existing
`averagePages([])` returns `null`.

## Arms

| | plain | sharaqi |
|---|---|---|
| Prompt | task.txt | `/sharaqi:sharaqi do ` + task.txt (the plugin form of `/sharaqi do`) |
| Model, effort | `--model opus --effort medium` | same |
| Plugin | v0.7.1 snapshot via `--plugin-dir` | same snapshot |
| Installed skills-folder copy | disabled (`enabledPlugins`) | same |
| Allow-list | [run.sh](run.sh): Read, Edit, Write, Glob, Grep, Agent, Task, SendMessage, and Bash for npm, node, git, date, python3, python, ls, cat, grep, head, tail, wc, find, sed, mkdir | same |
| Budget cap | `--max-budget-usd 8` | same |

Both arms load the same plugin so their system prompts differ only by what
the skill itself adds. In the plain arm the plugin's hooks must stay inert:
[marker-log.sh](marker-log.sh) logs, on every tool call, whether the
session has a sharaqi run marker. Pass condition for a valid plain run: no
call logged `marker=yes`. For a valid sharaqi run: every call logged
`marker=yes`.

Each run starts from a fresh copy of the fixture, committed to a new git
repo, in a directory outside this repository, so neither arm can read the
hidden tests or the probe.

Order: sharaqi 1, then plain 1, sharaqi 2, plain 2, sharaqi 3, plain 3
(interleaved, so drift over time hits both arms). Same machine, same CLI
version, sequential, nothing else running against the same account on
purpose.

## Stop rules

- Estimated total before starting: about $12 (plain $1–2 per run, sharaqi
  $1.5–3.5 per run, three each). Hard ceiling from the budget caps: $48.
- If sharaqi run 1 costs more than $5, stop and ask before continuing.
- A run that ends in an error or hits the budget cap counts as a run, with
  its hidden-test and probe results as they are.

## Recorded per run

From Claude Code (`--output-format json`): `total_cost_usd`, `duration_ms`,
`num_turns`, `permission_denials`, per-model `costUSD`. From the tree: hidden
tests passed, probe cases passed, `npm test` exit code, files changed. From
`scripts/tokens.py` on the session: per-model and per-role split. From the
transcript: the `Mode:` and `Route:` lines, agents spawned (type, model), and
references read.

## Success and comparison

A run **succeeds** if: hidden tests 16/16, `npm test` exits 0, and nothing is
committed.

For each arm: median and range (min–max) of cost, wall time, turns, hidden
tests and probe score; success count out of 3.

With three runs per arm there is no significance test. A metric is called
better for one arm only if the two arms' ranges do not overlap. Otherwise it
is reported as "no clear difference at N = 3", even when the medians differ.

The skill is not changed between runs or after seeing results. A generic fix
suggested by the results goes under "Next version" in RESULTS.md, unapplied.

## Known limits, stated in advance

- One task, one fixture, N = 3. A direction, not a general result.
- `--model opus` on Claude Code 2.1.274 resolves to `claude-opus-5`, not Opus
  5.5. The Agent tool on that version has no `effort` parameter.
- User-level Claude Code settings and instructions on the benchmark machine
  apply to both arms equally; they are not removed.
- The task names its files' roles but not every file; how much the skill
  delegates depends on its own break-even rule, which this task may or may
  not cross.
