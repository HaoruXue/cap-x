# Hybrid CaP-X + OpenPI Notes

This note summarizes the current combined agent + VLA setup, the first successful hillclimb result, and the constraints that mattered most.

The goal of this setup is not to replace CaP-X with OpenPI. The useful regime is:
- use OpenPI as a native short-horizon policy tool
- let the coding agent decide when to invoke it
- keep the fallback code-as-policy path available when VLA is clearly not enough

## Main Findings

### 1. Native OpenPI execution matters

The old interpreted OpenPI path was too lossy. The useful path is the native one:
- query OpenPI from the native LIBERO `OSC_POSE` observation contract
- execute raw 7D OpenPI actions on a synced native LIBERO env
- sync the resulting state back into the visible CaP-X env

This is exposed through:
- `get_openpi_native_action_chunk(...)`
- `execute_openpi_raw_action(...)`
- `execute_openpi_native_step(...)`
- `execute_openpi_native_plan(...)`

### 2. Standard LIBERO should start from the untouched reset state

This was the most important hillclimb result.

For standard LIBERO tasks:
- do **not** call `goto_home_joint_position()` before the first OpenPI plan
- do **not** pre-open / pre-close the gripper before the first OpenPI plan
- call native OpenPI directly from the reset observation

Moving to home before the first OpenPI call created a distribution shift and hurt the rollout badly.

### 3. OpenPI needs enough horizon

Giving OpenPI only one short call and then forcing the agent into explicit segmentation code was a mistake.

The successful standard-LIBERO hybrid run used repeated native replans:
- `execute_openpi_native_plan(replan_steps=5, execute_actions=5)`
- repeated across multiple regenerations
- stopping immediately if `native_done` became true

The direct OpenPI rollout on `libero_spatial task 0` took on the order of `~75` env steps, so the hybrid controller needed a comparable horizon before concluding that VLA had failed.

### 4. These trained VLA policies are better as local subtask priors than as global workspace planners

Operationally, the current OpenPI/LIBERO policy behaves more like this:
- strong when already near the relevant object or in the right local workspace
- useful for short-horizon pickup / placement continuation
- weaker at large workspace relocation or choosing a globally correct approach from a poor state

So the coding-agent prompt should assume:
- VLA may be good for subtasks
- VLA location generation is not always good over the full workspace
- VLA tends to work better once the end effector is already over / near the object

That means the hybrid agent should:
- try native OpenPI first on standard LIBERO from reset
- keep using it while the rollout is on-distribution
- switch to explicit code only after repeated native replans clearly fail
- use explicit code to recover global geometry or workspace-level search failures

## First Successful Hybrid Hillclimb

Task:
- `libero_spatial`
- `task_id=0`
- language: `Pick the akita black bowl between the plate and the ramekin and place it on the plate`

Model / backend:
- coding model: `openai/openai/gpt-5.4`
- proxy: NVIDIA Inference via local `nv_server`

Successful config:
- [env_configs/libero/franka_libero_spatial_0_vla_native_eval_hillclimb_v2.yaml](/root/cap-x/env_configs/libero/franka_libero_spatial_0_vla_native_eval_hillclimb_v2.yaml:1)

Successful artifacts:
- [summary.txt](/root/cap-x/outputs/openai_openai_gpt-5.4/hillclimb_runs_v2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1/summary.txt)
- [code.py](/root/cap-x/outputs/openai_openai_gpt-5.4/hillclimb_runs_v2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1/code.py)
- [video_combined.mp4](/root/cap-x/outputs/openai_openai_gpt-5.4/hillclimb_runs_v2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1/video_combined.mp4)

The generated program shape was simple:
- repeated loops over `execute_openpi_native_plan(replan_steps=5, execute_actions=5)`
- break immediately on `native_done`
- no hand-written segmentation / grasp / placement fallback code was needed for this successful run

## Prompt Guidance

The prompt that worked better had these properties:

- preserve the exact LIBERO task string
- do not paraphrase the task before sending it to OpenPI
- do not move to home before the first OpenPI call on standard LIBERO
- use native OpenPI directly from reset
- allow multiple native replans before giving up
- only switch to explicit code after repeated native failures

For LIBERO-PRO, a slightly different guidance is likely better:
- VLA is useful as a subtask prior
- VLA is less trustworthy for global location generation under perturbations
- the agent should use VLA when the robot is already near the target object or the local geometry is favorable
- if the state is off-distribution, use explicit code to recover the right local geometry first, then call VLA again

## Standard LIBERO Launch Recipe

Bring up the backend stack first:

```bash
uv run --no-sync --active capx/serving/nv_server.py --key-file .nvinferencekey --port 8110
uv run --no-sync --active capx/serving/launch_servers.py --profile default

source .venv-libero/bin/activate
XLA_FLAGS=--xla_gpu_enable_triton_gemm=false \
OPENPI_ROOT=/tmp/openpi \
uv run --no-sync --active capx/serving/launch_openpi_server.py \
  --policy-config pi05_libero \
  --policy-dir gs://openpi-assets/checkpoints/pi05_libero \
  --port 8000
```

Then run the hybrid hillclimb:

```bash
source .venv-libero/bin/activate
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/libero/franka_libero_spatial_0_vla_native_eval_hillclimb_v2.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions
```

## Standard LIBERO Oracle / Alignment Helpers

Useful companion files:
- [env_configs/libero/franka_libero_spatial_0_openpi_oracle.yaml](/root/cap-x/env_configs/libero/franka_libero_spatial_0_openpi_oracle.yaml:1)
- [env_configs/libero/franka_libero_spatial_0_vla_native_eval.yaml](/root/cap-x/env_configs/libero/franka_libero_spatial_0_vla_native_eval.yaml:1)
- [capx/envs/scripts/measure_openpi_native_alignment.py](/root/cap-x/capx/envs/scripts/measure_openpi_native_alignment.py:1)

The alignment check should be considered mandatory before trusting hybrid results on a new machine.

## What To Watch In Videos And Logs

Good hybrid behavior:
- first code block is native OpenPI from reset
- no immediate `goto_home_joint_position()`
- no huge segmentation-heavy fallback after a single failed OpenPI step
- repeated native replans while the task remains on-distribution

Bad hybrid behavior:
- home-reset before first OpenPI call
- paraphrased prompt rather than exact LIBERO language
- very short VLA horizon followed by manual recovery
- repeated native replans after the arm has clearly drifted into a bad workspace region without any corrective logic

Files to inspect first:
- `initial_prompt.txt`
- `all_responses.json`
- `trial_*/code.py`
- `trial_*/summary.txt`
- `trial_*/video_combined.mp4`

## Current Limitations

- Molmo startup is still less reliable than the rest of the stack on some nodes.
- Multi-worker LIBERO startup can add noisy MuJoCo / offscreen-init overhead; serial or lightly parallel runs are more stable for debugging.
- The current successful result is still a narrow hillclimb result on standard LIBERO, not yet a broad suite-level hybrid benchmark.

## Next Steps

The next sensible sequence is:

1. Re-run the `v2` hybrid config for a small standard-LIBERO sample to check stability.
2. Port the same prompt shape to one or two LIBERO-PRO tasks.
3. Add explicit prompt guidance that VLA is best for local subtasks and can be poor at workspace-scale location generation.
4. Let the coding agent recover global geometry first, then hand control back to VLA once the end effector is near the object.
