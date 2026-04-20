# Results

Last updated: 2026-04-20

## Setup

These comparisons assume the following services are already running:

- NVIDIA-compatible LLM proxy on `http://127.0.0.1:8110/chat/completions`
- OpenPI server on `127.0.0.1:8000`
- SAM3 on `127.0.0.1:8114`
- Contact-GraspNet on `127.0.0.1:8115`
- PyRoKi on `127.0.0.1:8116`
- Molmo2 on `127.0.0.1:8122` when available

The coding / visual model used in current comparisons is:

- `openai/openai/gpt-5.4`

## Scripts

Three Python entrypoints are used for the main comparison matrix:

- Pure VLA / direct OpenPI:
  - `capx/envs/scripts/run_openpi_libero_eval.py`
- Clean coding-agent baseline:
  - `capx/envs/scripts/run_libero_batch.py`
- Hybrid coding-agent + VLA:
  - `capx/envs/launch.py`

## Core Launch Commands

### Pure VLA / Direct OpenPI

```bash
.venv-libero/bin/python3 capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object_swap \
  --task-id 9 \
  --num-trials-per-task 20 \
  --port 8000
```

### Clean CaP-X Coding Agent

```bash
.venv-libero/bin/python3 capx/envs/scripts/run_libero_batch.py \
  --args.base-config-path env_configs/libero/hillclimb_object_swap_0_clean_fast.yaml \
  --args.suites libero_object_swap \
  --args.task-id-start 9 \
  --args.task-id-end 9 \
  --args.models openai/openai/gpt-5.4 \
  --args.server-url http://127.0.0.1:8110/chat/completions \
  --args.max-tokens 4096 \
  --args.reasoning-effort low \
  --args.total-trials 20 \
  --args.output-dir ./outputs/object_swap_task9_clean_20trials
```

### Hybrid CaP-X + VLA

```bash
.venv-libero/bin/python3 capx/envs/launch.py \
  --config-path env_configs/libero/hillclimb_object_swap_9_vla_minimal_v4.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --visual-differencing-model openai/openai/gpt-5.4 \
  --visual-differencing-model-server-url http://127.0.0.1:8110/chat/completions \
  --max-tokens 4096 \
  --reasoning-effort low \
  --total-trials 20 \
  --output-dir ./outputs/object_swap_task9_hybrid_20trials_v4
```

## Current Best Hybrid Configs

- Orange juice:
  - `env_configs/libero/hillclimb_object_swap_9_vla_minimal_v4.yaml`
- Orange juice, stricter placement gate:
  - `env_configs/libero/hillclimb_object_swap_9_vla_minimal_v5.yaml`
- Salad dressing:
  - `env_configs/libero/hillclimb_object_swap_2_vla_minimal_v1.yaml`
- Butter:
  - `env_configs/libero/hillclimb_object_swap_6_vla_minimal_v4.yaml`

## Latest 10-Trial Comparison Snapshot

### LIBERO-PRO Object Swap

| Task | Pure VLA | Clean CaP-X | Hybrid |
|---|---:|---:|---:|
| Orange juice (`task_id=9`) | `0/10` | `9/10` | `3/10` with `v4`, `0/10` with `v5` |
| Salad dressing (`task_id=2`) | `0/10` | `6/10` | `0/10` with `v1` |
| Butter (`task_id=6`) | `1/10` | `8/10` | `0/10` with `v3` |

Notes:

- The earlier one-trial broad scout made orange juice look like the strongest hybrid candidate.
- The 10-trial targeted rerun did not hold that result: hybrid beat pure VLA on orange juice, but not clean CaP-X.
- Butter currently looks the most hillclimbable because Molmo is responding better to `stick of butter` than plain `butter`.

## Current Artifact Pointers

### Hybrid Orange Juice

- Success:
  - `outputs/openai_openai_gpt-5.4/object_swap_task9_hybrid_10trials_v4/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
- Failure:
  - `outputs/openai_openai_gpt-5.4/object_swap_task9_hybrid_10trials_v4/trial_01_sandboxrc_0_reward_0.000_taskcompleted_0`

### Clean Orange Juice

- Success:
  - `outputs/object_swap_task9_clean_10trials/libero_object_swap/pick_up_the_orange_juice_and_place_it_in_the_basket/openai_openai_gpt-5.4/run/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`

### Clean Salad Dressing

- Success:
  - `outputs/object_swap_task2_clean_10trials/libero_object_swap/pick_up_the_salad_dressing_and_place_it_in_the_basket/openai_openai_gpt-5.4/run/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`

### Clean Butter

- Success:
  - `outputs/object_swap_task6_clean_10trials/libero_object_swap/pick_up_the_butter_and_place_it_in_the_basket/openai_openai_gpt-5.4/run/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`

## Current Interpretation

- On targeted 10-trial reruns, no hybrid configuration is yet better than both pure VLA and clean CaP-X.
- Hybrid is currently only clearly better than pure VLA on orange juice.
- The most actionable current failure mode is prompt/perception mismatch for local object grounding, especially on butter.

## Next 20-Trial Matrix

The next intended 20-trial comparisons are:

- Orange juice:
  - pure VLA
  - clean CaP-X
  - hybrid `v4`
- Salad dressing:
  - pure VLA
  - clean CaP-X
  - hybrid `v1`
- Butter:
  - pure VLA
  - clean CaP-X
  - hybrid `v4`

## Example 20-Trial Commands

### Orange Juice

```bash
.venv-libero/bin/python3 capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object_swap \
  --task-id 9 \
  --num-trials-per-task 20 \
  --port 8000

.venv-libero/bin/python3 capx/envs/scripts/run_libero_batch.py \
  --args.base-config-path env_configs/libero/hillclimb_object_swap_0_clean_fast.yaml \
  --args.suites libero_object_swap \
  --args.task-id-start 9 \
  --args.task-id-end 9 \
  --args.models openai/openai/gpt-5.4 \
  --args.server-url http://127.0.0.1:8110/chat/completions \
  --args.max-tokens 4096 \
  --args.reasoning-effort low \
  --args.total-trials 20 \
  --args.output-dir ./outputs/object_swap_task9_clean_20trials

.venv-libero/bin/python3 capx/envs/launch.py \
  --config-path env_configs/libero/hillclimb_object_swap_9_vla_minimal_v4.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --visual-differencing-model openai/openai/gpt-5.4 \
  --visual-differencing-model-server-url http://127.0.0.1:8110/chat/completions \
  --max-tokens 4096 \
  --reasoning-effort low \
  --total-trials 20 \
  --output-dir ./outputs/object_swap_task9_hybrid_20trials_v4
```

### Salad Dressing

```bash
.venv-libero/bin/python3 capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object_swap \
  --task-id 2 \
  --num-trials-per-task 20 \
  --port 8000

.venv-libero/bin/python3 capx/envs/scripts/run_libero_batch.py \
  --args.base-config-path env_configs/libero/hillclimb_object_swap_0_clean_fast.yaml \
  --args.suites libero_object_swap \
  --args.task-id-start 2 \
  --args.task-id-end 2 \
  --args.models openai/openai/gpt-5.4 \
  --args.server-url http://127.0.0.1:8110/chat/completions \
  --args.max-tokens 4096 \
  --args.reasoning-effort low \
  --args.total-trials 20 \
  --args.output-dir ./outputs/object_swap_task2_clean_20trials

.venv-libero/bin/python3 capx/envs/launch.py \
  --config-path env_configs/libero/hillclimb_object_swap_2_vla_minimal_v1.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --visual-differencing-model openai/openai/gpt-5.4 \
  --visual-differencing-model-server-url http://127.0.0.1:8110/chat/completions \
  --max-tokens 4096 \
  --reasoning-effort low \
  --total-trials 20 \
  --output-dir ./outputs/object_swap_task2_hybrid_20trials_v1
```

### Butter

```bash
.venv-libero/bin/python3 capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object_swap \
  --task-id 6 \
  --num-trials-per-task 20 \
  --port 8000

.venv-libero/bin/python3 capx/envs/scripts/run_libero_batch.py \
  --args.base-config-path env_configs/libero/hillclimb_object_swap_0_clean_fast.yaml \
  --args.suites libero_object_swap \
  --args.task-id-start 6 \
  --args.task-id-end 6 \
  --args.models openai/openai/gpt-5.4 \
  --args.server-url http://127.0.0.1:8110/chat/completions \
  --args.max-tokens 4096 \
  --args.reasoning-effort low \
  --args.total-trials 20 \
  --args.output-dir ./outputs/object_swap_task6_clean_20trials

.venv-libero/bin/python3 capx/envs/launch.py \
  --config-path env_configs/libero/hillclimb_object_swap_6_vla_minimal_v4.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --visual-differencing-model openai/openai/gpt-5.4 \
  --visual-differencing-model-server-url http://127.0.0.1:8110/chat/completions \
  --max-tokens 4096 \
  --reasoning-effort low \
  --total-trials 20 \
  --output-dir ./outputs/object_swap_task6_hybrid_20trials_v4
```
