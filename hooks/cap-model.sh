#!/usr/bin/env bash
# Blocks any subagent spawn above Opus 5.5 at high effort.
# Matches top-level JSON keys only: a key inside the prompt string is escaped (\"model\"),
# so the [{,] prefix never matches it. No jq needed (Git Bash on Windows has grep).
# Opt out for one session: SHARAQI_ALLOW_ABOVE_CAP=1

[ "${SHARAQI_ALLOW_ABOVE_CAP:-0}" = "1" ] && exit 0

input=$(cat)

if printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"model"[[:space:]]*:[[:space:]]*"[^"]*(fable|mythos)[^"]*"'; then
  echo "Blocked by sharaqi: models above Opus are not allowed. Use opus (max effort high), sonnet or haiku." >&2
  exit 2
fi

if printf '%s' "$input" | grep -Eiq '[{,][[:space:]]*"effort"[[:space:]]*:[[:space:]]*"(xhigh|max)"'; then
  echo "Blocked by sharaqi: effort above high is not allowed. Use high, medium or low." >&2
  exit 2
fi

exit 0
