#!/bin/bash
# PreToolUse logger for the benchmark: one line per tool call, "<tool> marker=<yes|no>", where
# marker says whether sharaqi's run marker exists for this session. No session id is logged.
in=$(cat)
sid=$(printf '%s' "$in" | jq -r '.session_id // empty')
tool=$(printf '%s' "$in" | jq -r '.tool_name // "?"')
f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state/$sid.run"
[ -n "$sid" ] && [ -f "$f" ] && m=yes || m=no
echo "$tool marker=$m" >> "$1"
exit 0
