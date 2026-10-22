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
an Opus reviewer checked every run. Measured on real tasks, it cost about
8× more and took about 20× longer than doing the same task directly. The
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

Start a new session afterwards. Optional: `/sharaqi setup` offers a smaller
auto-compact window and blocks reads of dependency folders. It asks before
each change to `~/.claude/settings.json`.

Python 3 is needed only for the token report. Without it, the report says
`unavailable`.

## What's inside

| Path | Role |
|---|---|
| `SKILL.md` | the workflow and rules |
| `references/triage.md` | risk factors and the three modes |
| `references/review.md` | post-diff scan; when and how to use the reviewer |
| `references/security-checklist.md` | security items for CRITICAL (and any that apply elsewhere) |
| `references/delegation.md` | when a subagent is worth its cost |
| `references/setup.md` | `/sharaqi setup` |
| `agents/reviewer.md` | read-only reviewer: spec · quality · security, returns findings |
| `hooks/cap-model.sh` | blocks subagents above Opus/high, and Sonnet above medium |
| `hooks/session-hints.sh` | suggests a fresh session after repeated compactions |
| `scripts/tokens.py` | token usage from the local transcript, priced at API list rates |

## Token numbers

`scripts/tokens.py` reads the session transcript Claude Code writes locally.
It keeps the last line of each API response (earlier lines carry partial
output counts) and prices each request at list rates for its model. That
dollar figure is an API-equivalent estimate, not a bill. Subscription plans
aren't charged per token.

## Safety rails

- Nothing leaves the machine (commit, push, PR, publish, email, tickets)
  without an explicit yes for that exact action.
- No checks are claimed without having run. Tests and reviewers lower risk;
  they don't prove correctness or security.
- Secrets are reported by location, never by value.

## License

MIT. See [LICENSE](LICENSE).
