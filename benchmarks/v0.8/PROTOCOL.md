# v0.8 end-to-end benchmark: protocol (pre-registered)

Written on 2026-10-25, before any v0.8 change to the skill, and pinned with
the fixtures, hidden tests, probes, task texts and harness in
[HASHES.sha256](HASHES.sha256). Not edited after that. Anything that changes
during the runs is logged in [RESULTS.md](RESULTS.md) under "Deviations".

## Question

Per task class, does `/sharaqi do` (v0.8, the cost-aware router) cost less
and take less time than a plain prompt to the same model, with equal
correctness?

## Task ladder

Four dependency-free Node libraries under [tasks/](tasks/), none from the
earlier cart or reading-list benchmarks. No words that suggest money, auth,
data deletion or other CRITICAL triggers.

| Class | Fixture | Task ([task.txt](tasks/)) | Hidden tests | Probe |
|---|---|---|---|---|
| tiny | text helpers, 3 source files | fix a trailing/leading hyphen in `slugify` | 7 | 4 |
| small | duration parser, 3 source files, tests | add day and second units; reject repeated or out-of-order units; format the new units | 10 | 8 |
| medium | habit tracker, 9 source files, 6 test files | weekly habits across validation, streaks, stats, CSV, format, filter | 13 | 8 |
| large | audit-event library, 12 source files, 11 test files | rename `userId` → `actorId` in 16 files, plus a severity feature across 8 modules | 16 | 8 |

**Hidden tests** (`tasks/<class>/hidden/hidden.test.js`) check only
behaviour the task text states. Copied into the run's tree after the run,
executed with `node --test`, then removed.

**Edge probe** (`tasks/<class>/probe.mjs`) checks inputs the task text does
not spell out (year boundary in ISO weeks, 0/0, case of enum values, old
input formats, boundary days). A case passes only if the feature it probes
exists.

Validated before any run, on reference solutions written for this purpose
and kept outside the repository:

| Class | Reference: hidden · probe | Untouched fixture: hidden · probe | Naive variant: hidden · probe |
|---|---|---|---|
| tiny | 7/7 · 4/4 | 4/7 · 1/4 | 5/7 · 3/4 (only the trailing hyphen stripped) |
| small | 10/10 · 8/8 | 2/10 · 0/8 | 9/10 · 7/8 (same unit twice allowed) |
| medium | 13/13 · 8/8 | 2/13 · 0/8 | 11/13 · 2/8 (week = day-of-year / 7, no enum check) |
| large | 16/16 · 8/8 | 0/16 · 0/8 | 15/16 · 6/8 (no 0/0 guard, debug retention replaces maxAgeDays) |

## Arms

| | plain | sharaqi |
|---|---|---|
| Prompt | task.txt | `/sharaqi:sharaqi do ` + task.txt |
| Model, effort | `--model opus --effort medium` | same |
| Plugin | the v0.8 snapshot via `--plugin-dir` | same snapshot |
| Installed skills-folder copy | disabled (`enabledPlugins`) | same |
| Allow-list | [run.sh](run.sh): Read, Edit, Write, Glob, Grep, Agent, Task, SendMessage, and Bash for npm, node, git, date, python3, python, ls, cat, grep, head, tail, wc, find, sed, mkdir | same |
| Budget cap | `--max-budget-usd 5` | same |

Both arms load the same plugin, so their system prompts differ only by what
the skill adds. In the plain arm the plugin's hooks must stay inert:
[marker-log.sh](marker-log.sh) logs, on every tool call, whether the session
has a sharaqi run marker. A plain run is valid only if no call logged
`marker=yes`; a sharaqi run only if every call did.

Each run starts from a fresh copy of the fixture, committed to a new git
repo, in a directory outside this repository.

Order, per class from tiny to large: sharaqi 1, plain 1, sharaqi 2, plain 2,
sharaqi 3, plain 3. Same machine, same CLI version, sequential.

## Budget and stop rules

- A cost estimate is printed and the owner is asked before the total spend
  of this round (probes, routing cases and end-to-end runs) passes $30.
- Any single run over $5 (it would hit the budget cap): stop and ask before
  continuing.
- A run that errors or hits the cap counts as a run, with its results as
  they are.

## Recorded per run

From Claude Code (`--output-format json`): `total_cost_usd`, `duration_ms`,
`num_turns`, `permission_denials`, per-model `costUSD`. Wall time around
the `claude -p` call. From the tree: hidden tests passed, probe cases
passed, `npm test` exit code, files changed, commits. From
`scripts/tokens.py --phases`: cost split by phase (orchestrator, each
implementer, each reviewer), orchestrator requests and output tokens, and
double reads (a file read by the orchestrator and then by a subagent, or
read twice by the same thread). From the transcript: the routing card,
delegations (agent, model, effort recorded on its requests), whether
delegations ran in parallel (several Agent calls in one assistant message),
and the reviewer trigger line.

## Success rules (fixed now, per class, never averaged across classes)

Correctness first. In every sharaqi run of a class: all hidden tests pass,
`npm test` exits 0, nothing is committed, and the probe score is at least
the lowest plain probe score in that class. A class that fails this has not
met its rule, whatever the cost.

| Class | Rule on medians |
|---|---|
| tiny, small | sharaqi cost ≤ 1.15 × plain cost, and sharaqi wall time ≤ 1.15 × plain wall time |
| medium, large | sharaqi cost ≤ 0.80 × plain cost, and wall time ≤ 0.80 × plain wall time, and for both metrics the two arms' ranges (min–max) do not overlap |

With three runs per arm there is no significance test. Each class is
reported as met or not met, with the medians, ranges and ratios.

## After the runs

- The skill is not changed between runs.
- If a class misses its rule, RESULTS.md says so plainly and the README
  routes users away from that class.
- One fix round is allowed, and only for generic waste a transcript audit
  shows (something any repository would pay). It is logged with before and
  after, and the affected class is rerun with the same protocol. No
  iterating until a number looks good.

## Known limits, stated in advance

- One task per class, N = 3. A direction, not a general result.
- Claude Code 2.1.274 on this machine: `--model opus` resolves to
  `claude-opus-5`, `sonnet` to `claude-sonnet-5`, `haiku` to
  `claude-haiku-4-5`, which has no effort setting (checked in a captured run
  on 2026-10-25). The Agent tool has no `effort` parameter on this version.
- User-level Claude Code settings on the benchmark machine apply to both arms
  equally.
- The fixtures are small libraries the plain arm can read whole; that favours
  inline work. Larger real repositories are not covered.
