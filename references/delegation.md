# Delegation — when a subagent is worth its cost

Default: none. A subagent starts a fresh context, re-reads files you may
already have read, and hands back a summary you then have to trust or check.
In measured sharaqi v0.4 runs, the handoffs and re-reads cost more than the
cheaper models saved. Delegate only when one of these holds, and print one
line first: `▶ <agent> · <model>/<effort> — <reason>`.

| Reason | Agent | Model / effort |
|---|---|---|
| Broad exploration: many files, directories or naming conventions, where you only need the conclusion | `Explore` | `haiku`; `sonnet` / `medium` when the search needs judgement |
| Genuinely parallel workstreams: two or more independent parts that touch different files and each need substantial work | `general-purpose`, one per part | `sonnet` / `medium` for well-specified parts; `opus` / `medium` when a part needs judgement |
| Independent review justified by risk | `reviewer` (this skill) | see review.md |
| A specialised job a cheaper model has been shown to do as well, at lower total cost | whichever agent fits | the cheaper model |

Not reasons:
- "It's a big task." Size alone doesn't decide this; coupled work belongs in one context.
- Anything you could do in about five tool calls.
- Writing a plan or code for another model to copy.
- Work that touches the same files as another stream.

When you delegate:
- Give the intent, acceptance criteria, files, constraints and how to verify,
  as paths and facts. Don't paste file contents.
- Read what comes back critically, and check its diff yourself. A subagent's
  "done" is a claim, not evidence.
- Name each delegation and its reason in the final report.

Always pass `model` explicitly in the Agent call, and `effort` where the table
gives one. A subagent with no `model` inherits this session's model, which may
be above the ceiling.

Ceiling: never `fable`, never effort `xhigh` or `max`, never Sonnet above
`medium`. Keeping to it is your job. When sharaqi is installed as a plugin,
`hooks/cap-model.sh` also blocks Agent calls that state a value above it, but
it can't see a model that is inherited or set in an agent's own file. When it
is installed as a plain skill, no hook runs at all.
