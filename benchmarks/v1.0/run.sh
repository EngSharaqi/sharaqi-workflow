#!/bin/bash
# ONE PAID RUN: one `claude -p` call, budget $1. usage: RUNS=<dir> bash run.sh <plain|v0.9|v1.0> <case> <rep>
#   RUNS comes from prepare.sh. PREFLIGHT=<port> sends the call to a local capture server
#   (preflight.sh) instead of Anthropic: no cost, no record. BENCH_TIMEOUT_S (default 300)
#   is the per-process limit; only the tests lower it.
# Identical for every arm: model opus, effort medium, $1 budget, permission mode default, the
# allow-list below, a new scratch repo, stdin from /dev/null, the PreToolUse marker log,
# sharaqi@skills-dir disabled, SHARAQI_BENCHMARK=1 with a declared 200k window (only v1.0
# reads it; 200k is stricter than the 1M Claude Code reports for these models).
# Only the prompt prefix and --plugin-dir differ (MANIFEST.md).
set -u
B=$(cd "$(dirname "$0")" && pwd)
: "${RUNS:?set RUNS (prepare.sh)}"
arm=$1; id=$2; rep=${3:-1}
[ -f "$B/cases/$id" ] || { echo "unknown case $id" >&2; exit 1; }
task=$(cat "$B/cases/$id")
case "$id" in 7a | 7b) entry=review ;; *) entry=route ;; esac
plugin=()
case "$arm" in
  plain) prompt="$task" ;;
  v0.9 | v1.0) prompt="/sharaqi:sharaqi $entry $task"; plugin=(--plugin-dir "$RUNS/plugins/$arm") ;;
  *) echo "arm: plain, v0.9 or v1.0" >&2; exit 1 ;;
esac
name="$arm-$id-$rep"; [ -n "${PREFLIGHT:-}" ] && name="preflight-$name"
A="$RUNS/work/$name"; REC="$RUNS/records/$name.json"
[ -e "$A" ] && { echo "$A exists" >&2; exit 1; }
[ -e "$REC" ] && { echo "$REC exists" >&2; exit 1; }
mkdir -p "$A" && cd "$A" || exit 1
printf '# scratch repo\n' > README.md
git init -q && git add -A && git -c user.email=bench@example.invalid -c user.name=bench commit -qm scratch
LOG="$RUNS/out/$name.markers"; : > "$LOG"
SETTINGS=$(jq -n --arg cmd "bash \"$B/../v0.8/marker-log.sh\" \"$LOG\"" \
  '{enabledPlugins: {"sharaqi@skills-dir": false},
    hooks: {PreToolUse: [{matcher: "*", hooks: [{type: "command", command: $cmd}]}]}}')
envs=(SHARAQI_BENCHMARK=1 SHARAQI_CONTEXT_WINDOW=200000)
[ -n "${PREFLIGHT:-}" ] && envs+=(ANTHROPIC_BASE_URL="http://127.0.0.1:$PREFLIGHT")
started=$(date -u +%Y-%m-%dT%H:%M:%SZ); t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
env "${envs[@]}" perl -e 'alarm shift; exec @ARGV' "${BENCH_TIMEOUT_S:-300}" claude -p "$prompt" --model opus --effort medium \
  --output-format stream-json --verbose --max-budget-usd 1 --permission-mode default \
  --settings "$SETTINGS" ${plugin[@]+"${plugin[@]}"} \
  --allowedTools Read Glob Grep Agent "Bash(git:*)" "Bash(ls:*)" "Bash(wc:*)" "Bash(grep:*)" "Bash(python3:*)" \
  < /dev/null > "$RUNS/out/$name.jsonl" 2> "$RUNS/out/$name.err"
rc=$?
t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time'); finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
wall=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b - a}')
echo "rc=$rc wall_s=$wall" >> "$RUNS/out/$name.err"
[ -n "${PREFLIGHT:-}" ] && exit 0
# One accounting rule for every arm: v1.0's runrecord.py, frozen in RUNS. The record is built in
# a temp file, validated, then renamed into place; a run with no usable result event (timeout,
# crash, empty or malformed output, a record that won't build) gets a `no-result` record with
# a null cost instead. Either way the run exits 1 unless it completed.
RR="$RUNS/plugins/v1.0/scripts/runrecord.py"; TMP="$RUNS/records/.$name.json.tmp"
ver=$(cat "$RUNS/plugins/$arm.id" 2>/dev/null || cat "$RUNS/claude-version.txt")
common=(--result "$RUNS/out/$name.jsonl" --run-id "$name" --arm "$arm" --version "$ver"
  --case "$id" --started "$started" --finished "$finished" --wall-s "$wall" --exit-code "$rc")
if ! { [ "$rc" -ne 142 ] && python3 -I "$RR" record "${common[@]}" > "$TMP" 2>> "$RUNS/out/$name.err" \
       && python3 -I "$RR" validate "$TMP" 2>> "$RUNS/out/$name.err"; }; then
  echo "record: no usable result for $name (rc=$rc); writing a no-result record" >> "$RUNS/out/$name.err"
  python3 -I "$RR" failure "${common[@]}" --error-log "$RUNS/out/$name.err" > "$TMP" \
    && python3 -I "$RR" validate "$TMP" \
    || { rm -f "$TMP"; echo "no record could be written for $name" >&2; exit 1; }
fi
[ -e "$REC" ] && { rm -f "$TMP"; echo "$REC appeared during the run; not overwritten" >&2; exit 1; }
mv "$TMP" "$REC" || exit 1
line=$(jq -c '{run_id, status, cost: .cost.actual_usd, wall_s, turns: .num_turns}' "$REC") || exit 1
echo "$line"
[ "$rc" -eq 0 ] && [ "$(jq -r .status "$REC")" = completed ]
