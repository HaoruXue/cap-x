#!/usr/bin/env bash
# Full LIBERO S2 campaign — Gemini 3.1 Pro via OpenRouter.
# 130 tasks, 10 trials each, SOP resume-to-10-successes:
#   - 0 successes in first batch  -> unsolvable_in_first_10, stop.
#   - >=10 cumulative successes    -> ten_successes, stop.
#   - 1..9                         -> resume with more trials (fresh outdir) until 10.
# Sequential launch.py invocations (avoids JAX rwlock D-state from concurrent cold starts).
#
# Usage: run_gemini_campaign.sh <SESSION_DIR> [START_INDEX]
#   START_INDEX (default 0): skip the first N tasks in the list (for resuming the campaign).
set -uo pipefail
cd /k8s-nfs/personal/haoru/cap-x/cap-x

SESSION="$1"
START_INDEX="${2:-0}"
export OPENROUTER_SERVER_URL=http://127.0.0.1:8111/chat/completions
MODEL=openrouter/google/gemini-3.1-pro-preview
MODELSEG=openrouter_google_gemini-3.1-pro-preview
PY=.venv-libero/bin/python
MANIFEST="$SESSION/manifest.jsonl"
COMMIT=$(git rev-parse --short HEAD)
MAX_RESUME_TRIALS=40   # safety cap on cumulative trials for a partial task

# Build task list: every *_S2.yaml, ordered object, spatial, goal, 10, then 90 (numeric).
mapfile -t TASKS < <(
  for s in object spatial goal 10; do
    for i in $(seq 0 9); do
      f="env_configs/libero/franka_libero_${s}_${i}_S2.yaml"
      [ -f "$f" ] && echo "${s}_${i} $f"
    done
  done
  for i in $(seq 0 89); do
    f="env_configs/libero/franka_libero_90_${i}_S2.yaml"
    [ -f "$f" ] && echo "90_${i} $f"
  done
)
echo "=== campaign: ${#TASKS[@]} tasks, starting at index $START_INDEX ==="

count_trials() { find "$1" -maxdepth 1 -name "trial_*" -type d 2>/dev/null | wc -l; }
count_succ()   { find "$1" -maxdepth 1 -name "trial_*_taskcompleted_1" -type d 2>/dev/null | wc -l; }

idx=-1
for spec in "${TASKS[@]}"; do
  idx=$((idx+1))
  [ "$idx" -lt "$START_INDEX" ] && continue
  read -r label config <<< "$spec"

  cum_trials=0; cum_succ=0; round=1; runs_json=""
  while :; do
    if [ "$round" -eq 1 ]; then
      outdir="$SESSION/${label}__S2"; want=10
    else
      outdir="$SESSION/${label}__S2_resume_${round}"
      want=$((10 - cum_succ + 2))   # a few extra to cover failures; capped below
      [ "$want" -lt 1 ] && want=1
    fi
    [ $((cum_trials + want)) -gt "$MAX_RESUME_TRIALS" ] && want=$((MAX_RESUME_TRIALS - cum_trials))
    [ "$want" -lt 1 ] && { echo "[$label] hit MAX_RESUME_TRIALS=$MAX_RESUME_TRIALS, stopping"; break; }

    log="${outdir}.log"
    echo "=== [$(date -u +%H:%M:%S)] [$idx/${#TASKS[@]}] $label round=$round want=$want (cum ${cum_succ}/${cum_trials}) ==="
    start=$(date +%s)
    $PY capx/envs/launch.py --config-path "$config" --model "$MODEL" \
      --total-trials "$want" --num-workers "$want" --output-dir "$outdir" > "$log" 2>&1
    rc=$?
    elapsed=$(( $(date +%s) - start ))

    resultdir="$SESSION/$MODELSEG/$(basename "$outdir")"
    t=$(count_trials "$resultdir"); s=$(count_succ "$resultdir")
    cum_trials=$((cum_trials + t)); cum_succ=$((cum_succ + s))
    echo "=== [$(date -u +%H:%M:%S)] $label round=$round done rc=$rc batch=${s}/${t} cum=${cum_succ}/${cum_trials} ${elapsed}s ==="

    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    printf '{"type":"run","ts":"%s","label":"%s","tier":"S2","round":%s,"config_path":"%s","model":"%s","trials_requested":%s,"output_dir":"%s","git_commit":"%s","launch_rc":%s,"trials_completed":%s,"successes":%s,"failures":%s,"elapsed_s":%s}\n' \
      "$ts" "$label" "$round" "$config" "$MODEL" "$want" "$resultdir" "$COMMIT" "$rc" "$t" "$s" "$((t-s))" "$elapsed" >> "$MANIFEST"
    runs_json="${runs_json:+$runs_json,}\"$resultdir\""

    # stop conditions
    if [ "$cum_succ" -ge 10 ]; then stop="ten_successes"; break; fi
    if [ "$round" -eq 1 ] && [ "$s" -eq 0 ]; then stop="unsolvable_in_first_10"; break; fi
    if [ "$cum_trials" -ge "$MAX_RESUME_TRIALS" ]; then stop="max_trials_reached"; break; fi
    round=$((round+1))
  done

  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{"type":"task_summary","ts":"%s","label":"%s","tier":"S2","stop_reason":"%s","total_trials":%s,"total_successes":%s,"total_failures":%s,"runs":[%s]}\n' \
    "$ts" "$label" "${stop:-unknown}" "$cum_trials" "$cum_succ" "$((cum_trials-cum_succ))" "$runs_json" >> "$MANIFEST"
  echo "=== [$label] SUMMARY: $stop  ${cum_succ}/${cum_trials} ==="
done
echo "=== CAMPAIGN COMPLETE ==="
