#!/usr/bin/env bash
# Trajectory-collection top-up: drive each task to 10 cumulative successes OR a
# trial cap, whichever first. Data-collection mode (not eval) — we want 10 good
# trajectories from any task with a non-zero success rate.
#
# Usage: run_topup.sh <SESSION_DIR> <MODEL> <PROXY_URL> <PRIOR_JSON> [CAP]
#   PRIOR_JSON: path to a JSON file: [{"label","config","prior_trials","prior_succ"}, ...]
#   CAP: cumulative trial cap per task (default 150), counting prior trials.
#
# Each task's prior trials/successes (from the originating campaign) count toward
# the cap and the success target, so we only run the REMAINING trials here.
set -uo pipefail
cd /k8s-nfs/personal/haoru/cap-x/cap-x

SESSION="$1"; MODEL="$2"; PROXY="$3"; PRIOR="$4"; CAP="${5:-150}"
export OPENROUTER_SERVER_URL="$PROXY"
PY=.venv-libero/bin/python
# runner.py _setup_output_dir inserts str(model).replace("/","_") — do NOT strip
# the openrouter_ prefix (it keeps it, e.g. openrouter_anthropic_claude-opus-4).
MODELSEG=$(echo "$MODEL" | sed 's#/#_#g')
MANIFEST="$SESSION/manifest.jsonl"
COMMIT=$(git rev-parse --short HEAD)
mkdir -p "$SESSION"; : > "$MANIFEST"

count_trials() { find "$1" -maxdepth 1 -name "trial_*" -type d 2>/dev/null | wc -l; }
count_succ()   { find "$1" -maxdepth 1 -name "trial_*_taskcompleted_1" -type d 2>/dev/null | wc -l; }

# Iterate the prior-json with python, emit "label|config|prior_trials|prior_succ" lines.
mapfile -t SPECS < <($PY -c "
import json
for d in json.load(open('$PRIOR')):
    print(f\"{d['label']}|{d['config']}|{d['prior_trials']}|{d['prior_succ']}\")
")
echo "=== topup [$MODEL]: ${#SPECS[@]} tasks, cap=$CAP cumulative ==="

for spec in "${SPECS[@]}"; do
  IFS='|' read -r label config pt ps <<< "$spec"
  cum_trials=$pt; cum_succ=$ps; round=1; runs_json=""
  echo "=== [$(date -u +%H:%M:%S)] $label start (prior ${ps}/${pt}) ==="
  while :; do
    if [ "$cum_succ" -ge 10 ]; then stop="ten_successes"; break; fi
    remaining_cap=$((CAP - cum_trials))
    [ "$remaining_cap" -le 0 ] && { stop="cap_reached"; break; }
    need=$((10 - cum_succ))
    # request a batch sized to plausibly get `need` more, but bounded by cap and 30/batch
    # cap batch at 12 workers: two models run concurrently and share the SAM3 FIFO,
    # so keep combined worker count modest (~24 across both campaigns).
    want=$((need * 4)); [ "$want" -gt 12 ] && want=12
    [ "$want" -gt "$remaining_cap" ] && want=$remaining_cap
    [ "$want" -lt 1 ] && want=1

    outdir="$SESSION/${label}__topup_${round}"; log="${outdir}.log"
    echo "  [$(date -u +%H:%M:%S)] $label round=$round want=$want (cum ${cum_succ}/${cum_trials}, cap $CAP)"
    start=$(date +%s)
    $PY capx/envs/launch.py --config-path "$config" --model "$MODEL" \
      --total-trials "$want" --num-workers "$want" --output-dir "$outdir" > "$log" 2>&1
    rc=$?; elapsed=$(( $(date +%s) - start ))
    resultdir="$SESSION/$MODELSEG/$(basename "$outdir")"
    t=$(count_trials "$resultdir"); s=$(count_succ "$resultdir")
    cum_trials=$((cum_trials + t)); cum_succ=$((cum_succ + s))
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    printf '{"type":"run","ts":"%s","label":"%s","round":%s,"config_path":"%s","model":"%s","trials_requested":%s,"output_dir":"%s","git_commit":"%s","launch_rc":%s,"batch_trials":%s,"batch_succ":%s,"cum_trials":%s,"cum_succ":%s,"elapsed_s":%s}\n' \
      "$ts" "$label" "$round" "$config" "$MODEL" "$want" "$resultdir" "$COMMIT" "$rc" "$t" "$s" "$cum_trials" "$cum_succ" "$elapsed" >> "$MANIFEST"
    runs_json="${runs_json:+$runs_json,}\"$resultdir\""
    echo "  -> batch ${s}/${t}, cum ${cum_succ}/${cum_trials}"
    if [ "$t" -eq 0 ]; then stop="launch_failed"; break; fi   # guard: no trials => bail
    round=$((round+1))
  done
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{"type":"task_summary","ts":"%s","label":"%s","model":"%s","stop_reason":"%s","total_trials":%s,"total_successes":%s,"prior_trials":%s,"prior_succ":%s,"runs":[%s]}\n' \
    "$ts" "$label" "$MODEL" "${stop:-unknown}" "$cum_trials" "$cum_succ" "$pt" "$ps" "$runs_json" >> "$MANIFEST"
  echo "=== [$label] DONE: $stop  ${cum_succ}/${cum_trials} ==="
done
echo "=== TOPUP COMPLETE [$MODEL] ==="
