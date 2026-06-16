#!/usr/bin/env bash
# Sequential comparison run: Gemini 3.1 Pro on the 7 Opus-4.8 threshold-hit tasks.
# 10 trials each, run one launch.py at a time (avoids JAX rwlock D-state hang).
set -uo pipefail
cd /k8s-nfs/personal/haoru/cap-x/cap-x

SESSION="$1"
export OPENROUTER_SERVER_URL=http://127.0.0.1:8111/chat/completions
MODEL=openrouter/google/gemini-3.1-pro-preview
PY=.venv-libero/bin/python
MANIFEST="$SESSION/manifest.jsonl"
COMMIT=$(git rev-parse --short HEAD)
git diff --quiet && DIRTY=false || DIRTY=true

# task spec: "label config tier"
TASKS=(
  "spatial_0 env_configs/libero/franka_libero_spatial_0_S1.yaml S1"
  "goal_1    env_configs/libero/franka_libero_goal_1_S2.yaml    S2"
  "goal_4    env_configs/libero/franka_libero_goal_4_S2.yaml    S2"
  "10_2      env_configs/libero/franka_libero_10_2_S2.yaml      S2"
  "90_19     env_configs/libero/franka_libero_90_19_S2.yaml     S2"
  "90_20     env_configs/libero/franka_libero_90_20_S2.yaml     S2"
  "90_44     env_configs/libero/franka_libero_90_44_S2.yaml     S2"
)

for spec in "${TASKS[@]}"; do
  read -r label config tier <<< "$spec"
  outdir="$SESSION/${label}__${tier}"
  log="$SESSION/${label}__${tier}.log"
  echo "=== [$(date -u +%H:%M:%S)] launching $label ($tier) ==="
  start=$(date +%s)
  $PY capx/envs/launch.py \
    --config-path "$config" \
    --model "$MODEL" \
    --total-trials 10 --num-workers 10 \
    --output-dir "$outdir" > "$log" 2>&1
  rc=$?
  end=$(date +%s); elapsed=$((end-start))

  # _setup_output_dir inserts the model name BEFORE the last path component, so
  # trials land at <SESSION>/openrouter_google_gemini-3.1-pro-preview/<label>__<tier>/
  resultdir="$SESSION/openrouter_google_gemini-3.1-pro-preview/${label}__${tier}"
  total=$(find "$resultdir" -maxdepth 2 -name "trial_*" -type d 2>/dev/null | wc -l)
  succ=$(find "$resultdir" -maxdepth 2 -name "trial_*_taskcompleted_1" -type d 2>/dev/null | wc -l)
  fail=$((total - succ))
  echo "=== [$(date -u +%H:%M:%S)] $label done rc=$rc trials=$total succ=$succ fail=$fail elapsed=${elapsed}s ==="

  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{"type":"run","ts":"%s","label":"%s","tier":"%s","config_path":"%s","model":"%s","trials_requested":10,"num_workers":10,"output_dir":"%s","git_commit":"%s","git_dirty":%s,"launch_rc":%s,"trials_completed":%s,"successes":%s,"failures":%s,"elapsed_s":%s}\n' \
    "$ts" "$label" "$tier" "$config" "$MODEL" "$resultdir" "$COMMIT" "$DIRTY" "$rc" "$total" "$succ" "$fail" "$elapsed" >> "$MANIFEST"
done
echo "=== ALL DONE ==="
