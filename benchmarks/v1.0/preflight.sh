#!/bin/bash
# Zero-cost launch check of all 33 arm x case combinations: each run goes to capture.py on
# localhost (HTTP 400), never to Anthropic. Checks, per run, what the API would have received:
# the seat model, the sharaqi skill text, the prompt hook's ROUTE, which sharaqi agents are
# listed, and that plain Claude has no sharaqi at all.
#   usage: RUNS=<dir from prepare.sh> bash preflight.sh
set -u
B=$(cd "$(dirname "$0")" && pwd)
: "${RUNS:?set RUNS (prepare.sh)}"
port=${PORT:-48199}
mkdir -p "$RUNS/preflight"
fail=0
for id in 1 2 3 4 5 6 7a 7b 8 9 10; do
  for arm in plain v0.9 v1.0; do
    cap="$RUNS/preflight/$arm-$id"; mkdir -p "$cap"
    python3 -I "$B/capture.py" "$cap" "$port" & pid=$!
    sleep 0.5
    PREFLIGHT=$port bash "$B/run.sh" "$arm" "$id" 1 >/dev/null 2>&1
    kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
    python3 -I "$B/score.py" --preflight "$cap" "$arm" "$id" || fail=$((fail + 1))
  done
done
echo "preflight: $fail failed"
[ "$fail" -eq 0 ]
