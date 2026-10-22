#!/usr/bin/env bash
# Tests for hooks/cap-model.sh and hooks/session-hints.sh. No dependencies beyond bash.
# usage: bash tests/test_hooks.sh

root="$(cd "$(dirname "$0")/.." && pwd)"
cap="$root/hooks/cap-model.sh"
hints="$root/hooks/session-hints.sh"
fail=0
pass=0

check() { # name expected actual
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "FAIL: $1 (expected $2, got $3)"; fi
}

cap_exit() { printf '%s' "$1" | env -u SHARAQI_ALLOW_ABOVE_CAP bash "$cap" >/dev/null 2>&1; echo $?; }

# --- cap-model.sh: blocked
check "fable alias"          2 "$(cap_exit '{"tool_input":{"model":"fable","prompt":"x"}}')"
check "fable full id"        2 "$(cap_exit '{"tool_input":{"model":"claude-fable-5-1"}}')"
check "mythos"               2 "$(cap_exit '{"tool_input":{"model":"Mythos"}}')"
check "effort xhigh"         2 "$(cap_exit '{"tool_input":{"model":"opus","effort":"xhigh"}}')"
check "effort max"           2 "$(cap_exit '{"tool_input":{"effort":"max"}}')"
check "sonnet high"          2 "$(cap_exit '{"tool_input":{"model":"sonnet","effort":"high"}}')"
check "sonnet high reversed" 2 "$(cap_exit '{"tool_input":{"effort":"high","model":"claude-sonnet-5-5"}}')"
check "pretty-printed"       2 "$(cap_exit $'{"tool_input":{\n  "model": "fable"\n}}')"
check "haiku high"           2 "$(cap_exit '{"tool_input":{"model":"haiku","effort":"high"}}')"

# --- cap-model.sh: allowed
check "opus high"            0 "$(cap_exit '{"tool_input":{"model":"opus","effort":"high"}}')"
check "sonnet medium"        0 "$(cap_exit '{"tool_input":{"model":"sonnet","effort":"medium"}}')"
check "haiku no effort"      0 "$(cap_exit '{"tool_input":{"model":"haiku"}}')"
check "keys inside prompt"   0 "$(cap_exit '{"tool_input":{"model":"opus","prompt":"use {\"model\": \"fable\", \"effort\": \"max\"}"}}')"
check "opt-out"              0 "$(printf '%s' '{"tool_input":{"model":"fable"}}' | SHARAQI_ALLOW_ABOVE_CAP=1 bash "$cap" >/dev/null 2>&1; echo $?)"
# Known gap, documented: no model in the call -> nothing to check, unless --require-model.
check "no model (known gap)" 0 "$(cap_exit '{"tool_input":{"subagent_type":"general-purpose"}}')"

# --- cap-model.sh --require-model (registered by SKILL.md while /sharaqi is active)
req_exit() { printf '%s' "$1" | env -u SHARAQI_ALLOW_ABOVE_CAP bash "$cap" --require-model >/dev/null 2>&1; echo $?; }
check "require: no model"         2 "$(req_exit '{"tool_input":{"subagent_type":"implementer","prompt":"x"}}')"
check "require: model in prompt"  2 "$(req_exit '{"tool_input":{"prompt":"use {\"model\": \"haiku\"}"}}')"
check "require: empty model"      2 "$(req_exit '{"tool_input":{"model":""}}')"
check "require: haiku low"        0 "$(req_exit '{"tool_input":{"model":"haiku","effort":"low"}}')"
check "require: still caps"       2 "$(req_exit '{"tool_input":{"model":"fable"}}')"

# --- session-hints.sh
tmp=$(mktemp -d)
sid="test-$$"
run_hint() { printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"$2\"}" | CLAUDE_CONFIG_DIR="$tmp" env -u SHARAQI_NO_HINTS bash "$hints" "$1"; }

check "no hint before compaction" "" "$(run_hint prompt hello)"
run_hint postcompact "" >/dev/null
check "no hint after 1 compaction" "" "$(run_hint prompt hello)"
run_hint postcompact "" >/dev/null
out=$(run_hint prompt hello)
case "$out" in *'"systemMessage"'*'compacted 2 times'*) r=ok ;; *) r="$out" ;; esac
check "hint after 2 compactions" ok "$r"
check "hint shown once" "" "$(run_hint prompt hello)"
run_hint postcompact "" >/dev/null
check "slash command passes" "" "$(run_hint prompt /compact)"
out=$(printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"hi\"}" | CLAUDE_CONFIG_DIR="$tmp" SHARAQI_NO_HINTS=1 bash "$hints" prompt)
check "SHARAQI_NO_HINTS=1 silences" "" "$out"
case "$(run_hint prompt hello)" in *systemMessage*) r=ok ;; *) r=missing ;; esac
check "hint again after a new compaction" ok "$r"

# Hint output must be valid JSON when python is available.
if command -v python3 >/dev/null 2>&1; then
  run_hint postcompact "" >/dev/null
  run_hint prompt hello | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null
  check "hint is valid JSON" 0 $?
fi

# Old state files are deleted on the next compaction.
touch -t 202001010000 "$tmp/sharaqi-state/old.compacts"
run_hint postcompact "" >/dev/null
check "old state cleaned" no "$([ -e "$tmp/sharaqi-state/old.compacts" ] && echo yes || echo no)"
check "current state kept" yes "$([ -e "$tmp/sharaqi-state/$sid.compacts" ] && echo yes || echo no)"

rm -rf "$tmp"
echo "hooks: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
