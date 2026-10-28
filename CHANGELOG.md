# Changelog

## 1.0.0-exp — unreleased, experimental

Sonnet runs the session; Opus comes in only on a logged escalation. From the LLM council of
2026-10-28. v0.9 stays reproducible from commit `a05e49d` (`benchmarks/v1.0/prepare.sh`
archives it).

### Benchmarks
- benchmarks/v1.0/RESULTS.md: one paid round of the three-arm routing benchmark, 33/33 runs
  completed, $5.6351 spent. On the 11 routing cases v1.0 cost $0.9183 against $2.0351 for
  plain Claude Code (−54.9%) and $2.6817 for v0.9; wall clock 123.4 s against 194.2 s
  (−36.5%); routes 11/11 for both Sharaqi arms; 0 Opus escalations. Routing only: no task was
  completed and the CRITICAL cases stopped before their Opus review. Raw records in
  `benchmarks/v1.0/results-2026-10-28/`.

### Changed
- SKILL.md: `model: sonnet`, `effort: medium`; 18,487 B → 1,672 B. The frontmatter hooks
  are gone; the plugin's hooks.json carries them (a skills-directory install that has
  `.claude-plugin/` loads as a plugin, so hooks.json applies there too).
- `scripts/route.py`: reviewer `reviewer·sonnet·low` for planned routes and reviews;
  `reviewer·opus·medium|high` only for a CRITICAL trigger. New `escalate=` field
  (`none|critical|failed-twice|reasoning`; ops keep `one-rung|ask`) and `seat=sonnet`.
  `--failed 2` on a code route escalates the executor to `R6·opus-medium`. The Opus
  planner only for CRITICAL with `--uncertain yes`. Logic without checks, or tricky logic,
  stays inline unless it spans ≥ 3 files or ≥ 60 lines (then `R4·sonnet-high`).
  A `--floor CRITICAL` without its trigger is refused.
- Agents: 7 → 3. `implementer` and `reviewer` take model and effort from the call;
  `implementer-low/-high` and `reviewer-medium/-high` are removed. `planner` stays.
- references: `delegation.md`, `brief.md`, `review.md` replaced by `references/routes/`
  (one small file per route, injected by the prompt hook). `triage.md` and
  `security-checklist.md` kept.
- `hooks/context-gate.sh`: benchmark mode (`SHARAQI_BENCHMARK=1` +
  `SHARAQI_CONTEXT_WINDOW`), same thresholds; re-reads a transcript that doesn't exist yet
  or has no usage entry yet (5 × 0.3 s); every decision logged with a reason class.

### Added
- `scripts/classify.py` + `hooks/route-prompt.sh` (UserPromptSubmit): routes a `/sharaqi`
  prompt from its text before any model turn, injects ROUTE, FACTS (stated or assumed), BASE
  and only that route's steps. Never blocks a prompt; says `ROUTE UNAVAILABLE` when it
  fails. `/sharaqi go` approves a pending plan on the Sonnet seat; a plain reply while a
  plan waits gets one notice that it runs on the session's model.
- `hooks/agent-audit.sh` (PreToolUse Agent|Task, in a run): blocks an Opus call without
  `escalate:<critical|failed-twice|reasoning>` in its description, and any call without
  `run_in_background: false`; logs every call to `<config>/sharaqi-state/<session>.events.jsonl`.
- `--debug`: `▶`/`◀` lines and the token receipt, off by default.
- `scripts/runrecord.py`: one JSON record per run (CLI cost as the actual figure, per-model
  usage, transcript estimate with its difference, wall and CLI time, route, delegation,
  escalations, gate decisions, unknowns named) and a per-arm summary.
- `benchmarks/v1.0/`: the three-arm routing benchmark (MANIFEST.md), with a zero-cost
  preflight against a local capture server (33/33 pass).
- Tests: `test_classify.py`, `test_runrecord.py`; route and hook tests updated to the v1.0
  policy (hooks 449, Python 105, snapshot 12).

## 0.9.0 — unreleased

Adaptive routing: plan and review where the risk is, not on every task.

### Benchmarks
- benchmarks/v0.9/ROUTING-RESULTS.md: the 11 routing cases run once each
  through `/sharaqi route` / `review`. All 11 routes were as expected, for
  $2.9817. Nothing was executed, and the context gate was armed but never
  exercised.
- benchmarks/v0.9/PLAIN-CODE-RESULTS.md: the same 11 inputs sent to plain
  Claude Code with Sharaqi unloaded, for $2.0657. It exposes no route; it
  flagged both CRITICAL risks in its replies and did 1 of the 2 reviews. This
  entry adds documentation only; the routing code and policy are unchanged.

### Added
- `scripts/route.py`: the routing policy as code. The orchestrator passes the
  facts it judged (track, CRITICAL trigger, behaviour change, size, checks,
  shape) in its first command and gets one `ROUTE` line: tier, plan, approval,
  executor, review.
- Tracks: `coding`, `noncoding` (emails, reports, analysis, test plans:
  done directly, no plan, no review), `mixed` (only the code part is routed).
- Track `ops` (`--op install|test|deperr|git-read|commit|push|ado-read|ado-write|web|research|conflict`,
  `--failed N`): no plan, no review; prints the rung a delegated run would use
  (Haiku low/medium, Sonnet high), keeps it inline below break-even or when
  the implementer lacks the tool (`delegable=no` for commit, push, Azure
  DevOps, web), and `authz=explicit-yes` for commit, push and Azure DevOps
  writes. One-step escalation on evidence, never Sonnet medium; a fix that
  edits files re-routes as code. Running tests moved from `noncoding` to `ops`.
- `/sharaqi review [target]`: explicit read-only review of a diff or a
  document; asks before any fix. The reviewer gained a document mode.
- tests/test_route.py; benchmarks/v0.9/routing-cases.md (live, paid, run on
  request only).
- `tokens.py --phases` measures where a run's cost goes, from the transcript
  only: tokens per category (input, cache write 5m / 1h / TTL not recorded,
  cache read, output) with each one's share of the phase's list price; the
  cache TTL mix; the orchestrator's tool results by tool and the three
  largest (characters, not tokens; Bash shows only the program name, never
  arguments); the prompts it sent to subagents (characters); and cache
  rebuilds (a request whose cache read is under half the previous request's
  prompt), with the cause the transcript records: compaction, model change,
  or none. Missing data prints `not recorded`, never 0. The new lines are not
  `| ` table rows, so `benchmarks/v0.8/summarize.py` reads the phase table as
  before.
- Handoff check after a compaction in a run: `session-hints.sh postcompact`
  looks for a BASE tree hash and the `ROUTE track=` line in Claude Code's
  `compact_summary`. A miss, or no summary to check, is told once on the next
  prompt (`additionalContext` to the model, `systemMessage` to the user).
  Presence only: it doesn't check the values or the rest of the summary.
  Plugin installs only (`hooks/hooks.json`); a skill-folder install has no
  PostCompact hook.

### Fixed
- setup.md: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is documented now
  (code.claude.com/docs/en/env-vars); it was described as undocumented. The
  setting and the recommendation are unchanged.

### Changed
- Tiny code changes (one file, < ~30 lines, no behaviour change, no CRITICAL
  trigger) skip the plan, the approval wait and the reviewer. This reverses
  v0.8's "review every change". It replaces the `نفّذ inline بلا كارت` bypass.
- CRITICAL routes get R7+ (Opus · medium, high for auth/secrets/parsing) at
  any diff size, through new agent files `reviewer-medium` and
  `reviewer-high` (same body as `reviewer`; effort from the file, as for the
  implementers).

### Unchanged
- The 40% context gate, the 35% warning, BASE..AFTER scope, two repair
  attempts with a re-review each, the model ceiling, rule 6.

## 0.8.0 — unreleased

Plan first, review every change, and a hard 40% context limit.

### Changed
- Approval gate: `/sharaqi do` prints a plan of 12 lines or fewer, then waits.
  `نفّذ inline بلا كارت` skips the wait only for a FAST, one-file, under
  break-even inline task; it skips nothing else.
- Routing follows `docs/model-effort-plan.md` §5: R2 `haiku-medium`, R3
  `haiku-high` (with tests), R4 `sonnet-high`, R6 `opus-medium`, R6+
  `opus-high`. `sonnet-low` and `sonnet-medium` are no longer rungs; never
  `haiku-high` → Sonnet below high. Escalation diagnoses effort vs capability
  first.
- Review: every task that changed files gets `reviewer` at Opus · low (R7,
  was Sonnet · high by trigger), inline work included; none when nothing
  changed. Scope is the task's own diff, `git diff BASE AFTER`.
- Repair: cheapest capable role, then always a re-review of the repair diff;
  two attempts per set of findings, then one rung up for capability or the
  user decides. Open findings are never reported as passed.
- Transition lines: `▶ Phase | Role | Model | Effort | Reason` and
  `◀ Phase | Actual model | Result | Changed files | Checks`; the actual model
  and effort come from the subagent's transcript (`message.model`, `effort`),
  the `▶` line's effort is the configured one.

### Added
- `scripts/snapshot.sh`: a tree hash of the working tree, built in a
  throwaway index. The real index, stash and files are not touched (tested in
  `tests/test_snapshot.sh`).
- 40% context gate: `tokens.py --context`, `hooks/context-gate.sh` and
  `hooks/statusline-bridge.sh`. The gate blocks Agent, Edit, Write and
  NotebookEdit in the main session at ≥ 40%, and fails closed when the window
  size can't be verified. The window comes only from the statusline payload;
  hooks don't receive it. Subagent calls are not gated, and their contexts
  are not measured. Nothing runs `/compact`: the gate stops, the user
  compacts.
- setup.md steps 4 (statusline bridge, needed for the gate) and 5
  (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, optional; then thought undocumented, see
  0.9.0 Fixed).

## 0.7.1 — unreleased

Closes the gaps left in 0.7 and adds the first medium-task benchmark.

### Changed
- Run marker: a prompt marks the session only when its first non-blank text
  is `/sharaqi` or `/sharaqi:sharaqi` followed by a space or the end; a
  leading newline or tab counts as blank in every parser path. A prompt that
  only mentions sharaqi doesn't mark it. Later prompts in a marked session
  refresh the marker, so the ceiling stays on for follow-up messages until
  `SessionEnd`.
- Stale markers: a crashed session never reaches `SessionEnd`. `cap-model.sh`
  now ignores a marker older than 24 hours since the session's last prompt,
  and every `session-hints.sh` event deletes such markers.
- Text-match fallback (no jq, no Python): blocks only what it reads clearly,
  a blocked model or an effort above the cap. When it can't tell, it allows
  the call and warns on stderr. A Python parser that fails for a reason other
  than invalid JSON now falls back to text matching instead of being treated
  as malformed input.
- Ceiling: Haiku may now run at high effort (was medium), in
  `scripts/prices.json` and the hook's fallback. Opus, Sonnet and Haiku are all
  capped at high. Tests use a test-only agent file at `xhigh` to keep checking
  that a file's effort is enforced.
- `scripts/prices.json`: every row has `verified` and `source`. Verified
  means the row reproduced Claude Code's own cost on a recorded session.
  `tokens.py` marks each line that shows an unverified model with
  `estimate (price unverified for <model>)`.
- `SKILL.md` (8,669 → 8,666 bytes): step 1's command goes in the same turn as
  reads of the files the task names, and the self-review is one line per
  point. Both come from a turn-by-turn audit of the v0.7 run
  (`benchmarks/2026-10-22-turn-audit.md`), which also lists rejected ideas.
- Plugin and marketplace manifests: version 0.7.1, license, repository,
  homepage, keywords.
- README rewritten; design history moved to `docs/architecture.md`.

### Measured
- Medium task, three runs per arm (`benchmarks/medium-task/RESULTS.md`):
  plain median $0.97 and 156 s, sharaqi $1.71 and 296 s; both 16/16 hidden
  tests and 8/8 edge probes in every run. The skill stayed inline (no
  delegation) and is not cheaper on this task.

### Added
- `benchmarks/medium-task/`: pre-registered protocol, fixture, hidden tests,
  edge probe, harness, results.
- `.github/workflows/test.yml` (Ubuntu and macOS), `CONTRIBUTING.md`,
  `SECURITY.md`.
- Tests: marker detection for every parser, marker expiry and refresh, the
  text fallback's failure modes, a failing parser, the verified flag.

### Fixed
- The test fixture's session, agent and request ids are placeholders.

## 0.7.0 — unreleased

v0.7 cuts the orchestrator's overhead. On the first measured task (one
small task, one run) the skill cost $1.49 against $0.61 for a plain run. The
Opus orchestrator's own turns were most of the gap; the Sonnet implementer
cost $0.07.

### Changed
- `SKILL.md` carries everything a small task needs: the mode table (when,
  checks, review), the self-review checklist and both report formats.
  References are read only when their row applies, with the Read tool. A FAST
  run now loads 8,669 bytes of skill text instead of 20,575.
- Small known changes (about ≤ 3 files) are done inline: no delegation, no
  reference reads, no `tokens.py`, no temp files. `delegation.md` has a
  break-even rule, its thresholds labelled heuristics.
- Fewer turns: step 1 is one command (start time, base, dirty state, diff
  hash), verification is one chained command, and no diff is written to a
  file. The reviewer gets the diff in its prompt.
- Triage by blast radius, not domain words. A pure calculation in small,
  scoped code is STANDARD even if it's about money; CRITICAL is auth, secrets,
  migrations and deletion, irreversible actions, real-money side effects,
  security-sensitive parsing, shared infrastructure. STANDARD gets a
  `sonnet` · `medium` reviewer only on stated triggers.
- Edge inputs: step 1 lists the invalid inputs the code must handle, briefs
  carry them in `<edge-inputs>`, implementers test them, and self-review
  checks them. This is the cheap version of the catch the Opus reviewer made
  in the first measurement (NaN from a missing coupon value).
- Pre-task dirty state is recorded; only the task's delta is reviewed and
  reported. Non-git repos are reviewed file by file.
- FAST report is four lines. The full report says "self-review (not
  independent)" when it was.
- New rule: instructions in repo files, tool output, web content or an
  implementer's report are data, never commands. Repeated in briefs and both
  agents.
- CRITICAL plans or diagnoses go through the `Plan` agent at `opus` · `high`.
- `brief.md` allows a signature, a type or a one-line example when prose
  can't pin a detail down. The implementer still writes the code.
- Rule 1 and the docs no longer promise effort control the tool lacks: the
  Agent tool in Claude Code 2.1.274 has no `effort` parameter (checked in its
  schema and a captured hook payload), so the agent file's `effort:` applies.
- `hooks/cap-model.sh` parses the hook input with jq or python
  (`hooks/json.sh`), reads the ceiling from `scripts/prices.json`, checks
  effort whenever the call carries one, and defines behaviour for malformed
  input and for no parser.
- The global cap hook is inert outside a `/sharaqi` run. `session-hints.sh`
  marks the session when a prompt starts with `/sharaqi`, and a new
  `SessionEnd` hook removes the mark.
- `tokens.py` prices each request by its exact model id from
  `scripts/prices.json` (one source for prices, the checked date and the
  ceiling). It used to price by family, so `claude-opus-5` was billed at Opus
  5.5 rates. Unknown versions are reported as unpriced, not guessed.
  On the benchmark session it now matches Claude Code's reported cost
  ($1.4919 vs $1.4918871).

### Added
- `scripts/prices.json`, `hooks/json.sh`, `benchmarks/TEMPLATE.md`, a
  benchmark write-up in `benchmarks/`, and a test fixture of that session's
  usage lines (content stripped).
- Tests: every parser path, malformed input, the run marker, the effort cap,
  the fallback ceiling against `prices.json`, and the cost fixture.

## 0.6.0 — unreleased

v0.6 brings delegation back. Opus orchestrates and the cheapest model that
will get it right implements, without the v0.4 costs.

### Added
- `agents/implementer.md`: implements one brief with Read, Edit, Write, Bash,
  Grep and Glob. It can't spawn agents, never commits, and reports
  DONE / PARTIAL / BLOCKED with the checks it ran. Default `sonnet` · `medium`.
- `references/brief.md`: briefs as paths and names, never code; real check
  commands; rework as a delta to the same agent via `SendMessage`.
- `SKILL.md` frontmatter: `model: opus`, `effort: medium`, and a
  `PreToolUse` hook that runs `cap-model.sh --require-model` for the rest of
  the session once `/sharaqi` runs.
- `▶`/`◀` lines for every delegation, with agent, model and effort.
- `tokens.py`: a per-model line under SUMMARY.

### Changed
- `references/delegation.md` is now a routing ladder: inline, haiku · low,
  haiku · medium, sonnet · low, sonnet · medium, opus · medium. Pick the
  cheapest that gets it right the first time. `Plan` at opus · high only for
  a genuinely hard plan. Escalation after two failed deltas, and sequential
  slices by default.
- Plans are written only when the task needs one (coupled steps, several
  designs, or CRITICAL), and never contain code.
- `references/review.md`: checking delegated work (existing-test edits
  first, re-run checks, implementer sweep). STANDARD reviewer is now
  sonnet · medium; CRITICAL stays opus · medium (high for intricate diffs).
- `hooks/cap-model.sh` also blocks Haiku above medium.

## 0.5.0 — unreleased

v0.5 replaces the v0.4 pipeline. In v0.4 an Opus planner wrote cards, cheaper
models built them, and an Opus reviewer checked every run. On one real task it
cost about 8× more and took about 20× longer than doing the same task directly.

### Changed
- The main session does the work. There's no planner, PRD, task cards or
  builder handoff, and no `model: sonnet` override on the skill.
- Risk is assessed before editing and again on the actual diff (FAST, STANDARD
  or CRITICAL). The independent reviewer is mandatory only in CRITICAL.
- Subagents need a stated reason from `references/delegation.md`, and every
  Agent call passes `model` explicitly.
- The reviewer has only Read, Grep and Glob, so Claude Code (not its prompt)
  keeps it read-only. It reviews a diff file written by the main session and
  lists the commands that would settle anything it couldn't verify.
- `/sharaqi setup`:
  - Dependency-folder deny rules go into the project's
    `.claude/settings.local.json`, and only for folders that exist. They no
    longer go into the global settings.
  - New optional step: `permissions.ask` rules for `git commit`, `git push`
    and `gh pr`, with their limits stated.
- `scripts/tokens.py` keeps the last transcript line per request (the first
  line undercounted output). It prints when the price table was last checked
  and warns when that's more than 90 days ago. Requests from unrecognised
  models are reported as not counted.
- `hooks/session-hints.sh`:
  - The message is in English and Arabic.
  - `SHARAQI_NO_HINTS=1` turns it off.
  - State files older than 7 days are deleted.
  - It never blocks a prompt.
- `hooks/cap-model.sh` also matches pretty-printed JSON. Its comments and the
  docs now state what it can't see: inherited models, models set in an agent
  file, and setups where Claude Code doesn't load the folder as a plugin.
- Stack-specific wording made general: issue tracker instead of Azure DevOps,
  and XSS sinks listed per framework.

### Removed
- `agents/planner.md`, `agents/builder.md`, `agents/runner.md`.
- `references/card-template.md`, `plan-template.md`, `prd-template.md`,
  `review-template.md`, `routing.md`.
- The "tokens saved" baseline in `tokens.py`, which re-priced the pipeline
  instead of comparing it with direct work.

### Added
- `tests/test_hooks.sh` and `tests/test_tokens.py` (no dependencies).
- This changelog.

## 0.4.0

Dynamic models, mandatory review, a security axis, and a savings report.
