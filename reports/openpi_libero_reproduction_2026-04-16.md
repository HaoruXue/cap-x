# OpenPI LIBERO / LIBERO-PRO Reproduction Notes

## Scope

This report covers four parallel workstreams completed on `2026-04-16` on the current `dev/vla` branch:

1. OpenPI checkpoint download and direct LIBERO spot-check evals.
2. OpenPI direct LIBERO-PRO spot-check evals.
3. VLA-as-tool integration work inside CaP-X for LIBERO Franka.
4. Initial CaP-X + OpenRouter + OpenPI-tool rollout validation, including MP4 artifact generation.

The upstream OpenPI server was run from `/tmp/openpi` against the `pi05_libero` checkpoint on `127.0.0.1:8000`.

## Environment Notes

- GPU topology used conservatively on this 8xL40 node:
  - OpenPI server: GPU 0
  - Direct eval workers: GPUs 2-4
  - CaP-X/OpenRouter trial: GPU 6
- Required OpenPI runtime flag on this machine:
  - `XLA_FLAGS=--xla_gpu_enable_triton_gemm=false`
- OpenRouter proxy was served from:
  - `http://127.0.0.1:8110/chat/completions`

## Direct OpenPI Results

### Standard LIBERO spot checks

Sampled from `outputs/openpi_libero/spotcheck_logs/`:

| Suite | Task IDs | Successes | Rate |
| --- | --- | --- | --- |
| `libero_spatial` | `0, 5` | `10/10` | `1.0000` |
| `libero_object` | `0, 5` | `10/10` | `1.0000` |
| `libero_goal` | `0, 5` | `9/10` | `0.9000` |
| Total | `6 sampled task/trial bundles` | `29/30` | `0.9667` |

Interpretation:

- The sampled standard LIBERO tasks are consistent with the expected "very strong on vanilla LIBERO" behavior from upstream OpenPI.
- This is still a spot-check, not a full benchmark reproduction across all tasks and episodes.

### LIBERO-PRO spot checks

Sampled from `/tmp/openpi_libero_*`:

| Suite | Task ID | Successes | Rate |
| --- | --- | --- | --- |
| `libero_object_swap` | `0` | `3/5` | `0.6000` |
| `libero_object_swap` | `5` | `0/5` | `0.0000` |
| `libero_spatial_swap` | `0` | `5/5` | `1.0000` |
| `libero_spatial_swap` | `7` | `0/5` | `0.0000` |

Aggregated over the sampled PRO subset:

| Suite | Aggregate |
| --- | --- |
| `libero_object_swap` | `3/10 = 0.3000` |
| `libero_spatial_swap` | `5/10 = 0.5000` |

Interpretation:

- The task-variation drop is already visible in this partial sample.
- The collapse is not uniform; some variations remain easy while others fail completely.
- This is directionally consistent with the LIBERO-PRO claim that OpenPI degrades on certain variations.

## Rollout Videos

### Direct OpenPI videos

- Success example:
  - `outputs/openpi_libero/videos/libero_spatial_task0_pick_up_the_black_bowl_between_the_plate_and_the_ramekin_and_place_it_on_the_plate_success.mp4`
- Failure example:
  - `outputs/openpi_libero/videos/libero_object_swap_task5_pick_up_the_tomato_sauce_and_place_it_in_the_basket_failure.mp4`

These came from real direct-policy rollouts using `capx/envs/scripts/run_openpi_libero_eval.py --record-video`.

### CaP-X rollout videos

The CaP-X validation run also produced MP4s:

- `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/video_combined.mp4`
- `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/video_turn_01.mp4`
- `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/video_turn_02.mp4`
- `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/video_turn_03.mp4`

## CaP-X VLA Tool Integration Status

### What was integrated

OpenPI is now exposed as a first-class LIBERO tool surface in CaP-X:

- `get_openpi_server_info(...)`
- `plan_with_openpi(...)`
- `execute_openpi_step(...)`
- `execute_openpi_plan(...)`
- `get_openpi_action_chunk(...)`
- `get_openpi_subgoal(...)`

There are also VLA-forward API variants and a LIBERO config intended for OpenPI-tool evaluation:

- `capx/integrations/franka/openpi_tooling.py`
- `capx/integrations/franka/libero.py`
- `capx/integrations/franka/libero_reduced.py`
- `capx/integrations/__init__.py`
- `env_configs/libero/franka_libero_object_swap_vla_eval.yaml`

### Did the coding model actually choose the VLA tool?

Yes.

The first generated CaP-X program immediately called:

```python
execute_openpi_plan(
    prompt="Pick the alphabet soup and place it in the basket",
    replan_steps=5,
    execute_subgoals=5
)
```

Artifact:

- `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/code.py`

So the prompt and tool exposure are doing what they were intended to do: the model does try the OpenPI tool first.

## Initial CaP-X/OpenRouter/OpenPI Trial Outcome

Config:

- `env_configs/libero/franka_libero_object_swap_vla_eval.yaml`
- Model: `openrouter/google/gemini-2.5-pro`
- Trials: `1`

Summary:

- Success rate: `0/1`
- Average reward: `0.000`
- Average code blocks: `5`
- Average regenerations: `4`

Artifacts:

- Trial summary:
  - `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/summary.txt`
- Full response trace:
  - `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/all_responses.json`
- Initial prompt:
  - `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/prompts_and_responses/initial_prompt.txt`
- Multi-turn prompts:
  - `outputs/openrouter_google_gemini-2.5-pro/franka_libero_object_swap_vla_eval_initial/trial_01_sandboxrc_1_reward_0.000_taskcompleted_0/prompts_and_responses/multi_turn_prompt_00.txt`
  - `..._01.txt`
  - `..._02.txt`
  - `..._03.txt`

## Blocking Issues Found

### 1. OpenPI websocket incompatibility on the CaP-X LIBERO observation path

The direct standalone OpenPI evaluator works.

The CaP-X OpenPI-tool path does not yet work end-to-end against the same server. The failure occurs inside the upstream OpenPI server during request decoding / preprocessing:

- First observed failure:
  - `IndexError: tuple index out of range` in `openpi/policies/libero_policy.py::_parse_image`
- After forcing image payloads into plain lists:
  - the request got past image parsing, which confirms the bug is in the image serialization boundary
  - but then later hit a secondary type/path issue in the upstream transform stack

Current conclusion:

- The blocker is not model behavior.
- The blocker is not the CaP-X prompt surface.
- The blocker is the request contract between CaP-X and the upstream OpenPI websocket server for this LIBERO environment path.

### 2. No-SAM3 VLA config still exposes fallback tools that assume `sam3`

The no-SAM3 run used a VLA-forward API, but the model still had access to fallback perception functions such as `sample_grasp_pose(...)` and `get_object_pose(...)`.

Those functions eventually touched:

- `self.sam3_seg_fn`

which is unavailable in the no-SAM3 variant, producing:

- `AttributeError: 'FrankaLiberoVLAApi' object has no attribute 'sam3_seg_fn'`

This means the current no-SAM3 variant needs one more cleanup step:

- either expose a stricter VLA-only API surface with no SAM3-dependent fallback tools
- or add explicit non-SAM3 fallbacks for those methods

## Current Read

What is already verified:

- OpenPI checkpoint download is complete.
- Standard LIBERO spot checks are strong.
- LIBERO-PRO sampled variations show the expected drop.
- OpenPI rollout MP4 generation works.
- CaP-X rollout MP4 generation works.
- The coding model does decide to call the OpenPI VLA tool first when it is surfaced as the preferred tool.

What is not yet fully solved:

- clean end-to-end CaP-X execution of an OpenPI-guided LIBERO trial against the upstream websocket server
- clean no-SAM3 fallback surface after the first VLA attempt
- full benchmark sweeps for exact headline reproduction numbers

## Recommended Next Fixes

1. Build a strict `FrankaLiberoVLANoSam3Api` class whose `functions()` only exposes OpenPI planning/execution plus motion primitives that do not require SAM3.
2. Keep the direct OpenPI rollout path as the numerical reproduction baseline while the CaP-X websocket adapter is being stabilized.
3. Patch the CaP-X OpenPI request adapter by mirroring the exact upstream `OffScreenRenderEnv` observation contract, then retest with a single `get_openpi_action_chunk(...)` call before rerunning a full trial.
4. After the adapter is stable, rerun:
   - `1` trial to confirm the first OpenPI tool call executes successfully
   - `5` trials on `libero_object_swap` task `0`
   - `5` trials on one harder failure case such as `libero_object_swap` task `5` or `libero_spatial_swap` task `7`
