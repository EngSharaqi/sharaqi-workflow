#!/usr/bin/env bash
# Blocks any subagent spawn above Opus 5.5 at high effort, and Sonnet or Haiku above medium.
# Two places run it:
#   - hooks/hooks.json, when Claude Code loads sharaqi as a plugin (marketplace, or a skills
#     folder with .claude-plugin/): every Agent call in every session.
#   - SKILL.md frontmatter with --require-model, from the moment /sharaqi runs until the
#     session ends: also blocks an Agent call that names no model, because such a subagent
#     inherits the session's model or takes one from its agent file, and nothing here sees it.
# Matches top-level JSON keys only: a key inside the prompt string is escaped (\"model\"),
# so the [{,] prefix never matches it. No jq needed (Git Bash on Windows has grep).
# Opt out for one session: SHARAQI_ALLOW_ABOVE_CAP=1

[ "${SHARAQI_ALLOW_ABOVE_CAP:-0}" = "1" ] && exit 0

# Join lines so pretty-printed JSON ({\n"model": ...) still matches.
input=$(tr '\r\n' '  ')

key() { printf '%s' "$input" | grep -Eiq "[{,][[:space:]]*\"$1\"[[:space:]]*:[[:space:]]*\"$2\""; }

if [ "$1" = "--require-model" ] && ! key model '[^"]+'; then
  echo "Blocked by sharaqi: name the model in every Agent call (haiku, sonnet or opus) and its effort, so nothing inherits the session's model." >&2
  exit 2
fi

if key model '[^"]*(fable|mythos)[^"]*'; then
  echo "Blocked by sharaqi: models above Opus are not allowed. Use opus (max effort high), sonnet or haiku." >&2
  exit 2
fi

if key effort '(xhigh|max)'; then
  echo "Blocked by sharaqi: effort above high is not allowed. Use high, medium or low." >&2
  exit 2
fi

if key model '[^"]*(sonnet|haiku)[^"]*' && key effort 'high'; then
  echo "Blocked by sharaqi: Sonnet and Haiku run at medium or lower. Use medium, or opus/medium for harder work." >&2
  exit 2
fi

exit 0
