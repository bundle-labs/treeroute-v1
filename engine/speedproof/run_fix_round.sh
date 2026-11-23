#!/usr/bin/env bash
# Speedproof fix round (2026-09-28): the re-runs the review asked for, STRICTLY ONE AT A TIME.
# Each run writes a NEW folder under D:/treeroute/speedproof/ plus <name>.console.txt beside it.
# Resumable: a run whose folder already has a finished verdict.json is skipped. Stops at the first
# failure (fail loud); the scripts' own pre-flights refuse to start while temp files remain.
#   bash run_fix_round.sh            (from engine/speedproof/)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="D:/treeroute/speedproof"
STATUS="$OUT/fix_round_status.txt"
WIDE="--smoke --npd 400 --links identity,log,logc"
U2="--smoke --links identity,log,logc --levels 10 --ratios 0.0625 --expect-from D:/pm25_adapt/smoke/inner_candidates.csv"

run() {   # run <name> <script> <flags...>
  local name="$1"; shift
  local script="$1"; shift
  if [ -f "$OUT/$name/verdict.json" ] && grep -q '"status": "done"' "$OUT/$name/verdict.json"; then
    echo "SKIP $name (already finished) $(date +%H:%M:%S)" | tee -a "$STATUS"
    return 0
  fi
  if [ -e "$OUT/$name" ] || [ -e "$OUT/$name.console.txt" ]; then
    echo "STOPPED $name: folder or console file exists but the run is not finished; look first" | tee -a "$STATUS"
    exit 2
  fi
  echo "START $name $(date +%H:%M:%S): $script $* --run-dir $OUT/$name" | tee -a "$STATUS"
  (cd "$HERE" && py -3.9 -u "$script" "$@" --run-dir "$OUT/$name") > "$OUT/$name.console.txt" 2>&1
  local rc=$?
  local left
  left="$(ls "$OUT/tmp" 2>/dev/null | wc -l) in tmp, $(ls D:/pm25 2>/dev/null | wc -l) in D:/pm25"
  echo "DONE $name rc=$rc $(date +%H:%M:%S) | temp files left: $left" | tee -a "$STATUS"
  if [ "$rc" != "0" ]; then
    echo "STOPPED after $name (rc=$rc); see $OUT/$name.console.txt" | tee -a "$STATUS"
    exit "$rc"
  fi
}

echo "ROUND START $(date '+%Y-%m-%d %H:%M:%S') | copy sha256 $(sha256sum "$HERE/pm25_adaptation_fast.py" | cut -c1-64)" | tee -a "$STATUS"
# shellcheck disable=SC2086
run wide_final_fo_w8      pm25_adaptation_fast.py $WIDE --workers 8 --finite-once 1
run wide_final_w8         pm25_adaptation_fast.py $WIDE --workers 8
run wide_final_fo_w1      pm25_adaptation_fast.py $WIDE --workers 1 --finite-once 1
run wide_final_trees8_fo0 pm25_adaptation_fast.py $WIDE --tree-workers 8 --router-workers 1 --router-pin 0 --finite-once 0
run wide_golden_blas1     run_shipped_blas1.py    $WIDE
run final2_u2_w8          pm25_adaptation_fast.py $U2 --workers 8
echo "ALL FINISHED $(date +%H:%M:%S)" | tee -a "$STATUS"
