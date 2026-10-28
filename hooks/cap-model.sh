#!/usr/bin/env bash
# PreToolUse on Agent|Task: blocks a subagent spawn above the model ceiling in
# scripts/prices.json (never Fable or Mythos; Opus, Sonnet and Haiku at
# most high effort). The effort checked is the call's own `effort` when it has one (Claude Code
# 2.1.292+), else the `effort:` in the frontmatter of the named sharaqi agent file
# (subagent_type sharaqi:<name> -> agents/<name>.md), which is what a subagent runs at on
# 2.1.274 (a captured run showed it). Other agents' effort isn't visible here.
# Flags:
#   --require-model  also block a call that names no model: it would inherit the session's
#                    model or take one from its agent file, and nothing here sees either.
#   --in-run         do nothing unless this session ran /sharaqi. session-hints.sh writes
#                    <config>/sharaqi-state/<session>.run on that prompt, refreshes it on each
#                    later prompt, and removes it at SessionEnd. A marker older than
#                    RUN_TTL_MIN (a crashed session that never reached SessionEnd) is ignored.
# hooks/hooks.json runs it with both flags; SKILL.md frontmatter with --require-model.
# Input is parsed with jq or python (hooks/json.sh).
#   Malformed input: blocked with --require-model alone (we know a run is active). With
#   --in-run, or no flag, it's allowed with a warning on stderr, because a global hook that
#   fails closed would block every Agent call in every session.
#   No parser (or the parser itself failed): keys are matched as text, model and effort only
#   after "tool_input". A key inside the prompt string is escaped (\"model\"), so the [{,]
#   prefix never matches it. Text matching blocks only what it reads clearly: a blocked model
#   name, or an effort above the cap. When it can't tell (no "tool_input", a model key whose
#   value isn't a plain string, no session id under --in-run) it allows the call and warns on
#   stderr. A tool_input with no model key at all is still blocked under --require-model.
# Opt out for one session: SHARAQI_ALLOW_ABOVE_CAP=1

[ "${SHARAQI_ALLOW_ABOVE_CAP:-0}" = "1" ] && exit 0

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"
prices="$here/../scripts/prices.json"

require=0
in_run=0
for a in "$@"; do
  case "$a" in
    --require-model) require=1 ;;
    --in-run) in_run=1 ;;
  esac
done

warn() { echo "sharaqi cap-model: $*" >&2; }
block() { echo "Blocked by sharaqi: $*" >&2; exit 2; }

input=$(cat)

# Text fallback: the value of a string key, or empty. model and effort are looked up only
# after "tool_input", because the payload's top-level effort is the parent turn's.
text_key() { # key [text]
  printf '%s' "${2-$input}" | tr '\r\n' '  ' \
    | grep -Eio "[{,][[:space:]]*\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 \
    | sed 's/.*"\([^"]*\)"$/\1/'
}

line=$(json_fields "$input" tool_input.model tool_input.effort session_id tool_input.subagent_type)
case $? in
  0) IFS=$'\x1f' read -r model effort sid agent <<<"$line" ;;
  3)
    if [ "$require" = 1 ] && [ "$in_run" = 0 ]; then
      block "the hook input is not valid JSON, so the model ceiling can't be checked."
    fi
    warn "hook input is not valid JSON; this Agent call was not checked."
    exit 0
    ;;
  *)
    textmode=1
    after="${input#*\"tool_input\"}"
    [ "$after" = "$input" ] && after=""
    model=$(text_key model "$after")
    effort=$(text_key effort "$after")
    agent=$(text_key subagent_type "$after")
    sid=$(text_key session_id)
    ;;
esac

if [ "$in_run" = 1 ]; then
  if [ -z "$sid" ] && [ "${textmode:-0}" = 1 ]; then
    warn "no JSON parser (jq or python) and no readable session_id; this Agent call was not checked."
    exit 0
  fi
  case "$sid" in "" | *[!A-Za-z0-9_-]*) exit 0 ;; esac
  RUN_TTL_MIN=1440 # 24 hours since the session's last prompt; keep equal to session-hints.sh
  run_f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state/$sid.run"
  [ -f "$run_f" ] || exit 0
  [ -n "$(find "$run_f" -mmin -"$RUN_TTL_MIN" 2>/dev/null)" ] || exit 0
fi

# Ceiling. The defaults apply only when prices.json can't be read; a test keeps them equal.
DEFAULT_CEILING="fable|mythos high high high high"
ceiling=$(json_fields "$(cat "$prices" 2>/dev/null)" ceiling.blocked_models \
  ceiling.max_effort.opus ceiling.max_effort.sonnet ceiling.max_effort.haiku ceiling.max_effort.other)
if [ $? -eq 0 ]; then
  IFS=$'\x1f' read -r blocked max_opus max_sonnet max_haiku max_other <<<"$ceiling"
  blocked=$(printf '%s' "$blocked" | tr -d '[]" ' | tr ',' '|')
else
  read -r blocked max_opus max_sonnet max_haiku max_other <<<"$DEFAULT_CEILING"
fi

# Text mode can't tell a missing model from one it failed to read: allow, and say so.
flat=$(printf '%s' "$after" | tr '\r\n' '  ')
if [ -z "$model" ] && [ "${textmode:-0}" = 1 ] && { [ -z "$after" ] || {
  printf '%s' "$flat" | grep -Eq '[{,][[:space:]]*"model"[[:space:]]*:' \
    && ! printf '%s' "$flat" | grep -Eq '[{,][[:space:]]*"model"[[:space:]]*:[[:space:]]*"'; }; }; then
  warn "no JSON parser (jq or python) and the model couldn't be read as text; this Agent call was not checked."
  model_unread=1
fi

if [ -z "$model" ] && [ "$require" = 1 ] && [ "${model_unread:-0}" = 0 ]; then
  block "name the model in every Agent call (haiku, sonnet or opus), so nothing inherits the session's model."
fi

m=$(printf '%s' "$model" | tr '[:upper:]' '[:lower:]')
e=$(printf '%s' "$effort" | tr '[:upper:]' '[:lower:]')

if [ -n "$m" ] && printf '%s' "$m" | grep -Eq "$blocked"; then
  block "models above Opus are not allowed. Use opus (max effort $max_opus), sonnet or haiku."
fi

# No effort on the call: a sharaqi agent runs at its file's effort, so check that.
src="the call"
if [ -z "$e" ]; then
  case "$agent" in
    sharaqi:*)
      name="${agent#sharaqi:}"
      case "$name" in "" | *[!a-z0-9-]*) name="" ;; esac
      if [ -n "$name" ] && [ -f "$here/../agents/$name.md" ]; then
        e=$(sed -n '1{/^---$/!q;};2,/^---$/{s/^effort:[[:space:]]*\([A-Za-z]*\).*/\1/p;}' "$here/../agents/$name.md" \
          | head -1 | tr '[:upper:]' '[:lower:]')
        src="agents/$name.md"
      fi
      ;;
  esac
fi

[ -z "$e" ] && exit 0

rank() {
  case "$1" in
    low) echo 1 ;; medium) echo 2 ;; high) echo 3 ;; xhigh) echo 4 ;; max) echo 5 ;; *) echo 9 ;;
  esac
}

case "$m" in
  *opus*) cap="$max_opus" ;;
  *sonnet*) cap="$max_sonnet" ;;
  *haiku*) cap="$max_haiku" ;;
  *) cap="$max_other" ;;
esac

if [ "$(rank "$e")" -gt "$(rank "$cap")" ]; then
  case "$m" in
    *haiku*) block "Haiku runs at $cap effort or lower (effort '$e' from $src). Use effort high or lower on the call, or a sonnet rung for harder work." ;;
    *) block "effort '$e' (from $src) is above the ceiling for ${m:-this model} ($cap). Use $cap or lower." ;;
  esac
fi
exit 0
