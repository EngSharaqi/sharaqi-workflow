# sharaqi

A Claude Code skill for development tasks. The main session does the work. The
skill makes it assess risk before editing and again on the actual diff, scale
checks and review to that risk, and finish with a report that states only
what was actually verified.

```
/sharaqi do <task>
```

## Why v0.5 changed direction

v0.4 was a pipeline: an Opus planner wrote cards, cheaper models built them,
an Opus reviewer checked every run. On one real task, it cost about 8× more
and took about 20× longer than doing the same task directly. The
handoffs, re-reads and cache re-reads on the Opus steps outweighed what the
cheap builders saved. Its "tokens saved" report re-priced the pipeline itself
instead of comparing it with direct work, and it undercounted output tokens.

v0.5 keeps what held up (risk-aware review, the security checklist, cheap
context habits, the model ceiling) and drops the rest.

## How a task runs

1. **Understand**: one-line task statement and acceptance criteria, from the
   user's words. Questions only when the answer changes what gets built.
2. **Assess risk before editing**: FAST, STANDARD or CRITICAL, from semantic
   risk, uncertainty, coupling, test coverage and blast radius. Line count
   is a signal only. See [references/triage.md](references/triage.md).
3. **Implement** in the main session.
4. **Verify** with the repo's own checks, in proportion to the mode.
5. **Reassess on the diff**, which can raise the mode but never lowers it, then review
   ([references/review.md](references/review.md)):

   | Mode | Review |
   |---|---|
   | FAST | self-review of the diff |
   | STANDARD | self-review; independent reviewer only when the risk justifies it, with the reason stated |
   | CRITICAL | mandatory read-only `reviewer` agent, [security checklist](references/security-checklist.md), user approval before risky actions |

6. **Report**: what changed, which checks ran and what they showed, mode,
   review, delegation, acceptance criteria, risks and unknowns, and token
   usage from the local transcript (or `unavailable`).

Subagents are used only for a concrete reason: broad exploration, truly
parallel workstreams, risk-justified review, or a job a cheaper model has been
shown to do as well. See [references/delegation.md](references/delegation.md).

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

The hooks in `hooks/` and the `reviewer` agent load only when Claude Code
loads the folder as a plugin. Both installs above do that on current Claude
Code: the skills-folder clone contains `.claude-plugin/plugin.json`, so it is
listed as `sharaqi@skills-dir` under `claude plugin list`. Check that list. If
sharaqi isn't in it, the hooks aren't running and the model ceiling is only an
instruction. When they do load, the hooks apply to every session, not only to
`/sharaqi` runs.

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
| `references/delegation.md` | when a subagent is worth its cost |
| `references/setup.md` | `/sharaqi setup` |
| `agents/reviewer.md` | reviewer with Read/Grep/Glob only: spec · quality · security, returns findings |
| `hooks/cap-model.sh` | when loaded as a plugin: blocks Agent calls that ask for a model above Opus/high, or Sonnet above medium |
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
| Model ceiling (no Fable, no `xhigh`/`max`, Sonnet ≤ medium) | `cap-model.sh`, when loaded as a plugin | can't see a model that is inherited or set in an agent file; the skill tells the model to always pass `model` explicitly |
| Nothing leaves the machine (publish, email, tickets) | instruction only | the model can still do it |
| No claimed checks without a run; secrets by location only | instruction only | — |

Tests and reviewers lower risk. They don't prove a change correct or secure,
and the report doesn't say they do.

## Not measured yet

v0.5 has not been benchmarked against a plain Claude Code session. The v0.4
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
