# LIBERO / OpenPI Migration Playbook

This document is the operational guide for moving the current LIBERO, OpenPI, and CaP-X evaluation stack to a new machine.

It covers:
- exact environment setup
- service launch order
- standard verification commands
- direct OpenPI reproduction
- CaP-X native OpenPI alignment checks
- standard LIBERO hybrid VLA experiments
- known sharp edges on shared multi-GPU nodes

## Scope

This playbook is for the setup used during OpenPI and LIBERO / LIBERO-PRO investigation on an 8xL40 node. The main assumptions are:
- Linux
- CUDA-capable NVIDIA GPUs
- `uv` available
- enough disk for the repo, submodules, and an external OpenPI checkout

There are three distinct runtime environments:
- repo base env: `.venv`
- LIBERO env: `.venv-libero`
- upstream OpenPI checkout: separate repo, typically `/tmp/openpi` or `/path/to/openpi`

Keep them separate. That split matters.

## Port Map

These are the ports used by the current stack.

| Service | Port | Notes |
| ------- | ---- | ----- |
| NVIDIA / OpenRouter-style LLM proxy | `8110` | OpenAI-compatible `/chat/completions` |
| SAM3 | `8114` | segmentation |
| Contact-GraspNet | `8115` | grasp proposals |
| PyRoKi | `8116` | IK / kinematic helper |
| Molmo2 | `8122` | optional object-centric pointing |
| OpenPI | `8000` | websocket policy server plus `/healthz` |

Do not change these casually. Several configs and helper defaults assume them.

## Repository Setup

Clone CaP-X with submodules:

```bash
git clone --recurse-submodules https://github.com/capgym/cap-x.git
cd cap-x
```

If the repo already exists:

```bash
git submodule update --init --recursive
```

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create the base env:

```bash
uv python install 3.10
uv venv -p 3.10
uv sync
```

Optional extras used in this workflow:

```bash
uv sync --extra molmo
```

## LIBERO Environment Setup

LIBERO uses its own env because of the `robosuite` version split.

```bash
uv venv .venv-libero --python 3.12
source .venv-libero/bin/activate
uv sync --active --extra libero --extra contactgraspnet
```

On headless servers:

```bash
sudo apt-get update
sudo apt-get install -y libegl1 libgl1
export MUJOCO_GL=egl
```

### Non-Interactive LIBERO Config

LIBERO will otherwise try to prompt interactively. Pre-create the config:

```bash
mkdir -p ~/.libero
cat > ~/.libero/config.yaml <<EOF
assets: $(pwd)/capx/third_party/LIBERO-PRO/libero/libero/assets
bddl_files: $(pwd)/capx/third_party/LIBERO-PRO/libero/libero/bddl_files
benchmark_root: $(pwd)/capx/third_party/LIBERO-PRO/libero/libero
datasets: $(pwd)/capx/third_party/LIBERO-PRO/libero/libero/../datasets
init_states: $(pwd)/capx/third_party/LIBERO-PRO/libero/libero/init_files
EOF
```

Check it once:

```bash
source .venv-libero/bin/activate
python -c "from libero import benchmark; print(sorted(list(benchmark.get_benchmark_dict().keys()))[:8])"
```

## Upstream OpenPI Setup

OpenPI should live in a separate checkout.

```bash
git clone --recurse-submodules https://github.com/Physical-Intelligence/openpi.git /tmp/openpi
cd /tmp/openpi
uv sync
uv pip install -e .
```

The `pi05_libero` checkpoint used in these experiments is:
- config: `pi05_libero`
- checkpoint: `gs://openpi-assets/checkpoints/pi05_libero`

The CaP-X launcher wraps upstream OpenPI. On L40s, use the XLA workaround below.

## Keys And Secrets

Never commit these files:
- `.openrouterkey`
- `.nvinferencekey`

Typical layouts:

```bash
echo "sk-or-..." > .openrouterkey
printf '%s\n%s\n' 'nvapi-...' 'nvapi-...' > .nvinferencekey
```

The NVIDIA proxy supports multiple keys in one file and rotates across them.

## Recommended Launch Order

This order reduces false negatives during startup.

### 1. LLM proxy

NVIDIA Inference:

```bash
uv run --no-sync --active capx/serving/nv_server.py \
  --key-file .nvinferencekey \
  --port 8110
```

OpenRouter:

```bash
uv run --no-sync --active capx/serving/openrouter_server.py \
  --key-file .openrouterkey \
  --port 8110
```

Quick health check:

```bash
curl -s http://127.0.0.1:8110/health
```

### 2. Perception servers

From the repo root:

```bash
uv run --no-sync --active capx/serving/launch_servers.py --profile default
```

That launches:
- SAM3 on `8114`
- Contact-GraspNet on `8115`
- PyRoKi on `8116`

### 3. OpenPI

From the repo root, with the LIBERO env active:

```bash
source .venv-libero/bin/activate
XLA_FLAGS=--xla_gpu_enable_triton_gemm=false \
OPENPI_ROOT=/tmp/openpi \
uv run --no-sync --active capx/serving/launch_openpi_server.py \
  --policy-config pi05_libero \
  --policy-dir gs://openpi-assets/checkpoints/pi05_libero \
  --port 8000
```

Quick health check:

```bash
curl -s http://127.0.0.1:8000/healthz
```

### 4. Optional Molmo2

Run this from the base `.venv`, not `.venv-libero`.

```bash
source .venv/bin/activate
CUDA_VISIBLE_DEVICES=0 uv run --active --no-sync vllm serve allenai/Molmo2-8B \
  --trust-remote-code \
  --port 8122 \
  --max-num-batched-tokens 36864 \
  --dtype bfloat16 \
  --limit-mm-per-prompt.image 2
```

If the node is crowded, reduce `--gpu-memory-utilization` or move Molmo to a less loaded GPU. On this machine, ghost allocations often prevented Molmo from launching reliably.

## Model IDs That Matter

The provider-specific model name must be correct.

For NVIDIA Inference, these were the important IDs:
- `openai/openai/gpt-5.4`
- `gcp/google/gemini-3.1-pro-preview`

The shorter `openai/gpt-5.4` is not the same thing for the NVIDIA endpoint. Use the fully qualified ID.

## Basic Service Verification

Before any longer run, do these checks.

### Check NVIDIA GPT-5.4 through the proxy

```bash
curl -s http://127.0.0.1:8110/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"openai/openai/gpt-5.4",
    "messages":[{"role":"user","content":"Reply with exactly OK."}],
    "temperature":0
  }'
```

Expected: response content is `OK`.

### Check OpenPI is serving

```bash
curl -s http://127.0.0.1:8000/healthz
```

Expected: HTTP `200`.

### Check LIBERO benchmark visibility

```bash
source .venv-libero/bin/activate
python -c "
from libero import benchmark
names = sorted(benchmark.get_benchmark_dict().keys())
print('libero_spatial' in names, 'libero_object_swap' in names, 'libero_spatial_swap' in names)
"
```

## Direct OpenPI Reproduction

Use this path when you want upstream-style VLA numbers and no code-generation loop.

### Standard LIBERO

```bash
source .venv-libero/bin/activate

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_spatial \
  --port 8000

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object \
  --port 8000

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_goal \
  --port 8000

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_10 \
  --port 8000
```

Upstream reference numbers for `pi05_libero` are approximately:
- `libero_spatial`: `98.8`
- `libero_object`: `98.2`
- `libero_goal`: `98.0`
- `libero_10`: `92.4`

### LIBERO-PRO

The safest local suites in this checkout are:
- `libero_object_swap`
- `libero_spatial_swap`

Commands:

```bash
source .venv-libero/bin/activate

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_object_swap \
  --port 8000

uv run --no-sync --active capx/envs/scripts/run_openpi_libero_eval.py \
  --task-suite-name libero_spatial_swap \
  --port 8000
```

Some other vendored PRO suites may need additional upstream assets before they run cleanly.

## Native OpenPI Alignment Check

Before trusting CaP-X hybrid VLA experiments, check that native OpenPI execution inside CaP-X matches direct LIBERO closely enough.

Use:

```bash
source .venv-libero/bin/activate

uv run --no-sync --active capx/envs/scripts/measure_openpi_native_alignment.py \
  --cases libero_spatial:0 libero_object:0 libero_goal:0 \
  --trials-per-task 1 \
  --compare-steps 320 \
  --output-json outputs/openpi_native_alignment/alignment_task0_fullrollout.json

uv run --no-sync --active capx/envs/scripts/measure_openpi_native_alignment.py \
  --cases libero_spatial:5 libero_object:5 libero_goal:5 \
  --trials-per-task 1 \
  --compare-steps 320 \
  --output-json outputs/openpi_native_alignment/alignment_task5_fullrollout.json
```

What these checks establish:
- same OpenPI action chunk
- same next-state rollout in direct LIBERO and CaP-X native OpenPI path
- same `done` outcome
- same rollout success outcome

On the current node, the full-rollout spot checks gave:
- `6/6` done-match
- `6/6` success-match
- worst end-effector drift about `0.00127 m`
- worst quaternion angle error about `0.00304 rad`

Artifacts:
- `outputs/openpi_native_alignment/alignment_task0_fullrollout.json`
- `outputs/openpi_native_alignment/alignment_task5_fullrollout.json`

## Scripted Oracle In `launch.py`

Use this when you want to confirm that the CaP-X `launch.py` path can drive native OpenPI directly, without a coding model in the loop.

Create a local oracle config from a tracked standard LIBERO config:

```bash
cp env_configs/libero/franka_libero_spatial_0.yaml \
   env_configs/libero/franka_libero_spatial_0_openpi_oracle.local.yaml
```

Then edit the copied YAML to use the native OpenPI oracle path for your local experiment.

Example launch:

```bash
source .venv-libero/bin/activate
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/libero/franka_libero_spatial_0_openpi_oracle.local.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --total-trials 3 \
  --num-workers 1
```

Expected outcome:
- reward-based success on `libero_spatial task 0`
- artifacts written under `outputs/`

This path is useful because it exercises CaP-X launch infrastructure while still using scripted native OpenPI execution.

## Standard LIBERO Hybrid VLA + Code Experiment

This is the first hybrid experiment to run after alignment is confirmed.

Create a local hybrid config from a tracked base config:

```bash
cp env_configs/libero/franka_libero_spatial_0.yaml \
   env_configs/libero/franka_libero_spatial_0_vla_native_eval.local.yaml
```

Then edit the copied YAML to expose the native OpenPI APIs and add the multi-turn / VLA prompt you want to test.

```bash
source .venv-libero/bin/activate
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/libero/franka_libero_spatial_0_vla_native_eval.local.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions \
  --total-trials 1 \
  --num-workers 1
```

This config is intended to:
- expose native OpenPI as a tool
- let the coding model decide whether to call it
- continue with code as policy afterward

Artifacts to inspect:
- `initial_prompt.txt`
- `all_responses.json`
- `trial_*/code.py`
- `trial_*/summary.txt`
- `trial_*/video_combined.mp4`

## LIBERO-PRO Baseline And VLA Hillclimb

Once standard LIBERO is stable, move to LIBERO-PRO.

Useful local config names from this investigation were:
- `hillclimb_object_swap_0_clean_fast`
- `hillclimb_spatial_swap_0_clean_fast`
- `hillclimb_object_swap_0_vla_reduced_fast`
- `hillclimb_object_swap_0_vla_native_fast`

These were local experiment YAMLs rather than stable repo entry points. On a new machine, recreate them by copying a tracked LIBERO-PRO config such as `env_configs/libero/franka_libero_object_swap_vla_eval.yaml` and then trimming it for the narrow task you want to test.

Typical clean baseline:

```bash
source .venv-libero/bin/activate
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/libero/your_local_object_swap_clean_fast.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions
```

Typical native VLA hillclimb:

```bash
source .venv-libero/bin/activate
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/libero/your_local_object_swap_vla_native_fast.yaml \
  --model openai/openai/gpt-5.4 \
  --server-url http://127.0.0.1:8110/chat/completions
```

## Debugging Checklist

If a run fails, check these in order.

### LLM side

- `curl http://127.0.0.1:8110/health`
- tiny completion against `openai/openai/gpt-5.4`
- proxy logs for `401`, `403`, or `429`

If NVIDIA returns repeated `429`, the proxy may still be healthy but the keys are rate-limited.

### OpenPI side

- `curl http://127.0.0.1:8000/healthz`
- server logs for JAX / XLA startup failures
- confirm `XLA_FLAGS=--xla_gpu_enable_triton_gemm=false` on L40 nodes

### Perception side

- confirm `8114`, `8115`, `8116` are all up
- confirm Hugging Face auth for SAM3
- if Molmo-dependent flows fail, verify `8122`

### Artifact inspection

Inspect these files first:
- `initial_prompt.txt`
- `all_responses.json`
- `trial_*/summary.txt`
- `trial_*/stderr.txt`
- `trial_*/video_combined.mp4`
- `trial_*/code.py`

## Shared-GPU Node Notes

On busy nodes, you may see large GPU allocations in `nvidia-smi` for PIDs that do not exist in `/proc`. That usually means stale driver-side allocations or processes in another namespace.

Useful checks:

```bash
nvidia-smi
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv
nvidia-smi -q -d PIDS
```

If the PIDs are missing from `/proc`, you usually cannot kill them directly from this shell. On this node, `nvidia-smi --gpu-reset` also failed with insufficient permissions, so the practical workaround was:
- reduce Molmo memory
- move Molmo to a less loaded GPU
- or migrate to a cleaner machine

## What To Carry To A New Machine

Minimum checklist:

1. Clone `cap-x` with submodules.
2. Recreate `.venv` and `.venv-libero`.
3. Recreate `~/.libero/config.yaml`.
4. Clone `/tmp/openpi` or another OpenPI checkout.
5. Restore `.openrouterkey` or `.nvinferencekey` locally.
6. Launch `8110`, `8114-8116`, and `8000` in that order.
7. Run the OpenPI alignment script before hybrid experiments.
8. Only then run `launch.py` hybrid VLA configs.

## Notes Worth Remembering

- The native OpenPI path is the one to trust, not the older interpreted Cartesian approximation.
- For NVIDIA Inference, use provider-qualified model IDs.
- Molmo should run from the base `.venv`.
- LIBERO should run from `.venv-libero`.
- OpenPI should stay in its own checkout.
- Never commit API key files.
