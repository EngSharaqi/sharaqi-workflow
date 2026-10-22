# Setup (`/sharaqi setup`)

Optional and run once. It edits Claude Code settings files, so every change
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

SKILL.md rule 4 is advice to the model. Permission rules are enforced by
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
