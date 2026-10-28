#!/usr/bin/env bash
# statusLine command. Records the context window Claude Code reports for this session, so
# scripts/tokens.py --context can verify the window instead of guessing it from the model name.
#   statusline-bridge.sh            prints "ctx <pct>%"
#   statusline-bridge.sh <cmd...>   runs <cmd...> with the same stdin and prints its output, to
#                                   wrap an existing statusline
# Writes <config>/sharaqi-state/<session>.ctx (JSON, replaced atomically). Always exits 0 and
# never prints an error on stdout.

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"

input=$(cat)
dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state"

if line=$(json_fields "$input" session_id model.id context_window.context_window_size \
  context_window.used_percentage context_window.total_input_tokens 2>/dev/null); then
  IFS=$'\x1f' read -r sid model window pct tokens <<<"$line"
  case "$sid" in "" | *[!A-Za-z0-9_-]*) sid="" ;; esac
  [[ $window =~ ^[0-9]+$ ]] || window=""
  [[ $pct =~ ^[0-9]+(\.[0-9]+)?$ ]] || pct=""
  [[ $tokens =~ ^[0-9]+$ ]] || tokens=""
  model=$(printf '%s' "$model" | tr -cd 'A-Za-z0-9._[]-')

  if [ -n "$sid" ] && mkdir -p "$dir" 2>/dev/null; then
    body="{\"window\":${window:-null},\"used_percentage\":${pct:-null},\"total_input_tokens\":${tokens:-null},\"model\":\"$model\",\"ts\":$(date +%s)}"
    tmpf=$(mktemp "$dir/.$sid.XXXXXX" 2>/dev/null) && {
      if printf '%s\n' "$body" > "$tmpf" 2>/dev/null && mv -f "$tmpf" "$dir/$sid.ctx" 2>/dev/null; then
        :
      else
        rm -f "$tmpf" 2>/dev/null
      fi
    }
  fi
fi

if [ "$#" -gt 0 ]; then
  printf '%s' "$input" | "$@" 2>/dev/null
  exit 0
fi

if [ -n "${pct:-}" ]; then
  printf 'ctx %s%%\n' "$pct"
else
  printf 'ctx ?\n'
fi
exit 0
