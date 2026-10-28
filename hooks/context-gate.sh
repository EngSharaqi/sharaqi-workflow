#!/usr/bin/env bash
# PreToolUse on Agent|Task|Edit|Write|NotebookEdit: stops the main session once its context
# reaches the gate in scripts/prices.json (context.warn_pct warns, context.max_pct blocks).
# Fails closed: when the context can't be verified, the call is blocked with the reason.
# Read-only tools are not matched, so they keep working.
# Flags:
#   --in-run  do nothing unless this session ran /sharaqi (the same run marker and TTL as
#             hooks/cap-model.sh --in-run; that script is not changed).
# A call with a non-empty agent_id comes from a subagent, which has its own context: allowed.
# Python for scripts/tokens.py: python3, then python. SHARAQI_PYTHON overrides it (the tests
# use a missing path to simulate no interpreter).
# Exit: 0 allowed (a warning on stderr at warn_pct), 2 blocked (the reason on stderr).

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"
tokens="$here/../scripts/tokens.py"
RUN_TTL_MIN=1440 # keep equal to cap-model.sh and session-hints.sh
hint="context can't be verified; set up the statusline bridge (references/setup.md) or check /context. Read-only tools still work."

in_run=0
for a in "$@"; do
  case "$a" in --in-run) in_run=1 ;; esac
done

block() { # reason lines...
  printf '%s\n' "$@" >&2
  exit 2
}

run_live() { # session -> 0 when this session ran /sharaqi within RUN_TTL_MIN
  case "$1" in "" | *[!A-Za-z0-9_-]*) return 1 ;; esac
  local f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state/$1.run"
  [ -f "$f" ] && [ -n "$(find "$f" -mmin -"$RUN_TTL_MIN" 2>/dev/null)" ]
}

input=$(cat)
why=""
line=$(json_fields "$input" session_id agent_id transcript_path)
rc=$?
if [ "$rc" -eq 0 ]; then
  IFS=$'\x1f' read -r sid agent tpath <<<"$line"
else
  agent=""
  tpath=""
  if [ "$rc" -eq 3 ]; then
    why="hook input is not valid JSON, so the context can't be read."
  else
    why="no JSON parser (jq or python3) to read the hook input."
  fi
  sid=$(printf '%s' "$input" | tr '\r\n' '  ' \
    | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
fi

if [ "$in_run" = 1 ] && ! run_live "$sid"; then
  # No live marker: not a run. Only an unreadable payload with no session id to look up is
  # blocked, since then the session can't be told apart from a run.
  case "$sid" in "" | *[!A-Za-z0-9_-]*) [ -n "$why" ] && block "$why" "$hint" ;; esac
  exit 0
fi

[ -n "$why" ] && block "$why" "$hint"

# A subagent's own calls are not the main session's context.
[ -n "$agent" ] && exit 0

py="${SHARAQI_PYTHON:-}"
[ -z "$py" ] && py=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$py" ] || ! command -v "$py" >/dev/null 2>&1; then
  block "python3 not found, so scripts/tokens.py can't run." "$hint"
fi

args=(--context)
[ -n "$sid" ] && args+=(--session "$sid")
[ -n "$tpath" ] && args+=(--transcript "$tpath")
out=$("$py" -I "$tokens" "${args[@]}" 2>/dev/null)
rc=$?
[ -n "$out" ] || out="context check failed (scripts/tokens.py exit $rc)"

case "$rc" in
  0) exit 0 ;;
  3) printf '%s\n' "$out" >&2; exit 0 ;;
  4) block "$out" "run /compact, then continue" ;;
  *) block "$out" "$hint" ;;
esac
