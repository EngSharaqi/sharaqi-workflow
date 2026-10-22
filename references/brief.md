# Writing a brief for the implementer

The implementer starts with no memory of this conversation. It sees the brief,
its own short instructions (`agents/implementer.md`) and the repo. If a fact
or constraint is not in the brief or findable in the repo, it doesn't exist for
the implementer. A brief that assumes context is the most common failure.

## Rules

- **Pointers, not content.** Paths, function and type names, line ranges,
  the existing pattern to follow ("same shape as `useTrainingsQuery` in
  `src/services/trainings/queries.ts`"). Don't paste file contents.
- **No code.** Not in the plan, not in the brief. Name what to build and
  where; the implementer writes it once. A function or type *name* or a
  signature it must match is a fact, not code.
- **One bounded job per brief.** A plan with several slices gets one brief per
  slice. A later brief restates any fact an earlier slice settled (a helper's
  name, a file's location), because the new implementer never saw it.
- **Real checks.** Copy the repo's actual commands from `CLAUDE.md`,
  `package.json`, `Makefile` and the like. "Run the tests" gets guessing.
- **Premises freeze at dispatch.** Check the facts before sending. If one
  turns out wrong while the agent runs, stop it and send a corrected brief.

## Template

Keep the blocks the task needs; drop the empty ones.

```
<task>
One or two sentences: the concrete job and where it lives. Current state, what
to change.
</task>

<acceptance>
- criterion, as observable behaviour
</acceptance>

<files>
Touch: <paths>
Follow: <existing pattern, by path and name>
Leave untouched: <paths, modules, behaviour; tests' existing assertions>
</files>

<facts>
Only what the implementer can't find cheaply: the cause you already found, a
decision made in the plan, a name an earlier slice settled. Omit if none.
</facts>

<checks>
<exact commands> — fix what they surface. Confirm `git status` shows only the
intended files.
</checks>
```

The report format is in the implementer's own instructions; don't repeat it.

## Rework

A fix goes back to the **same** agent with `SendMessage` (its agent id from
the Agent result), so it keeps the files it already read. Send only the delta:
the finding, its `file:line`, and what correct looks like.
