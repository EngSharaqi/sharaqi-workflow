#!/usr/bin/env bash
# PreToolUse on Agent|Task in a sharaqi run (--in-run: the same run marker as cap-model.sh).
# 1. Opus only by escalation: an Agent call whose model is Opus must start its `description`
#    with `escalate:critical`, `escalate:failed-twice` or `escalate:reasoning` (route.py's
#    escalate values); otherwise it is blocked with the reason.
# 2. Foreground only: the call must set `run_in_background: false`. A background agent ends the
#    /sharaqi turn, and the turn that receives its result runs on the session's model (Opus
#    in the benchmark), not the Sonnet seat: checked on Claude Code 2.1.312 with a stand-in
#    API. Several foreground calls in one message still run side by side.
# 3. Logs every call it sees, allowed or blocked, as one JSON line in
#    <config>/sharaqi-state/<session>.events.jsonl: subagent type, model, effort, escalation,
#    decision. Never the prompt. The log stays outside the model's context.
# Unreadable input (no parser) in a run: an Opus call can't be told apart, so the call is
# allowed with a warning on stderr and logged as unchecked; cap-model.sh still applies.
# Exit: 0 allowed, 2 blocked.

here=$(cd "$(dirname "$0")" && pwd)
. "$here/json.sh"
RUN_TTL_MIN=1440 # keep equal to cap-model.sh and session-hints.sh

in_run=0
for a in "$@"; do case "$a" in --in-run) in_run=1 ;; esac; done

input=$(cat)
line=$(json_fields "$input" session_id tool_input.model tool_input.effort tool_input.subagent_type \
  tool_input.description agent_id)
rc=$?
if [ "$rc" -eq 0 ]; then
  IFS=$'\x1f' read -r sid model effort atype desc parent <<<"$line"
else
  sid=$(printf '%s' "$input" | tr '\r\n' '  ' \
    | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
  model="" effort="" atype="" desc="" parent=""
fi
# json_fields maps false to "", so read run_in_background on its own: true, false or null.
bg=""
if [ "$rc" -eq 0 ]; then
  case "$(json_parser)" in
    jq) bg=$(printf '%s' "$input" | jq -r '.tool_input.run_in_background | tostring' 2>/dev/null) ;;
    python3 | python)
      bg=$(printf '%s' "$input" | "$(json_parser)" -I -c 'import json,sys
v=(json.load(sys.stdin).get("tool_input") or {}).get("run_in_background")
print({True: "true", False: "false"}.get(v, "null"))' 2>/dev/null) ;;
  esac
fi
case "$sid" in "" | *[!A-Za-z0-9_-]*) exit 0 ;; esac
dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sharaqi-state"
if [ "$in_run" = 1 ]; then
  f="$dir/$sid.run"
  [ -f "$f" ] && [ -n "$(find "$f" -mmin -"$RUN_TTL_MIN" 2>/dev/null)" ] || exit 0
fi

clean() { printf '%s' "$1" | tr -cd 'A-Za-z0-9._:@+-' | cut -c1-60; }
m=$(clean "$model"); e=$(clean "$effort"); t=$(clean "$atype"); p=$(clean "$parent")
esc=$(printf '%s' "$desc" | sed -n 's/^[[:space:]]*escalate:\([a-z-]*\).*/\1/p' | head -1)
decision=allow reason=""
if [ "$rc" -ne 0 ]; then
  decision=unchecked
  echo "sharaqi agent-audit: hook input unreadable; escalation not checked." >&2
elif printf '%s' "$m" | grep -qi opus && case "$esc" in critical | failed-twice | reasoning) false ;; *) true ;; esac; then
  decision=block reason=escalation
elif [ "$bg" != "false" ]; then
  decision=block reason=background
fi
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
mkdir -p "$dir" 2>/dev/null && printf '{"event":"agent","ts":"%s","subagent_type":"%s","model":"%s","effort":"%s","escalate":"%s","background":"%s","from_subagent":"%s","decision":"%s","reason":"%s"}\n' \
  "$ts" "$t" "$m" "$e" "$(clean "$esc")" "$(clean "$bg")" "$p" "$decision" "$reason" \
  >> "$dir/$sid.events.jsonl" 2>/dev/null
case "$reason" in
  escalation)
    echo "Blocked by sharaqi: an Opus Agent call needs a logged reason. Start its description with escalate:critical, escalate:failed-twice or escalate:reasoning, as the ROUTE's escalate= says; otherwise use sonnet or haiku." >&2
    exit 2 ;;
  background)
    echo "Blocked by sharaqi: set run_in_background: false. A background agent's result returns in a turn on the session's model, not the Sonnet seat. Several foreground Agent calls in one message still run in parallel." >&2
    exit 2 ;;
esac
exit 0
