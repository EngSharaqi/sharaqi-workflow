# Changelog

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
