# Security

## Reporting

Report a vulnerability privately through GitHub's
[security advisories](https://github.com/EngSharaqi/sharaqi-workflow/security/advisories/new)
for this repository, not in a public issue. Include the file, what an
attacker controls, and what they get.

## What the plugin's code can do

The plugin ships Markdown instructions, two agent definitions, three hook
scripts and one Python script. None of them opens a network connection.

| Component | Runs when | Reads | Writes |
|---|---|---|---|
| `hooks/cap-model.sh` | before every Agent/Task call (PreToolUse) | the hook's JSON on stdin, `scripts/prices.json`, whether `<config>/sharaqi-state/<session>.run` exists and its age | nothing; it can only block the call (exit 2) |
| `hooks/session-hints.sh` | on each prompt, after compaction, at session end | the hook's JSON on stdin | `<config>/sharaqi-state/<session>.{run,compacts,hinted}`; deletes run markers older than 24 h and other state older than 7 days in that folder |
| `hooks/json.sh` | sourced by the two hooks | its arguments | nothing |
| `scripts/tokens.py` | when the skill reports tokens | session transcripts under `<config>/projects/`, `scripts/prices.json` | nothing (stdout only) |

`<config>` is `$CLAUDE_CONFIG_DIR`, or `~/.claude`.

What the hooks can't do: check an effort the Agent call doesn't carry (on
Claude Code 2.1.274 it never does; the agent file's `effort:` applies), act
outside a session that ran `/sharaqi`, or control what the model does with
Bash.
The rules about commits, pushes and publishing are instructions to the
model; the enforced guard is Claude Code's permission rules
(`/sharaqi setup` offers them).
