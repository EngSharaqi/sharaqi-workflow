#!/bin/bash
# One v0.9 routing-case run (paid: one `claude -p` call, budget $1). usage: route.sh <case id> <task text file>
#   RUNS=<dir>, PLUGIN=<dir> as in ../v0.8/run.sh; ENTRY=route (default) or review. Runs
#   `/sharaqi:sharaqi $ENTRY <task>` in a fresh scratch repo and writes <RUNS>/route-<id>.{json,err,markers}.
set -u
B=$(cd "$(dirname "$0")" && pwd)
: "${RUNS:?set RUNS}" "${PLUGIN:?set PLUGIN}"
id=$1; A="$RUNS/route-$id"
[ -e "$A" ] && { echo "$A exists" >&2; exit 1; }
mkdir -p "$A"; cd "$A" || exit 1
printf '# scratch repo\n' > README.md
git init -q && git add -A && git -c user.email=bench@example.invalid -c user.name=bench commit -qm scratch
LOG="$RUNS/route-$id.markers"; : > "$LOG"
SETTINGS=$(jq -n --arg cmd "bash \"$B/../v0.8/marker-log.sh\" \"$LOG\"" \
  '{enabledPlugins: {"sharaqi@skills-dir": false},
    hooks: {PreToolUse: [{matcher: "*", hooks: [{type: "command", command: $cmd}]}]}}')
claude -p "/sharaqi:sharaqi ${ENTRY:-route} $(cat "$2")" --model opus --effort medium \
  --output-format json --max-budget-usd 1 --permission-mode default \
  --settings "$SETTINGS" --plugin-dir "$PLUGIN" \
  --allowedTools Read Glob Grep "Bash(git:*)" "Bash(ls:*)" "Bash(wc:*)" "Bash(grep:*)" "Bash(python3:*)" \
  > "$RUNS/route-$id.json" 2> "$RUNS/route-$id.err"
jq -r '.result' "$RUNS/route-$id.json"
