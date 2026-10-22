# Setup (`/sharaqi setup`)

Optional and run once. It edits the user's global `~/.claude/settings.json`, so
every change needs the user's answer first.

Claude Code compacts automatically when the context reaches the auto-compact
window. With a smaller window each turn re-reads less, so compaction comes
sooner and each turn costs less.

1. Read `~/.claude/settings.json` (create `{}` if missing). Show the current
   `autoCompactWindow` and any `modelSettings.*.autoCompactWindow` (those
   override the top-level value for their model).
2. AskUserQuestion: window size. Options: **200000 (Recommended)** · 150000 ·
   300000 · keep current. Explain in one line: smaller means cheaper turns
   but more frequent compactions, and each compaction also costs tokens.
3. On a choice, set the top-level `"autoCompactWindow": <n>` with a JSON-aware
   edit that keeps every other key. Tell the user it applies from the next
   session, and that `/autocompact` changes it per model later.
4. AskUserQuestion: block dependency folders in every session? Explain in one
   line: a single wrong search in `vendor/` or `node_modules/` can cost tens
   of thousands of tokens, but this also stops the user from asking Claude to
   read a package's source. Options: **Yes (Recommended)** · No.
   On yes, add these to `permissions.deny`, keeping existing entries and not
   adding duplicates: `Read(vendor/**)`, `Read(node_modules/**)`,
   `Read(storage/logs/**)`, `Read(public/build/**)`, `Read(bootstrap/cache/**)`.
   To undo, delete those lines.
