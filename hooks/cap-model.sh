#!/usr/bin/env bash
# Blocks any subagent spawn above Opus 5.5 at high effort, and Sonnet above medium.
# Runs only when Claude Code loads sharaqi as a plugin (marketplace, or a skills folder
# with .claude-plugin/), and then for every Agent call in every session, not only /sharaqi.
# Limits: it checks only the model/effort written in the Agent call. A subagent that
# inherits the session's model, or takes it from its own agent file, passes unchecked.
# Matches top-level JSON keys only: a key inside the prompt string is escaped (\"model\"),
# so the [{,] prefix never matches it. No jq needed (Git Bash on Windows has grep).
# Opt out for one session: SHARAQI_ALLOW_ABOVE_CAP=1

[ "${SHARAQI_ALLOW_ABOVE_CAP:-0}" = "1" ] && exit 0

# Join lines so pretty-printed JSON ({\n"model": ...) still matches.
input=$(tr '\r\n' '  ')

if printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"model"[[:space:]]*:[[:space:]]*"[^"]*(fable|mythos)[^"]*"'; then
  echo "Blocked by sharaqi: models above Opus are not allowed. Use opus (max effort high), sonnet or haiku." >&2
  exit 2
fi

if printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"effort"[[:space:]]*:[[:space:]]*"(xhigh|max)"'; then
  echo "Blocked by sharaqi: effort above high is not allowed. Use high, medium or low." >&2
  exit 2
fi

if printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"model"[[:space:]]*:[[:space:]]*"[^"]*sonnet[^"]*"' \
  && printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"effort"[[:space:]]*:[[:space:]]*"high"'; then
  echo "Blocked by sharaqi: Sonnet runs at medium or lower. Use sonnet/medium, or opus/medium for harder work." >&2
  exit 2
fi

exit 0
