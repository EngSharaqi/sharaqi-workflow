# sharaqi

A Claude Code skill for development tasks. Opus orchestrates: it sizes the
task, diagnoses, plans only when the task needs a plan, and hands the
implementation to the cheapest model that will get it right (Haiku or Sonnet,
effort at most medium). It then re-runs the checks itself, reviews the diff in
proportion to the risk, and finishes with a report that states only what was
actually verified.

```
/sharaqi do <task>
```

## History

- **v0.4** was a fixed pipeline: an Opus planner wrote cards with code in
  them, cheaper models built them, an Opus reviewer checked every run. On one
  real task it cost about 8× more and took about 20× longer than doing the
  task directly. The Opus steps (planner, dispatcher, reviewer) re-read a
  large context on every tool turn, and the dispatcher fell back to Opus.
- **v0.5** made the main session do everything. Fast, but no delegation at
  all.
- **v0.6** delegates again, without the v0.4 costs: no planner or dispatcher
  by default, no code in plans or briefs, briefs as paths and names,
  rework sent to the same agent so it doesn't re-read, and trivial edits done
  inline because starting a subagent costs more than they do.

## How a task runs

1. **Understand**: one-line task and acceptance criteria. Opus diagnoses an
   unclear bug itself.
2. **Risk and route**: FAST, STANDARD or CRITICAL from
   [triage.md](references/triage.md), and who implements from
   [delegation.md](references/delegation.md). A plan only when the task needs
   one (coupled steps, several designs, or CRITICAL), with no code in it.
3. **Implement**: inline for tiny edits, otherwise one
   [brief](references/brief.md) per slice to the `implementer` agent:

   | Rung | For |
   |---|---|
   | inline (Opus) | ≤ ~3 tool calls, exact edit already known |
   | haiku · low / medium | mechanical work on an existing pattern |
   | sonnet · low / medium | real feature and bug work (medium is the default) |
   | opus · medium | a slice that needs judgement a brief can't pin down |
   | Plan agent · opus · high | only a genuinely hard plan, with the reason stated |

4. **Verify**: Opus re-runs the checks; an implementer's "done" is a claim.
5. **Review** ([review.md](references/review.md)): existing-test edits first,
   an "implementer sweep" for generated-code failure modes, the post-diff
   scan, and an independent reviewer when the risk justifies it (sonnet ·
   medium in STANDARD, opus · medium in CRITICAL). Fixes go back to the same
   agent as a delta.
6. **Report**: changes, checks, mode, plan, every delegation with its model
   and effort, review, acceptance criteria, risks, and tokens per model.

Every delegation is printed as it happens:

```
▶ implementer · sonnet · effort medium — 3 files, new query hook on the existing pattern
◀ implementer · sonnet · effort medium — DONE, 3 files changed, lint + typecheck green
```

Ceiling: never Fable, never above Opus · high, Sonnet and Haiku never above
medium.

## Install

The folder must be named `sharaqi` inside your skills folder.

```bash
git clone https://github.com/EngSharaqi/sharaqi-workflow.git ~/.claude/skills/sharaqi
```

```powershell
git clone https://github.com/EngSharaqi/sharaqi-workflow.git "$env:USERPROFILE\.claude\skills\sharaqi"
```

Or as a plugin (the command becomes `/sharaqi:sharaqi do <task>`):

```bash
claude plugin marketplace add EngSharaqi/sharaqi-workflow
claude plugin install sharaqi@sharaqi-workflow
```

Start a new session afterwards.

The `implementer` and `reviewer` agents and the hooks in `hooks/hooks.json`
load only when Claude Code loads the folder as a plugin. Both installs above
do that on current Claude Code: the skills-folder clone contains
`.claude-plugin/plugin.json`, so it is listed as `sharaqi@skills-dir` under
`claude plugin list`. Check that list. When they load, the `hooks.json` hooks
apply to every session, not only to `/sharaqi` runs.

`SKILL.md` also registers its own hook when `/sharaqi` runs, for the rest of
that session: the model ceiling, plus a block on any Agent call that names no
model. It finds the script through `CLAUDE_PLUGIN_ROOT`, or
`~/.claude/skills/sharaqi` when that isn't set.

`model: opus` and `effort: medium` in `SKILL.md` apply to the `/sharaqi`
turn only. Follow-up messages in the same session run on the session's model,
so keep the session on Opus 5.5 at medium.

Python 3 is needed only for the token report. Without it, the report says
`unavailable`.

### `/sharaqi setup` (optional)

Each step asks first and can be skipped:

| Step | Writes to |
|---|---|
| Smaller auto-compact window (cheaper turns, more compactions) | `~/.claude/settings.json` |
| Ask before `git commit`, `git push`, `gh pr` | `~/.claude/settings.json` → `permissions.ask` |
| Block reads of dependency/build folders that exist in this repo | `<repo>/.claude/settings.local.json` → `permissions.deny` |

Skip setup if you're just trying sharaqi out. Everything else works without it.

## What's inside

| Path | Role |
|---|---|
| `SKILL.md` | the workflow and rules |
| `references/triage.md` | risk factors and the three modes |
| `references/review.md` | post-diff scan; when and how to use the reviewer |
| `references/security-checklist.md` | security items for CRITICAL (and any that apply elsewhere) |
| `references/delegation.md` | who implements: the rungs, the ceiling, announcing, escalation, slices |
| `references/brief.md` | how to write a brief: pointers, no code, real checks; rework as a delta |
| `references/setup.md` | `/sharaqi setup` |
| `agents/implementer.md` | implements one brief; Read/Edit/Write/Bash/Grep/Glob, no Agent; never commits |
| `agents/reviewer.md` | reviewer with Read/Grep/Glob only: spec · quality · security, returns findings |
| `hooks/cap-model.sh` | blocks Agent calls above Opus/high, Fable, and Sonnet/Haiku above medium; with `--require-model` (while `/sharaqi` is active) also calls that name no model |
| `hooks/session-hints.sh` | when loaded as a plugin: suggests a fresh session after repeated compactions |
| `scripts/tokens.py` | token usage from the local transcript, priced at API list rates |
| `tests/` | tests for the hooks and `tokens.py` |
| `CHANGELOG.md` | what changed per version |

## Token numbers

`scripts/tokens.py` reads the session transcript Claude Code writes locally.
It keeps the last line of each API response (earlier lines carry partial
output counts) and prices each request at list rates for its model. That
dollar figure is an API-equivalent estimate, not a bill. Subscription plans
aren't charged per token.

Prices are a fixed table in the script. The report prints the date the table
was last checked and warns after 90 days. Requests from a model it doesn't
recognise aren't counted, and the report says how many there were. If Claude
Code changes its transcript format, the report says `unavailable` rather than
guessing.

## What is enforced, and what is only an instruction

| Rail | Enforced by | Gaps |
|---|---|---|
| Reviewer can't change anything | Claude Code: the agent has no Bash, Edit or Write | none known |
| Ask before commit / push / PR | Claude Code permission rules, if you accepted them in setup | other command forms (`git -C . push`, `sh -c`, scripts) aren't matched; use the sandbox network allowlist or branch protection for a hard guarantee |
| Model ceiling (no Fable, no `xhigh`/`max`, Sonnet and Haiku ≤ medium) | `cap-model.sh`: globally when loaded as a plugin, and from the skill's own hook once `/sharaqi` runs | outside `/sharaqi` sessions a call with no `model` passes unchecked; if the script path doesn't resolve, the skill hook fails open |
| Every Agent call names a model | `cap-model.sh --require-model`, while `/sharaqi` is active | the `model` key is matched in the hook input as text, not parsed |
| Orchestrator on Opus · medium | `model`/`effort` in `SKILL.md` frontmatter | the `/sharaqi` turn only; ignored if your organisation's `availableModels` excludes it |
| No code in plans or briefs; implementers don't commit | instruction only | the implementer has Bash, so permission rules from setup are the real guard on commit and push |
| Nothing leaves the machine (publish, email, tickets) | instruction only | the model can still do it |
| No claimed checks without a run; secrets by location only | instruction only | — |

Tests and reviewers lower risk. They don't prove a change correct or secure,
and the report doesn't say they do.

## Not measured yet

v0.6 has not been benchmarked against v0.5 or a plain Claude Code session. The v0.4
numbers above come from one task. The comparison that would settle it:

1. Three tasks on one repo: one FAST (copy or style), one STANDARD (bug or
   small feature), one CRITICAL (a permission check).
2. Run each task twice from the same commit, in a new session each time:
   once as a plain prompt, once as `/sharaqi do`. Use the same model and
   effort for both.
3. Record `tokens.py` output, wall-clock minutes, whether hidden acceptance
   tests pass, and review findings that turned out real.

Until that's done, treat claims that sharaqi is cheaper or safer as
unproven.

## Tests

```bash
bash tests/test_hooks.sh
python3 -m unittest discover -s tests
```

## License

MIT. See [LICENSE](LICENSE).
