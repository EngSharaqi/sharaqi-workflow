# Setup (`/sharaqi setup`)

Run once. Steps 1–3 and 5 are optional; step 4 is needed for the context gate. It edits Claude Code settings files, so every change
needs the user's answer first. Each step can be skipped. Make every edit
JSON-aware: keep all other keys and existing entries, and add no duplicates.

## 1. Auto-compact window (global)

Claude Code compacts automatically when the context reaches the auto-compact
window. With a smaller window each turn re-reads less, so compaction comes
sooner and each turn costs less.

1. Read `~/.claude/settings.json` (create `{}` if missing). Show the current
   `autoCompactWindow` and any `modelSettings.*.autoCompactWindow` (those
   override the top-level value for their model).
2. AskUserQuestion: window size. Options: **200000 (Recommended)** · 150000 ·
   300000 · keep current. Explain in one line: smaller means cheaper turns
   but more frequent compactions, and each compaction also costs tokens.
3. On a choice, set the top-level `"autoCompactWindow": <n>`. Tell the user it
   applies from the next session, and that `/autocompact` changes it per model
   later.

## 2. Ask before anything leaves the machine (global)

SKILL.md rule 6 is advice to the model. Permission rules are enforced by
Claude Code itself.

AskUserQuestion: make Claude Code ask before commits, pushes and PRs, in every
project? Options: **Yes (Recommended)** · No. Explain in one line: you get a
prompt each time, even when you asked for the commit.

On yes, add to `permissions.ask` in `~/.claude/settings.json`:
`Bash(git commit *)`, `Bash(git push *)`, `Bash(gh pr *)`.

Tell the user plainly what this does not cover: these rules match the usual
command forms only. `git -C dir push`, `sh -c "git push"`, a script that pushes,
or another tool can still get through. For a hard guarantee, use Claude Code's
sandbox network allowlist or branch protection on the remote. To undo, delete
those lines.

## 3. Skip dependency and build folders (this project only)

A single wrong search in a dependency folder can cost tens of thousands of
tokens.

1. Check which of these exist in the current repo root: `vendor/`,
   `node_modules/`, `dist/`, `build/`, `.next/`, `public/build/`,
   `storage/logs/`, `bootstrap/cache/`, `.venv/`, `__pycache__/`, `target/`.
   Offer only the ones that exist. If none do, say so and skip this step.
2. AskUserQuestion: block reads of these folders in this project? Explain in
   one line: this also stops you from asking Claude to read a package's
   source here. Options: **Yes (Recommended)** · No.
3. On yes, add `Read(<folder>/**)` for each to `permissions.deny` in
   `<repo>/.claude/settings.local.json` (create `{}` if missing). That file is
   per-user and not meant to be committed; if `.gitignore` doesn't already
   exclude it, tell the user rather than editing `.gitignore`. To undo, delete
   those lines.

## 4. Context window source for the 40% gate (global, needed)

`hooks/context-gate.sh` blocks Agent, Edit, Write and NotebookEdit in the main
session of a sharaqi run when context is at or above 40%, **or when it can't
verify the window size**. Hooks don't receive the window size; only Claude
Code's statusLine command does (`context_window.context_window_size`). Without
this step every sharaqi run is blocked at its first edit, by design.

1. Read `statusLine` in `~/.claude/settings.json`. Show it, or say there is
   none.
2. AskUserQuestion: let sharaqi's bridge record the window size from the
   statusline? Explain in one line: it writes one small file per session
   under `sharaqi-state/` and passes the input on to your current statusline,
   whose output stays the same. Options: **Yes (Recommended)** · No.
3. On yes, set `statusLine` to
   `{"type": "command", "command": "bash \"<plugin root>/hooks/statusline-bridge.sh\" <current command, if any>"}`.
   It applies from the next statusline refresh.

Limits to tell the user: the statusline runs only where Claude Code draws
one; if an editor integration doesn't run it, the gate stays blocked there
(check with `tokens.py --context`). The reading counts the context up to the
last API call, not tool output since. Subagents' own contexts aren't
measured. The gate's 35% warning goes to the hook's stderr, which the model
doesn't see on an allowed call; v1.0 has the model run no context checks of its
own, so the warning is in the events log only. Nothing runs `/compact` for
you: the gate stops work, you compact.

Headless runs (`claude -p`) draw no statusline, so the window can't be verified
there. A benchmark declares it instead: `SHARAQI_BENCHMARK=1` with
`SHARAQI_CONTEXT_WINDOW=<tokens>`. The thresholds stay the same and the gate
says the window was declared, not verified. `SHARAQI_CONTEXT_WINDOW` alone does
nothing. Don't set either in an interactive session; use the bridge.

## 5. Auto-compact at 40% (global, optional)

`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` makes Claude Code compact on its own at a
percentage of the window less the output reserve, so at slightly under 40% of
the full window. It is documented in Claude Code's environment variables
(code.claude.com/docs/en/env-vars, checked 2026-10-28): 1–100, it can only
lower the threshold, and it applies to subagents too. The gate above works
without it.

AskUserQuestion: add `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "40"}` to
`~/.claude/settings.json`? Options: **No (Recommended)** · Yes. On yes, it
applies from the next session; to undo, delete the key.
