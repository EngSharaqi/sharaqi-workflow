#!/usr/bin/env bash
# Tests for hooks/cap-model.sh, hooks/session-hints.sh and hooks/json.sh. Needs bash; the
# parser-specific cases run for each of jq, python3 and "none" that is available.
# usage: bash tests/test_hooks.sh

root="$(cd "$(dirname "$0")/.." && pwd)"
cap="$root/hooks/cap-model.sh"
hints="$root/hooks/session-hints.sh"
fail=0
pass=0
tmp=$(mktemp -d)
export CLAUDE_CONFIG_DIR="$tmp"
unset SHARAQI_ALLOW_ABOVE_CAP SHARAQI_NO_HINTS

check() { # name expected actual
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "FAIL: $1 (expected $2, got $3)"; fi
}

cap_exit() { printf '%s' "$1" | bash "$cap" "${@:2}" >/dev/null 2>&1; echo $?; }
req_exit() { cap_exit "$1" --require-model; }

parsers="none"
command -v jq >/dev/null 2>&1 && parsers="jq $parsers"
command -v python3 >/dev/null 2>&1 && parsers="python3 $parsers"

for P in $parsers; do
  export SHARAQI_JSON_PARSER="$P"
  t="[$P]"
  # --- blocked
  check "$t fable alias"          2 "$(cap_exit '{"tool_input":{"model":"fable","prompt":"x"}}')"
  check "$t fable full id"        2 "$(cap_exit '{"tool_input":{"model":"claude-fable-5-1"}}')"
  check "$t mythos"               2 "$(cap_exit '{"tool_input":{"model":"Mythos"}}')"
  check "$t effort xhigh"         2 "$(cap_exit '{"tool_input":{"model":"opus","effort":"xhigh"}}')"
  check "$t effort max"           2 "$(cap_exit '{"tool_input":{"effort":"max"}}')"
  check "$t sonnet xhigh"          2 "$(cap_exit '{"tool_input":{"model":"sonnet","effort":"xhigh"}}')"
  check "$t sonnet xhigh reversed" 2 "$(cap_exit '{"tool_input":{"effort":"xhigh","model":"claude-sonnet-5-5"}}')"
  check "$t haiku high"           0 "$(cap_exit '{"tool_input":{"model":"haiku","effort":"high"}}')"
  # --- every model x effort boundary (ceiling: opus <= high, sonnet <= high, haiku <= high)
  for mdl in opus sonnet haiku claude-opus-5-5 claude-sonnet-5 claude-haiku-4-5; do
    for eff in low medium high xhigh max; do
      case "$mdl:$eff" in
        *:xhigh | *:max) want=2 ;;
        *) want=0 ;;
      esac
      j="{\"tool_input\":{\"model\":\"$mdl\",\"effort\":\"$eff\"}}"
      check "$t boundary $mdl $eff" "$want" "$(cap_exit "$j")"
    done
  done
  # --- effort from the sharaqi agent file when the call has none
  sa() { # model subagent_type [effort]; JSON built in a variable (a literal "{a,b}" inside "$(...)" brace-expands)
    local extra="" j
    [ -n "${3:-}" ] && extra=",\"effort\":\"$3\""
    j="{\"tool_input\":{\"model\":\"$1\",\"subagent_type\":\"$2\"$extra,\"prompt\":\"x\"}}"
    req_exit "$j"
  }
  check "$t file: haiku + implementer high"   0 "$(sa haiku sharaqi:implementer high)"
  check "$t file: haiku + implementer"        0 "$(sa haiku sharaqi:implementer)"
  check "$t file: haiku + implementer low"    0 "$(sa haiku sharaqi:implementer low)"
  check "$t file: sonnet + implementer high"  0 "$(sa sonnet sharaqi:implementer high)"
  check "$t file: opus + implementer high"    0 "$(sa opus sharaqi:implementer high)"
  check "$t file: opus + reviewer high"       0 "$(sa opus sharaqi:reviewer high)"
  check "$t file: opus + planner"             0 "$(sa opus sharaqi:planner)"
  check "$t file: haiku + planner"            0 "$(sa haiku sharaqi:planner)"
  check "$t file: call effort wins (lower)"   0 "$(sa haiku sharaqi:planner low)"
  check "$t file: call effort wins (higher)"  2 "$(sa sonnet sharaqi:implementer xhigh)"
  check "$t file: unknown sharaqi agent"      0 "$(sa haiku sharaqi:nope)"
  check "$t file: no prefix, not looked up"   0 "$(sa haiku implementer)"
  check "$t file: path in name ignored"       0 "$(sa haiku 'sharaqi:../agents/implementer')"
  check "$t file: still needs a model"        2 "$(req_exit '{"tool_input":{"subagent_type":"sharaqi:implementer","prompt":"x"}}')"
  check "$t pretty-printed"       2 "$(cap_exit $'{"tool_input":{\n  "model": "fable"\n}}')"
  check "$t unknown effort"       2 "$(cap_exit '{"tool_input":{"model":"opus","effort":"ultra"}}')"
  # --- allowed
  check "$t valid opus high"      0 "$(cap_exit '{"tool_input":{"model":"opus","effort":"high"}}')"
  check "$t valid sonnet medium"  0 "$(cap_exit '{"tool_input":{"model":"sonnet","effort":"medium"}}')"
  check "$t haiku no effort"      0 "$(cap_exit '{"tool_input":{"model":"haiku"}}')"
  check "$t keys inside prompt"   0 "$(cap_exit '{"tool_input":{"model":"opus","prompt":"use {\"model\": \"fable\", \"effort\": \"max\"}"}}')"
  check "$t no model, no flag"    0 "$(cap_exit '{"tool_input":{"subagent_type":"general-purpose"}}')"
  # Real payload shape from Claude Code 2.1.274: top-level effort is the parent turn's, not the call's.
  check "$t real payload"         0 "$(req_exit '{"session_id":"s","hook_event_name":"PreToolUse","tool_name":"Agent","effort":"xhigh","tool_input":{"description":"d","prompt":"p","subagent_type":"general-purpose","model":"haiku"}}')"
  # --- --require-model
  check "$t require: no model"        2 "$(req_exit '{"tool_input":{"subagent_type":"implementer","prompt":"x"}}')"
  check "$t require: model in prompt" 2 "$(req_exit '{"tool_input":{"prompt":"use {\"model\": \"haiku\"}"}}')"
  check "$t require: empty model"     2 "$(req_exit '{"tool_input":{"model":""}}')"
  check "$t require: haiku low"       0 "$(req_exit '{"tool_input":{"model":"haiku","effort":"low"}}')"
  check "$t require: still caps"      2 "$(req_exit '{"tool_input":{"model":"fable"}}')"
done
unset SHARAQI_JSON_PARSER

# --- malformed input (with a parser): fail closed only when a run is known to be active
if command -v jq >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
  check "malformed, --require-model: blocked"  2 "$(req_exit '{"tool_input": {"model": "haiku"')"
  check "malformed, no flag: allowed"          0 "$(cap_exit 'not json')"
  check "malformed, --in-run: allowed"         0 "$(cap_exit 'not json' --in-run --require-model)"
  msg=$(printf 'not json' | bash "$cap" 2>&1 >/dev/null)
  case "$msg" in *"not valid JSON"*) r=ok ;; *) r="$msg" ;; esac
  check "malformed: warning on stderr" ok "$r"
fi

check "opt-out" 0 "$(printf '%s' '{"tool_input":{"model":"fable"}}' | SHARAQI_ALLOW_ABOVE_CAP=1 bash "$cap" --require-model >/dev/null 2>&1; echo $?)"

# --- ceiling: the script's fallback defaults equal scripts/prices.json
if command -v jq >/dev/null 2>&1; then
  want=$(jq -r '.ceiling | [(.blocked_models | join("|")), .max_effort.opus, .max_effort.sonnet, .max_effort.haiku, .max_effort.other] | join(" ")' "$root/scripts/prices.json")
  have=$(sed -n 's/^DEFAULT_CEILING="\(.*\)"$/\1/p' "$cap")
  check "fallback ceiling matches prices.json" "$want" "$have"
fi

# --- prices.json: read when valid, defaults when malformed or missing (in a copy of the plugin)
plug="$tmp/plug"; mkdir -p "$plug/scripts"; cp -R "$root/hooks" "$root/agents" "$plug/"
printf -- '---\nname: test-xhigh\neffort: xhigh\n---\n' > "$plug/agents/test-xhigh.md" # no real agent file is over the ceiling
pcap() { printf '%s' "$1" | bash "$plug/hooks/cap-model.sh" --require-model >/dev/null 2>&1; echo $?; }
if command -v jq >/dev/null 2>&1; then
  jq '.ceiling.max_effort.sonnet = "low"' "$root/scripts/prices.json" > "$plug/scripts/prices.json"
  check "prices.json is read: sonnet medium over a low cap" 2 "$(pcap '{"tool_input":{"model":"sonnet","effort":"medium"}}')"
  check "prices.json is read: sonnet low allowed"           0 "$(pcap '{"tool_input":{"model":"sonnet","effort":"low"}}')"
fi
printf '{"ceiling": {nope' > "$plug/scripts/prices.json"
check "malformed prices.json: defaults, fable blocked"     2 "$(pcap '{"tool_input":{"model":"fable"}}')"
check "malformed prices.json: defaults, sonnet high ok"    0 "$(pcap '{"tool_input":{"model":"sonnet","effort":"high"}}')"
check "malformed prices.json: defaults, sonnet xhigh"      2 "$(pcap '{"tool_input":{"model":"sonnet","effort":"xhigh"}}')"
check "malformed prices.json: defaults, haiku high ok"     0 "$(pcap '{"tool_input":{"model":"haiku","effort":"high"}}')"
check "malformed prices.json: file effort still checked"   2 "$(pcap '{"tool_input":{"model":"haiku","subagent_type":"sharaqi:test-xhigh"}}')"
check "malformed prices.json: lower call effort wins"      0 "$(pcap '{"tool_input":{"model":"haiku","subagent_type":"sharaqi:test-xhigh","effort":"high"}}')"
rm "$plug/scripts/prices.json"
check "missing prices.json: defaults, opus xhigh"          2 "$(pcap '{"tool_input":{"model":"opus","effort":"xhigh"}}')"
check "missing prices.json: defaults, opus high ok"        0 "$(pcap '{"tool_input":{"model":"opus","effort":"high"}}')"

# --- agent files (v1.0: one implementer, one reviewer, one planner; effort comes from the call).
# Every executor/reviewer pairing references/routes/delegate.md names is within the ceiling,
# checked through the hook with the call's effort.
check "agents: three files" "implementer.md planner.md reviewer.md" "$(ls "$root/agents" | tr '\n' ' ' | sed 's/ $//')"
pairs=$(grep -oE '(implementer`?|planner`?) (haiku|sonnet|opus) (low|medium|high)' \
  "$root/references/routes/delegate.md" | tr -d '`' | sed 's/^sharaqi://')
check "delegate.md pairings parsed" 5 "$(printf '%s\n' "$pairs" | wc -l | tr -d ' ')"
ceil() { # agent model effort; JSON in a variable: a literal "{a,b}" inside "$(...)" brace-expands
  local j="{\"tool_input\":{\"model\":\"$2\",\"effort\":\"$3\",\"subagent_type\":\"sharaqi:$1\",\"prompt\":\"x\"}}"
  req_exit "$j"
}
while read -r a m e; do
  check "delegate.md: $a $m $e within ceiling" 0 "$(ceil "$a" "$m" "$e")"
done <<<"$pairs"
for e in low medium high; do
  for m in haiku sonnet opus; do
    check "reviewer $m $e within ceiling" 0 "$(ceil reviewer "$m" "$e")"
  done
done
check "planner opus high within ceiling" 0 "$(ceil planner opus high)"

# --- --in-run: inert unless session-hints.sh marked this session as a /sharaqi run
sid="test-$$"
run_hint() { printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"$2\"}" | bash "$hints" "$1"; }
inrun() { cap_exit "{\"session_id\":\"$sid\",\"tool_input\":$1}" --in-run --require-model; }
check "in-run: no marker, fable passes"      0 "$(inrun '{"model":"fable"}')"
check "in-run: no marker, no model passes"   0 "$(inrun '{"prompt":"x"}')"
run_hint prompt "hello" >/dev/null
check "plain prompt writes no marker" no "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
run_hint prompt "/sharaqi do fix the cart" >/dev/null
check "/sharaqi prompt writes marker" yes "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
check "in-run: marker, fable blocked"        2 "$(inrun '{"model":"fable"}')"
check "in-run: marker, no model blocked"     2 "$(inrun '{"prompt":"x"}')"
check "in-run: marker, sonnet medium passes" 0 "$(inrun '{"model":"sonnet","effort":"medium"}')"
check "in-run: other session unaffected"     0 "$(cap_exit '{"session_id":"other","tool_input":{"model":"fable"}}' --in-run)"
run_hint end "" >/dev/null
check "SessionEnd removes marker" no "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
check "in-run: after end, inert again"       0 "$(inrun '{"model":"fable"}')"
run_hint prompt "/sharaqi:sharaqi do x" >/dev/null
check "plugin command name writes marker" yes "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
run_hint end "" >/dev/null
run_hint prompt "/sharaqiX do x" >/dev/null
check "other command writes no marker" no "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
out=$(printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"/sharaqi do x\"}" | SHARAQI_NO_HINTS=1 bash "$hints" prompt)
check "NO_HINTS still writes marker" yes "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
run_hint end "" >/dev/null
check "bad session id ignored" 0 "$(printf '%s' '{"session_id":"../x","prompt":"/sharaqi do"}' | bash "$hints" prompt >/dev/null 2>&1; echo $?; )"
check "bad session id writes nothing" no "$([ -e "$tmp/x.run" ] && echo yes || echo no)"
SHARAQI_JSON_PARSER=none run_hint prompt "/sharaqi do x" >/dev/null
check "no parser: marker still written" yes "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"
run_hint end "" >/dev/null

# --- marker detection: only a prompt that starts with the command, for every parser path
marked() { # prompt-as-JSON-string-body -> yes|no
  rm -f "$tmp/sharaqi-state/$sid.run"
  printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"$1\"}" | bash "$hints" prompt >/dev/null 2>&1
  [ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no
}
for P in $parsers; do
  export SHARAQI_JSON_PARSER="$P"
  t="[$P]"
  check "$t marker: /sharaqi do"            yes "$(marked '/sharaqi do fix x')"
  check "$t marker: plugin form"            yes "$(marked '/sharaqi:sharaqi do fix x')"
  check "$t marker: bare command"           yes "$(marked '/sharaqi')"
  check "$t marker: leading spaces"         yes "$(marked '   /sharaqi do x')"
  check "$t marker: leading newline"        yes "$(marked '\n/sharaqi do x')"
  check "$t marker: leading tab, plugin"    yes "$(marked '\t /sharaqi:sharaqi do x')"
  check "$t no marker: mentions sharaqi"    no "$(marked 'please use sharaqi for this')"
  check "$t no marker: command mid-text"    no "$(marked 'what does /sharaqi do?')"
  check "$t no marker: in backticks"        no "$(marked '`/sharaqi do x`')"
  check "$t no marker: longer name"         no "$(marked '/sharaqi-next do x')"
  check "$t no marker: other plugin"        no "$(marked '/other:sharaqi do x')"
  check "$t no marker: other skill"         no "$(marked '/sharaqi:other do x')"
done
unset SHARAQI_JSON_PARSER

# --- marker lifecycle: follow-ups keep it; a crashed session's marker expires after 24 h
ago() { # hours -> touch -t stamp (BSD date, else GNU date)
  local s=$(( $(date +%s) - $1 * 3600 ))
  date -r "$s" +%Y%m%d%H%M 2>/dev/null || date -d "@$s" +%Y%m%d%H%M
}
run_f="$tmp/sharaqi-state/$sid.run"
run_hint prompt "/sharaqi do x" >/dev/null
touch -t "$(ago 23)" "$run_f"
check "marker 23 h old: still active"        2 "$(inrun '{"model":"fable"}')"
run_hint prompt "and also fix y" >/dev/null
check "follow-up prompt keeps marker"     yes "$([ -e "$run_f" ] && echo yes || echo no)"
check "follow-up prompt refreshes marker" yes "$([ -n "$(find "$run_f" -mmin -5)" ] && echo yes || echo no)"
check "follow-up: ceiling still enforced"    2 "$(inrun '{"model":"fable"}')"
touch -t "$(ago 25)" "$run_f"
check "marker 25 h old: ignored"             0 "$(inrun '{"model":"fable"}')"
touch -t "$(ago 25)" "$tmp/sharaqi-state/crashed.run"
touch "$tmp/sharaqi-state/live.run"
printf '%s' '{"session_id":"someone-else","prompt":"hi"}' | bash "$hints" prompt >/dev/null
check "any event deletes expired markers"   no "$([ -e "$tmp/sharaqi-state/crashed.run" ] && echo yes || echo no)"
check "fresh markers of others kept"        yes "$([ -e "$tmp/sharaqi-state/live.run" ] && echo yes || echo no)"
check "unmarked session gets no marker"      no "$([ -e "$tmp/sharaqi-state/someone-else.run" ] && echo yes || echo no)"
rm -f "$tmp/sharaqi-state/live.run" "$run_f"

# --- text fallback (no parser): block clear violations, otherwise allow with a warning
none_cap() { printf '%s' "$1" | SHARAQI_JSON_PARSER=none bash "$cap" "${@:2}" 2>&1 >/dev/null; echo "rc=$?"; }
check "text: fable is blocked"           "rc=2" "$(none_cap '{"tool_input":{"model":"fable"}}' --require-model | tail -1)"
check "text: xhigh is blocked"           "rc=2" "$(none_cap '{"tool_input":{"model":"opus","effort":"xhigh"}}' --require-model | tail -1)"
check "text: no model key is blocked"    "rc=2" "$(none_cap '{"tool_input":{"prompt":"x"}}' --require-model | tail -1)"
out=$(none_cap '{"tool_input":{"model":null,"prompt":"x"}}' --require-model)
case "$out" in *"not checked"*"rc=0") r=ok ;; *) r="$out" ;; esac
check "text: unreadable model allowed, warned" ok "$r"
out=$(none_cap '{"tool":{"model":"haiku"}}' --require-model)
case "$out" in *"not checked"*"rc=0") r=ok ;; *) r="$out" ;; esac
check "text: no tool_input allowed, warned"    ok "$r"
out=$(none_cap '{"tool_input":{"model":"fable"}}' --in-run --require-model)
case "$out" in *"session_id"*"rc=0") r=ok ;; *) r="$out" ;; esac
check "text: in-run without session id warned" ok "$r"
# A parser that exists but fails (not an invalid-JSON verdict) falls back to text matching.
fake="$tmp/fakebin"; mkdir -p "$fake"
printf '#!/bin/sh\nexit 1\n' > "$fake/python3"; chmod +x "$fake/python3"
broken() { printf '%s' "$1" | PATH="$fake:$PATH" SHARAQI_JSON_PARSER=python3 bash "$cap" --require-model >/dev/null 2>&1; echo $?; }
check "broken parser: fable still blocked" 2 "$(broken '{"tool_input":{"model":"fable"}}')"
check "broken parser: haiku allowed"       0 "$(broken '{"tool_input":{"model":"haiku"}}')"

# --- session-hints.sh: compaction hints
sid="hint-$$"
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
out=$(run_hint prompt ' see src/a.js')
case "$out" in *systemMessage*) r=ok ;; *) r=missing ;; esac
check "text with a slash still hints" ok "$r"
run_hint postcompact "" >/dev/null
out=$(printf '%s' "{\"session_id\":\"$sid\",\"prompt\":\"hi\"}" | SHARAQI_NO_HINTS=1 bash "$hints" prompt)
check "SHARAQI_NO_HINTS=1 silences" "" "$out"
case "$(run_hint prompt hello)" in *systemMessage*) r=ok ;; *) r=missing ;; esac
check "hint again after a new compaction" ok "$r"
check "malformed input: no output, exit 0" "0:" "$(o=$(printf 'nope' | bash "$hints" prompt); echo "$?:$o")"

if command -v python3 >/dev/null 2>&1; then
  run_hint postcompact "" >/dev/null
  run_hint prompt hello | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null
  check "hint is valid JSON" 0 $?
fi

touch -t 202001010000 "$tmp/sharaqi-state/old.compacts" "$tmp/sharaqi-state/old.run"
run_hint postcompact "" >/dev/null
check "old state cleaned" no "$([ -e "$tmp/sharaqi-state/old.compacts" ] && echo yes || echo no)"
check "old run marker cleaned" no "$([ -e "$tmp/sharaqi-state/old.run" ] && echo yes || echo no)"
check "current state kept" yes "$([ -e "$tmp/sharaqi-state/$sid.compacts" ] && echo yes || echo no)"

# --- session-hints.sh: handoff check after a compaction (BASE tree and ROUTE line kept?)
sid="ho-$$"
hf="$tmp/sharaqi-state/$sid.handoff"
B=1e587d25e9c5eba13a30d91bd2c46623a59404d7
R='ROUTE track=coding tier=planned mode=STANDARD'
compact() { # summary-json-fragment: '"compact_summary":"..."' or '' for no field
  printf '%s' "{\"session_id\":\"$sid\",\"trigger\":\"manual\"${1:+,$1}}" | bash "$hints" postcompact
}
flag() { [ -f "$hf" ] && cat "$hf" || echo none; }
compact "\"compact_summary\":\"no route here\"" >/dev/null
check "handoff: not a run, nothing checked" none "$(flag)"
run_hint prompt "/sharaqi do fix the cart" >/dev/null
compact "\"compact_summary\":\"Plan ...\\nBASE: $B\\n$R executor=inline\\nNext: tests\"" >/dev/null
check "handoff: BASE and ROUTE kept" none "$(flag)"
case "$(run_hint prompt continue)" in *additionalContext*) r=said ;; *) r=quiet ;; esac
check "handoff: nothing said when kept" quiet "$r"
compact "\"compact_summary\":\"$R and HEAD $B but no base\"" >/dev/null
check "handoff: BASE missing" BASE "$(flag)"
check "handoff: slash command keeps the flag" "" "$(run_hint prompt /context)"
check "handoff: flag kept after slash command" BASE "$(flag)"
out=$(run_hint prompt continue)
case "$out" in *'"additionalContext":"sharaqi: the last compaction'*'has no BASE'*'never take a new snapshot as BASE'*) r=ok ;; *) r="$out" ;; esac
check "handoff: model told what is missing" ok "$r"
case "$out" in *'"systemMessage":"sharaqi: the compaction summary is missing BASE'*) r=ok ;; *) r="$out" ;; esac
check "handoff: user told too" ok "$r"
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["hookSpecificOutput"]["hookEventName"]=="UserPromptSubmit"' 2>/dev/null
  check "handoff: one valid JSON object" 0 $?
fi
check "handoff: told once" none "$(flag)"
compact "\"compact_summary\":\"BASE $B only\"" >/dev/null
check "handoff: ROUTE missing" ROUTE "$(flag)"
compact "\"compact_summary\":\"Route: planned, base unknown\"" >/dev/null
check "handoff: both missing" "BASE ROUTE" "$(flag)"
compact "" >/dev/null
check "handoff: no summary field is unverified, not passed" unverified "$(flag)"
case "$(run_hint prompt go)" in *'not available to the hook'*) r=ok ;; *) r=missing ;; esac
check "handoff: unverified is said" ok "$r"
compact "\"compact_summary\":\"\"" >/dev/null
check "handoff: empty summary is unverified" unverified "$(flag)"
compact "\"compact_summary\":\"BASE $B $R\"" >/dev/null
check "handoff: a good summary clears it" none "$(flag)"
printf '%s' "{\"session_id\":\"$sid\",\"compact_summary\":\"BASE $B $R\"}" | SHARAQI_JSON_PARSER=none bash "$hints" postcompact >/dev/null
check "handoff: no JSON parser is unverified" unverified "$(flag)"
printf '%s' "{\"session_id\":\"$sid\",\"compact_summary\":\"x\"}" | SHARAQI_NO_HINTS=1 bash "$hints" postcompact >/dev/null
check "handoff: SHARAQI_NO_HINTS doesn't turn the check off" "BASE ROUTE" "$(flag)"
run_hint prompt "/sharaqi do next task" >/dev/null
check "handoff: a new run clears the flag" none "$(flag)"
check "handoff: malformed input, exit 0, no output" "0:" "$(o=$(printf 'nope' | bash "$hints" postcompact); echo "$?:$o")"
compact "\"compact_summary\":\"x\"" >/dev/null
: > "$tmp/sharaqi-state/other.handoff"
run_hint end "" >/dev/null
check "handoff: SessionEnd removes this session's flag" none "$(flag)"
check "handoff: SessionEnd keeps other sessions' files" yes "$([ -e "$tmp/sharaqi-state/other.handoff" ] && echo yes || echo no)"
check "handoff: SessionEnd removes the run marker" no "$([ -e "$tmp/sharaqi-state/$sid.run" ] && echo yes || echo no)"

# --- hooks.json wiring
if command -v jq >/dev/null 2>&1; then
  check "hooks.json: cap gated by run" "bash \"\${CLAUDE_PLUGIN_ROOT}/hooks/cap-model.sh\" --in-run --require-model" \
    "$(jq -r '.hooks.PreToolUse[0].hooks[0].command' "$root/hooks/hooks.json")"
  check "hooks.json: SessionEnd clears marker" "end" \
    "$(jq -r '.hooks.SessionEnd[0].hooks[0].command' "$root/hooks/hooks.json" | awk '{print $NF}')"
fi

# --- context-gate.sh and statusline-bridge.sh
gate="$root/hooks/context-gate.sh"
bridge="$root/hooks/statusline-bridge.sh"
gsid="gate-$$"
ctx_t="$tmp/gate-$gsid.jsonl"
mk_transcript() { # path input_tokens [model]: one main-thread assistant entry
  printf '{"type":"assistant","timestamp":"2026-01-01T10:00:00Z","message":{"model":"%s","usage":{"input_tokens":%s}}}\n' "${3:-claude-opus-5-5}" "$2" > "$1"
}
mk_bridge() { # session window [model]: what the statusline bridge writes
  mkdir -p "$tmp/sharaqi-state"
  printf '{"window":%s,"used_percentage":null,"total_input_tokens":null,"model":"%s","ts":1}\n' "$2" "${3:-claude-opus-5-5}" > "$tmp/sharaqi-state/$1.ctx"
}
gate_payload() { printf '{"session_id":"%s","transcript_path":"%s","tool_name":"Edit"}' "$gsid" "$ctx_t"; }
gate_exit() { printf '%s' "$1" | bash "$gate" "${@:2}" >/dev/null 2>&1; echo $?; }
gate_err() { printf '%s' "$1" | bash "$gate" "${@:2}" 2>&1 >/dev/null; }
has() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }
mk_bridge "$gsid" 200000
mk_transcript "$ctx_t" 1000
check "gate: OK allows"                 0 "$(gate_exit "$(gate_payload)")"
mk_transcript "$ctx_t" 70000
check "gate: WARN allows"               0 "$(gate_exit "$(gate_payload)")"
check "gate: WARN line on stderr"     yes "$(has "$(gate_err "$(gate_payload)")" "CONTEXT 35.0% · 70000/200000 tokens · window verified (statusline, claude-opus-5-5) · WARN")"
mk_transcript "$ctx_t" 80000
check "gate: STOP blocks"              2 "$(gate_exit "$(gate_payload)")"
check "gate: STOP names /compact"    yes "$(has "$(gate_err "$(gate_payload)")" "run /compact, then continue")"
check "gate: subagent call allowed"    0 "$(gate_exit "$(printf '{"session_id":"%s","agent_id":"a1","transcript_path":"%s","tool_name":"Edit"}' "$gsid" "$ctx_t")")"
check "gate: no bridge blocks"         2 "$(rm -f "$tmp/sharaqi-state/$gsid.ctx"; gate_exit "$(gate_payload)")"
check "gate: unverified says why"    yes "$(has "$(gate_err "$(gate_payload)")" "context can't be verified; set up the statusline bridge")"
mk_bridge "$gsid" 200000 claude-sonnet-5
check "gate: model mismatch blocks"    2 "$(gate_exit "$(gate_payload)")"
mk_bridge "$gsid" 200000
check "gate: missing transcript blocks" 2 "$(gate_exit "$(printf '{"session_id":"%s","transcript_path":"%s"}' "$gsid" "$tmp/none.jsonl")")"
check "gate: no session id blocks"     2 "$(gate_exit '{"tool_name":"Edit"}')"
check "gate: broken JSON blocks"       2 "$(gate_exit 'not json')"
check "gate: broken JSON says so"    yes "$(has "$(gate_err 'not json')" "not valid JSON")"
check "gate: no JSON parser blocks"    2 "$(SHARAQI_JSON_PARSER=none gate_exit "$(gate_payload)")"
check "gate: broken JSON, --in-run, no sid: blocks" 2 "$(gate_exit 'not json' --in-run)"
check "gate: broken JSON, --in-run, no marker: allowed" 0 "$(gate_exit '{"session_id":"gate-nomarker"' --in-run)"
# python missing, and any other tokens.py failure: blocked
export SHARAQI_PYTHON="$tmp/no-such-python"
check "gate: python missing blocks"    2 "$(gate_exit "$(gate_payload)")"
check "gate: python missing says so" yes "$(has "$(gate_err "$(gate_payload)")" "python3 not found")"
check "gate: python missing, no run: allowed (--in-run)" 0 "$(gate_exit "$(gate_payload)" --in-run)"
printf '#!/bin/sh\nexit 7\n' > "$tmp/fake-python"; chmod +x "$tmp/fake-python"
export SHARAQI_PYTHON="$tmp/fake-python"
check "gate: tokens.py exit 7 blocks"  2 "$(gate_exit "$(gate_payload)")"
unset SHARAQI_PYTHON
# --in-run: inert without a live marker, active with one
gate_run_f="$tmp/sharaqi-state/$gsid.run"
check "gate --in-run: no marker, STOP passes" 0 "$(gate_exit "$(gate_payload)" --in-run)"
printf '{"session_id":"%s","prompt":"/sharaqi do x"}' "$gsid" | bash "$hints" prompt >/dev/null
check "gate --in-run: marker, STOP blocks"    2 "$(gate_exit "$(gate_payload)" --in-run)"
check "gate --in-run: marker, subagent allowed" 0 "$(gate_exit "$(printf '{"session_id":"%s","agent_id":"a1","transcript_path":"%s"}' "$gsid" "$ctx_t")" --in-run)"
check "gate --in-run: marker, broken JSON blocks" 2 "$(gate_exit "{\"session_id\":\"$gsid\"" --in-run)"
touch -t "$(ago 25)" "$gate_run_f"
check "gate --in-run: marker 25 h old passes" 0 "$(gate_exit "$(gate_payload)" --in-run)"
rm -f "$gate_run_f"
mk_transcript "$ctx_t" 70000
check "gate: no flag is always active" 0 "$(gate_exit "$(gate_payload)")"
mk_transcript "$ctx_t" 80000
check "gate: no flag, STOP blocks"     2 "$(gate_exit "$(gate_payload)")"
# every entry and track arms the gate: review (both invocation forms), non-coding, tiny
for p in "/sharaqi review" "/sharaqi review src/a.ts" "/sharaqi:sharaqi review HEAD~1..HEAD" \
  "/sharaqi do draft an email to the client" "/sharaqi do change the button colour"; do
  printf '{"session_id":"%s","prompt":"%s"}' "$gsid" "$p" | bash "$hints" prompt >/dev/null
  check "gate --in-run [$p]: marker written" yes "$([ -f "$gate_run_f" ] && echo yes || echo no)"
  for tool in Agent Edit Write; do
    check "gate --in-run [$p]: STOP blocks $tool" 2 \
      "$(gate_exit "$(printf '{"session_id":"%s","transcript_path":"%s","tool_name":"%s"}' "$gsid" "$ctx_t" "$tool")" --in-run)"
  done
  rm -f "$gate_run_f"
done

# --- context gate, benchmark mode: a headless run declares the window; thresholds unchanged
rm -f "$tmp/sharaqi-state/$gsid.ctx"
ev_f="$tmp/sharaqi-state/$gsid.events.jsonl"; rm -f "$ev_f"
mk_transcript "$ctx_t" 1000
check "bench: no window declared, no bench: blocks"   2 "$(gate_exit "$(gate_payload)")"
check "bench: window without bench mode: blocks"      2 "$(SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)")"
check "bench: window without bench mode says so"    yes "$(has "$(SHARAQI_CONTEXT_WINDOW=200000 gate_err "$(gate_payload)")" "applies only with SHARAQI_BENCHMARK=1")"
check "bench: bench mode without window: blocks"      2 "$(SHARAQI_BENCHMARK=1 gate_exit "$(gate_payload)")"
check "bench: bench mode without window says so"    yes "$(has "$(SHARAQI_BENCHMARK=1 gate_err "$(gate_payload)")" "benchmark mode needs SHARAQI_CONTEXT_WINDOW")"
check "bench: garbage window blocks"                  2 "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=lots gate_exit "$(gate_payload)")"
check "bench: declared window, OK allows"             0 "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)")"
mk_transcript "$ctx_t" 80000
check "bench: declared window, STOP still blocks"     2 "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)")"
check "bench: line says declared, not verified"     yes "$(has "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_err "$(gate_payload)")" "window declared (benchmark mode")"
mk_bridge "$gsid" 1000000
check "bench: a real bridge wins over the declared window" 0 "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)")"
rm -f "$tmp/sharaqi-state/$gsid.ctx"
# events: every decision is logged with a class, outside the model's context
rm -f "$ev_f"
mk_transcript "$ctx_t" 1000
gate_exit "$(gate_payload)" >/dev/null
SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)" >/dev/null
mk_transcript "$ctx_t" 80000
SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)" >/dev/null
printf '{"type":"user","timestamp":"2026-01-01T10:00:00Z"}\n' > "$ctx_t"
SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)" >/dev/null
check "events: one line per decision" 4 "$(wc -l < "$ev_f" | tr -d ' ')"
check "events: classes in order" "block:unverified-window allow:ok block:stop block:unverified-transcript" \
  "$(python3 -I -c 'import json,sys; print(" ".join(d["decision"]+":"+d["class"] for d in map(json.loads, open(sys.argv[1]))))' "$ev_f")"
check "events: tool recorded" Edit "$(head -1 "$ev_f" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["tool"])')"
# no usage entry yet: re-read before giving up (the transcript is still being written)
printf '{"type":"user","timestamp":"2026-01-01T10:00:00Z"}\n' > "$ctx_t"
( sleep 0.5; mk_transcript "$ctx_t" 1000 ) &
check "gate: usage that appears late is waited for" 0 "$(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000 gate_exit "$(gate_payload)")"
wait

# --- agent-audit.sh: Opus only with an escalation reason; every call logged
audit="$root/hooks/agent-audit.sh"
asid="audit-$$"
a_ev="$tmp/sharaqi-state/$asid.events.jsonl"
apay() { # model [description] [effort] [run_in_background: false|true|omit]
  local bg=',"run_in_background":false'
  case "${4:-false}" in true) bg=',"run_in_background":true' ;; omit) bg="" ;; esac
  printf '{"session_id":"%s","tool_name":"Agent","tool_input":{"model":"%s","effort":"%s","subagent_type":"sharaqi:reviewer","description":"%s","prompt":"SECRET-PROMPT-TEXT"%s}}' \
    "$asid" "$1" "${3:-medium}" "${2:-review diff}" "$bg"
}
audit_exit() { printf '%s' "$1" | bash "$audit" "${@:2}" >/dev/null 2>&1; echo $?; }
check "audit: not a run, opus without reason: allowed (--in-run)" 0 "$(audit_exit "$(apay opus)" --in-run)"
check "audit: not a run: nothing logged" no "$([ -f "$a_ev" ] && echo yes || echo no)"
printf '{"session_id":"%s","prompt":"/sharaqi do x"}' "$asid" | bash "$hints" prompt >/dev/null
check "audit: opus without escalate blocked"       2 "$(audit_exit "$(apay opus)" --in-run)"
check "audit: full opus id without escalate"       2 "$(audit_exit "$(apay claude-opus-5-5)" --in-run)"
check "audit: unknown escalate reason blocked"     2 "$(audit_exit "$(apay opus 'escalate:long-task review')" --in-run)"
check "audit: escalate mid-description blocked"    2 "$(audit_exit "$(apay opus 'review escalate:critical')" --in-run)"
for r in critical failed-twice reasoning; do
  check "audit: opus escalate:$r allowed" 0 "$(audit_exit "$(apay opus "escalate:$r review" high)" --in-run)"
done
check "audit: sonnet needs no reason" 0 "$(audit_exit "$(apay sonnet)" --in-run)"
check "audit: haiku needs no reason"  0 "$(audit_exit "$(apay haiku)" --in-run)"
for P in $parsers; do
  [ "$P" = none ] && continue
  check "audit [$P]: background omitted blocked" 2 "$(SHARAQI_JSON_PARSER=$P audit_exit "$(apay sonnet 'review' low omit)" --in-run)"
  check "audit [$P]: background true blocked"    2 "$(SHARAQI_JSON_PARSER=$P audit_exit "$(apay haiku 'review' low true)" --in-run)"
  check "audit [$P]: foreground allowed"         0 "$(SHARAQI_JSON_PARSER=$P audit_exit "$(apay haiku 'review' low)" --in-run)"
done
check "audit: background message names the fix" yes "$(has "$(printf '%s' "$(apay sonnet x low omit)" | bash "$audit" --in-run 2>&1 >/dev/null)" "run_in_background: false")"
check "audit: block message names the fix" yes "$(has "$(printf '%s' "$(apay opus)" | bash "$audit" --in-run 2>&1 >/dev/null)" "escalate:critical")"
nparsers=$(printf '%s\n' $parsers | grep -vc '^none$')
check "audit: one log line per call" $((11 + 3 * nparsers)) "$(wc -l < "$a_ev" | tr -d ' ')"
want="block block block block allow allow allow allow allow"
for _ in $(seq "$nparsers"); do want="$want block block allow"; done
check "audit: log is JSON with decisions" "$want block block" \
  "$(python3 -I -c 'import json,sys; print(" ".join(json.loads(l)["decision"] for l in open(sys.argv[1])))' "$a_ev")"
check "audit: prompt never logged" 0 "$(grep -c 'SECRET-PROMPT-TEXT' "$a_ev")"
check "audit: escalation recorded" yes "$(grep -q '"model":"opus","effort":"high","escalate":"failed-twice","background":"false","from_subagent":"","decision":"allow"' "$a_ev" && echo yes || echo no)"
check "audit: block reasons recorded" "escalation background" \
  "$(python3 -I -c 'import json,sys; r=[json.loads(l).get("reason") for l in open(sys.argv[1])]; print(r[0], r[9])' "$a_ev")"
check "audit: unreadable input in a run: allowed, logged unchecked" 0 \
  "$(printf '{"session_id":"%s","tool_input":{' "$asid" | bash "$audit" --in-run >/dev/null 2>&1; echo $?)"
check "audit: unchecked logged" yes "$(tail -1 "$a_ev" | grep -q '"decision":"unchecked"' && echo yes || echo no)"
rm -f "$tmp/sharaqi-state/$asid.run"

# --- route-prompt.sh: routes /sharaqi prompts, never blocks, says so when it can't
rp="$root/hooks/route-prompt.sh"
rsid="route-$$"
rp_out() { printf '%s' "$1" | bash "$rp" 2>/dev/null; }
rp_ctx() { rp_out "$1" | python3 -I -c 'import json,sys
t=sys.stdin.read().strip()
print(json.loads(t)["hookSpecificOutput"]["additionalContext"] if t else "")'; }
check "route hook: other prompt passes, no output" "" "$(rp_out "{\"session_id\":\"$rsid\",\"prompt\":\"hello\"}")"
check "route hook: exit 0 on garbage" 0 "$(printf 'nope' | bash "$rp" >/dev/null 2>&1; echo $?)"
c=$(rp_ctx "{\"session_id\":\"$rsid\",\"prompt\":\"/sharaqi route Change the colour in a.css (one rule)\",\"cwd\":\"$tmp\"}")
check "route hook: ROUTE injected"   yes "$(has "$c" "ROUTE track=coding tier=tiny")"
check "route hook: FACTS injected"   yes "$(has "$c" "FACTS critical=none")"
check "route hook: route-only steps" yes "$(has "$c" "Run no tools")"
check "route hook: route entry takes no BASE" no "$(has "$c" "BASE ")"
check "route hook: route event logged" yes "$(grep -q '"event": "route"' "$tmp/sharaqi-state/$rsid.events.jsonl" && echo yes || echo no)"
c=$(rp_ctx "{\"session_id\":\"$rsid\",\"prompt\":\"/sharaqi:sharaqi review HEAD\"}")
check "route hook: plugin-prefixed form" yes "$(has "$c" "ROUTE track=review")"
check "route hook: no python: unavailable, said so" yes \
  "$(has "$(printf '{"session_id":"%s","prompt":"/sharaqi do x"}' "$rsid" | SHARAQI_PYTHON="$tmp/no-such-python" bash "$rp")" "ROUTE UNAVAILABLE")"
check "route hook: no python, other prompt: silent" "" \
  "$(printf '{"session_id":"%s","prompt":"hi"}' "$rsid" | SHARAQI_PYTHON="$tmp/no-such-python" bash "$rp")"
check "route hook: no python, exit 0" 0 \
  "$(printf '{"session_id":"%s","prompt":"/sharaqi do x"}' "$rsid" | SHARAQI_PYTHON="$tmp/no-such-python" bash "$rp" >/dev/null; echo $?)"
check "route hook: off switch" "" "$(printf '{"session_id":"%s","prompt":"/sharaqi do x"}' "$rsid" | SHARAQI_NO_ROUTE_HOOK=1 bash "$rp")"

# statusline-bridge.sh
bsid="bridge-$$"
bjson="{\"session_id\":\"$bsid\",\"model\":{\"id\":\"claude-opus-5-5\"},\"context_window\":{\"context_window_size\":200000,\"used_percentage\":12.5,\"total_input_tokens\":25000}}"
check "bridge: prints ctx pct" "ctx 12.5%" "$(printf '%s' "$bjson" | bash "$bridge")"
check "bridge: state file written" yes "$([ -f "$tmp/sharaqi-state/$bsid.ctx" ] && echo yes || echo no)"
check "bridge: state fields" yes "$(grep -q '"window":200000,"used_percentage":12.5,"total_input_tokens":25000,"model":"claude-opus-5-5"' "$tmp/sharaqi-state/$bsid.ctx" && echo yes || echo no)"
check "bridge: no temp file left" 0 "$(ls -A "$tmp/sharaqi-state" | grep -c '^\.')"
check "bridge: wrapped command gets stdin" "$bjson" "$(printf '%s' "$bjson" | bash "$bridge" cat)"
check "bridge: wrapped run still writes" yes "$(grep -q '"window":200000' "$tmp/sharaqi-state/$bsid.ctx" && echo yes || echo no)"
check "bridge: failing wrapped command, exit 0" 0 "$(printf '%s' "$bjson" | bash "$bridge" false >/dev/null 2>&1; echo $?)"
check "bridge: bad session id writes nothing" no "$([ -e "$tmp/bad.ctx" ] && echo yes || echo no)"
printf '%s' "${bjson/$bsid/..\/bad}" | bash "$bridge" >/dev/null
check "bridge: session id with / refused" no "$([ -e "$tmp/bad.ctx" ] && echo yes || echo no)"
check "bridge: garbage input: exit 0, ctx ?" "0:ctx ?" "$(o=$(printf 'nope' | bash "$bridge"); echo "$?:$o")"

# hooks.json: the gate is entry [1], after cap-model; the escalation audit is entry [2]
if command -v jq >/dev/null 2>&1; then
  check "hooks.json: three PreToolUse entries" 3 "$(jq '.hooks.PreToolUse | length' "$root/hooks/hooks.json")"
  check "hooks.json: audit matcher" "Agent|Task" "$(jq -r '.hooks.PreToolUse[2].matcher' "$root/hooks/hooks.json")"
  check "hooks.json: audit command" "bash \"\${CLAUDE_PLUGIN_ROOT}/hooks/agent-audit.sh\" --in-run" \
    "$(jq -r '.hooks.PreToolUse[2].hooks[0].command' "$root/hooks/hooks.json")"
  check "hooks.json: route hook on UserPromptSubmit" "bash \"\${CLAUDE_PLUGIN_ROOT}/hooks/route-prompt.sh\"" \
    "$(jq -r '.hooks.UserPromptSubmit[0].hooks[1].command' "$root/hooks/hooks.json")"
  check "hooks.json: gate matcher" "Agent|Task|Edit|Write|NotebookEdit" \
    "$(jq -r '.hooks.PreToolUse[1].matcher' "$root/hooks/hooks.json")"
  check "hooks.json: gate command" "bash \"\${CLAUDE_PLUGIN_ROOT}/hooks/context-gate.sh\" --in-run" \
    "$(jq -r '.hooks.PreToolUse[1].hooks[0].command' "$root/hooks/hooks.json")"
fi

rm -rf "$tmp"
echo "hooks: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
