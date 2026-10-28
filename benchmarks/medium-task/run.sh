#!/bin/bash
# One benchmark run. usage: run.sh <plain|skill> <n>
#   RUNS=<dir>    where runs go; must be outside this repo (the hidden tests must stay unseen)
#   PLUGIN=<dir>  the plugin under test, loaded with --plugin-dir in BOTH arms
# Writes <RUNS>/<arm>-<n>/ (the working tree) and <RUNS>/<arm>-<n>.{json,err,markers,hidden,probe,npm,tokens}.
set -u
B=$(cd "$(dirname "$0")" && pwd)
: "${RUNS:?set RUNS}" "${PLUGIN:?set PLUGIN}"
arm=$1; n=$2; name="$arm-$n"; A="$RUNS/$name"
case "$arm" in
  plain) prefix="" ;;
  skill) prefix="/sharaqi:sharaqi do " ;;
  *) echo "arm must be plain or skill" >&2; exit 1 ;;
esac
rm -rf "$A"; mkdir -p "$RUNS"; cp -R "$B/fixture" "$A"; cd "$A" || exit 1
git init -q && git add -A && git -c user.email=bench@example.invalid -c user.name=bench commit -qm fixture
LOG="$RUNS/$name.markers"; : > "$LOG"
SETTINGS=$(jq -n --arg cmd "bash \"$B/marker-log.sh\" \"$LOG\"" \
  '{enabledPlugins: {"sharaqi@skills-dir": false},
    hooks: {PreToolUse: [{matcher: "*", hooks: [{type: "command", command: $cmd}]}]}}')
START_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ); START=$(date +%s)
claude -p "$prefix$(cat "$B/task.txt")" --model opus --effort medium \
  --output-format json --max-budget-usd 8 --permission-mode acceptEdits \
  --settings "$SETTINGS" --plugin-dir "$PLUGIN" \
  --allowedTools Read Edit Write Glob Grep Agent Task SendMessage \
  "Bash(npm:*)" "Bash(node:*)" "Bash(git:*)" "Bash(date:*)" "Bash(python3:*)" "Bash(python:*)" \
  "Bash(ls:*)" "Bash(cat:*)" "Bash(grep:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(wc:*)" \
  "Bash(find:*)" "Bash(sed:*)" "Bash(mkdir:*)" \
  > "$RUNS/$name.json" 2> "$RUNS/$name.err"
echo "wall_s=$(( $(date +%s) - START ))" >> "$RUNS/$name.err"
# Ground truth, after the run: the arm's own tests, hidden tests, edge probe, and the tree.
npm test > "$RUNS/$name.npm" 2>&1; echo "npm_exit=$?" >> "$RUNS/$name.npm"
mkdir -p hidden-run && cp "$B/hidden/hidden.test.js" hidden-run/
node --test hidden-run/hidden.test.js > "$RUNS/$name.hidden" 2>&1
rm -rf hidden-run
node "$B/probe.mjs" "$A" > "$RUNS/$name.probe" 2>&1
git status --porcelain > "$RUNS/$name.status"
sid=$(jq -r '.session_id // empty' "$RUNS/$name.json")
python3 -I "$PLUGIN/scripts/tokens.py" --session "$sid" --since "$START_ISO" > "$RUNS/$name.tokens" 2>&1
jq -c '{cost: .total_cost_usd, turns: .num_turns, ms: .duration_ms, denials: (.permission_denials | length), error: .is_error}' "$RUNS/$name.json"
grep -E '^ℹ (pass|fail)' "$RUNS/$name.hidden" | tr '\n' ' '; tail -1 "$RUNS/$name.probe"
