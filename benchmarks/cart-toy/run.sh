#!/bin/bash
# usage: run.sh <arm> <prompt-prefix>   e.g. run.sh arm-skill "/sharaqi:sharaqi do "  |  run.sh arm-plain ""
# Arm dirs and logs are written next to this script; PLUGIN= points at the plugin under test (default: this repo).
B=$(cd "$(dirname "$0")" && pwd)
A="$B/$1"; rm -rf "$A"; cp -R "$B/fixture" "$A"; cd "$A"
git init -q && git add -A && git -c user.email=b@x -c user.name=bench commit -qm fixture
LOG="$B/$1.state.log"; : > "$LOG"
SETTINGS=$(cat <<J
{"enabledPlugins":{"sharaqi@skills-dir":false},
 "hooks":{"PreToolUse":[{"matcher":"Bash|Agent","hooks":[{"type":"command","command":"ls \$HOME/.claude/sharaqi-state/ 2>/dev/null | grep -c '\\\\.run\$' >> $LOG; jq -r '.session_id' >> $LOG"}]}]}}
J
)
START=$(date +%s)
claude -p "$2$(cat "$B/task.txt")" --model opus --effort medium \
  --output-format json --max-budget-usd 5 --permission-mode acceptEdits \
  --settings "$SETTINGS" --plugin-dir "${PLUGIN:-$B/../..}" \
  --allowedTools Read Edit Write Glob Grep Agent Task "Bash(npm:*)" "Bash(node:*)" "Bash(git:*)" \
  "Bash(date:*)" "Bash(python3:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(grep:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(wc:*)" \
  > "$B/$1.json" 2> "$B/$1.err"
echo "wall_s=$(( $(date +%s) - START ))" >> "$B/$1.err"
mkdir -p hidden-run && cp "$B/hidden/hidden.test.js" hidden-run/
node --test hidden-run/hidden.test.js > "$B/$1.hidden.txt" 2>&1; grep -E '^ℹ (tests|pass|fail)' "$B/$1.hidden.txt"
node "$B/probe.mjs" "$A" > "$B/$1.probe.txt" 2>&1; cat "$B/$1.probe.txt"
git status --porcelain; git diff --stat | tail -1
