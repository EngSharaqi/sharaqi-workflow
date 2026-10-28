#!/bin/bash
# THE PAID BENCHMARK: 3 arms x 11 cases x REPS runs, interleaved. Needs a separate yes.
#   usage: RUNS=<dir from prepare.sh> [REPS=1] [CAP_USD=<stop before passing it>] bash runall.sh
# Order: case by case; within a case the arm order rotates (plain,v0.9,v1.0 / v0.9,v1.0,plain /
# v1.0,plain,v0.9 ...), so no arm always runs first on a cold cache. Stops at the first run
# that fails, has no result event, or costs over $1, and before a run that could pass
# CAP_USD; never retries, never skips a case.
set -u
B=$(cd "$(dirname "$0")" && pwd)
: "${RUNS:?set RUNS (prepare.sh)}"
REPS=${REPS:-1}; CAP_USD=${CAP_USD:-$(awk -v r="$REPS" 'BEGIN{print 12 * r}')}
arms=(plain v0.9 v1.0); total=0; k=0
for rep in $(seq "$REPS"); do
  for id in 1 2 3 4 5 6 7a 7b 8 9 10; do
    for j in 0 1 2; do
      arm=${arms[$(( (k + j) % 3 ))]}
      if awk -v t="$total" -v c="$CAP_USD" 'BEGIN{exit !(t + 1 > c)}'; then
        echo "STOP before $arm $id #$rep: total \$$total, cap \$$CAP_USD"; exit 1
      fi
      line=$(bash "$B/run.sh" "$arm" "$id" "$rep") || { echo "STOP: $arm $id #$rep failed: $line"; exit 1; }
      echo "$line"
      c=$(printf '%s' "$line" | jq -r '.cost // empty')
      [ -n "$c" ] || { echo "STOP: $arm $id #$rep has no cost"; exit 1; }
      [ "$(printf '%s' "$line" | jq -r .status)" = completed ] || { echo "STOP: $arm $id #$rep not completed"; exit 1; }
      total=$(awk -v t="$total" -v c="$c" 'BEGIN{printf "%.6f", t + c}')
      awk -v c="$c" 'BEGIN{exit !(c > 1)}' && { echo "STOP: $arm $id #$rep over \$1"; exit 1; }
    done
    k=$((k + 1))
  done
done
echo "DONE total=\$$total"
python3 -I "$B/score.py" "$RUNS"
