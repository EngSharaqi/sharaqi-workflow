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
# Headless benchmark runs (no statusline) declare the window: SHARAQI_BENCHMARK=1 and
# SHARAQI_CONTEXT_WINDOW=<tokens> (scripts/tokens.py). The thresholds don't change.
# A transcript that doesn't exist yet or has no usage entry yet (the first tool call of a
# session, seen in headless runs on 2.1.312) is re-read up to 5 times, 0.3 s apart, before it
# counts as unverified.
# Every decision in a run is logged to <config>/sharaqi-state/<session>.events.jsonl with a
# reason class (ok, warn, stop, unverified-window, unverified-transcript, no-python,
# bad-input, error), so a blocked call can't pass for a delegation.
# Exit: 0 allowed (a warning on stderr at warn_pct), 2 blocked (the reason on stderr).

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"
tokens="$here/../scripts/tokens.py"
RUN_TTL_MIN=1440 # keep equal to cap-model.sh and session-hints.sh
hint="context can't be verified; set up the statusline bridge (references/setup.md), or in a headless benchmark set SHARAQI_BENCHMARK=1 and SHARAQI_CONTEXT_WINDOW. Read-only tools still work."

in_run=0
for a in "$@"; do
  case "$a" in --in-run) in_run=1 ;; esac
done

tool=""
log() { # decision class
  case "$sid" in "" | *[!A-Za-z0-9_-]*) return ;; esac
  local d="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state"
  mkdir -p "$d" 2>/dev/null && printf '{"event":"gate","ts":"%s","tool":"%s","decision":"%s","class":"%s","bench":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(printf '%s' "$tool" | tr -cd 'A-Za-z')" "$1" "$2" \
    "${SHARAQI_BENCHMARK:-0}" >> "$d/$sid.events.jsonl" 2>/dev/null
}
block() { # class reason lines...
  log block "$1"
  shift
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
line=$(json_fields "$input" session_id agent_id transcript_path tool_name)
rc=$?
if [ "$rc" -eq 0 ]; then
  IFS=$'\x1f' read -r sid agent tpath tool <<<"$line"
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
  case "$sid" in "" | *[!A-Za-z0-9_-]*) [ -n "$why" ] && block bad-input "$why" "$hint" ;; esac
  exit 0
fi

[ -n "$why" ] && block bad-input "$why" "$hint"

# A subagent's own calls are not the main session's context.
[ -n "$agent" ] && exit 0

py="${SHARAQI_PYTHON:-}"
[ -z "$py" ] && py=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$py" ] || ! command -v "$py" >/dev/null 2>&1; then
  block no-python "python3 not found, so scripts/tokens.py can't run." "$hint"
fi

args=(--context)
[ -n "$sid" ] && args+=(--session "$sid")
[ -n "$tpath" ] && args+=(--transcript "$tpath")
for try in 1 2 3 4 5 6; do
  out=$("$py" -I "$tokens" "${args[@]}" 2>/dev/null)
  rc=$?
  [ "$rc" = 5 ] && [ "$try" -lt 6 ] && case "$out" in
    *"no usage entry"* | *"transcript not found"* | *"no transcript found"*) sleep 0.3; continue ;;
  esac
  break
done
[ -n "$out" ] || out="context check failed (scripts/tokens.py exit $rc)"

case "$rc" in
  0) log allow ok; exit 0 ;;
  3) log allow warn; printf '%s\n' "$out" >&2; exit 0 ;;
  4) block stop "$out" "run /compact, then continue" ;;
  5) case "${out##* · }" in # the reason, after the estimate
       *bridge* | *SHARAQI_* | *"window size"*) block unverified-window "$out" "$hint" ;;
       *) block unverified-transcript "$out" "$hint" ;;
     esac ;;
  *) block error "$out" "$hint" ;;
esac
