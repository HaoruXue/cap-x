# Configuration Reference

## CLI flags

Override any YAML config field from the command line:

```bash
uv run --no-sync --active capx/envs/launch.py \
    --config-path <config.yaml> \
    --model google/gemini-3.1-pro-preview \
    --server-url http://127.0.0.1:8110/chat/completions \
    --temperature 1.0 \
    --total-trials 100 \
    --num-workers 12 \
    --record-video True
```

| Flag                | Default                                  | Description                           |
| ------------------- | ---------------------------------------- | ------------------------------------- |
| `--config-path`     | *(required)*                             | Path to YAML task config              |
| `--model`           | `google/gemini-3.1-pro-preview`          | Model name                            |
| `--server-url`      | `http://127.0.0.1:8110/chat/completions` | LLM endpoint                          |
| `--temperature`     | `1.0`                                    | Sampling temperature                  |
| `--total-trials`    | from YAML                                | Number of evaluation trials           |
| `--num-workers`     | from YAML                                | Parallel worker count                 |
| `--web-ui`          | `False`                                  | Launch interactive web UI             |
| `--use-oracle-code` | `False`                                  | Run human-written reference solutions |

## YAML config format

```yaml
# env_configs/my_task/my_task.yaml
env:
  _target_: capx.envs.tasks.my_robot.my_task.MyTaskCodeEnv
  cfg:
    _target_: capx.envs.tasks.base.CodeExecEnvConfig
    low_level: my_sim_env
    privileged: false
    apis:
      - FrankaControlApi

record_video: true
output_dir: ./outputs/my_task
trials: 100
num_workers: 12
```

The `_target_` keys enable Hydra-style lazy instantiation via `capx.envs.configs.instantiate()`.

### Perception servers (api_servers)

YAML configs can include an `api_servers` section that **auto-launches** perception servers when the evaluation starts:

```yaml
api_servers:
  - _target_: capx.serving.launch_sam3_server.main
    device: cuda
    port: 8114
    host: 127.0.0.1

  - _target_: capx.serving.launch_contact_graspnet_server.main
    port: 8115
    host: 127.0.0.1

  - _target_: capx.serving.launch_pyroki_server.main
    port: 8116
    host: 127.0.0.1
    robot: panda_description
    target_link: panda_hand
```

The launcher automatically:
- Skips servers whose port is already in use (e.g. started externally)
- Waits for all servers to be ready before running trials
- Terminates all servers on exit

If you prefer to manage servers separately (e.g. for sharing across multiple eval runs), use `launch_servers.py`:

```bash
uv run --no-sync --active capx/serving/launch_servers.py --profile default
```

| Profile | Servers | GPU Required |
|---------|---------|-------------|
| `default` | SAM3 (8114) + ContactGraspNet (8115) + PyRoKi (8116) | Yes (~5 GB VRAM) |
| `full` | default + OWL-ViT (8118) + SAM2 (8113) | Yes (~14 GB VRAM) |
| `minimal` | PyRoKi (8116) only | No (CPU-only) |

### OpenPI policy server

CaP-X can also launch an upstream [OpenPI](https://github.com/Physical-Intelligence/openpi) websocket policy server through a thin wrapper in `capx/serving`.

This is a separate policy-serving path from the OpenAI-compatible LLM proxies below:
- OpenPI serves robot actions over websocket plus `GET /healthz`
- OpenRouter/vLLM serve LLM generations over `POST /chat/completions`

Set up OpenPI in its own checkout first:

```bash
git clone --recurse-submodules https://github.com/Physical-Intelligence/openpi.git /path/to/openpi
cd /path/to/openpi
uv sync
```

Then launch it through CaP-X:

```bash
OPENPI_ROOT=/path/to/openpi \
uv run --no-sync --active capx/serving/launch_openpi_server.py --env libero --port 8000
```

To serve a custom checkpoint instead of a built-in OpenPI environment preset:

```bash
OPENPI_ROOT=/path/to/openpi \
uv run --no-sync --active capx/serving/launch_openpi_server.py \
    --policy-config pi05_libero \
    --policy-dir gs://openpi-assets/checkpoints/pi05_libero \
    --port 8000
```

The wrapper:
- Runs OpenPI in the OpenPI project environment via `uv run --project`
- Waits for `http://127.0.0.1:<port>/healthz` before reporting readiness
- Forwards SIGINT and SIGTERM so shutdown behaves like the other CaP-X launchers

When a LIBERO config uses `FrankaLiberoApi`, `FrankaLiberoApiReduced`, `FrankaLiberoVLAApi`, or `FrankaLiberoVLAApiReduced`, the coding agent can treat OpenPI as a first-class tool instead of only reading raw action chunks. The main tool-facing helpers are:
- `get_openpi_server_info(...)` to verify which OpenPI endpoint is active
- `plan_with_openpi(...)` to lift the VLA action chunk into Cartesian subgoals
- `execute_openpi_step(...)` to query OpenPI and execute a single interpreted subgoal
- `execute_openpi_plan(...)` to execute a short OpenPI-guided sequence through CaP-X's own IK / motion stack

See `env_configs/libero/franka_libero_object_swap_vla_eval.yaml` for a VLA-forward LIBERO-PRO example config.

## Adding new LLM providers

CaP-X queries language models through a local proxy server that exposes an OpenAI-compatible `/chat/completions` endpoint.

### OpenRouter (recommended for getting started)

1. Get an API key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Save it to a file in the project root:
   ```bash
   echo "sk-or-v1-your-key-here" > .openrouterkey
   ```
3. Start the proxy (supports automatic key rotation across multiple keys):
   ```bash
   uv run --no-sync --active capx/serving/openrouter_server.py --key-file .openrouterkey --port 8110
   ```

OpenRouter provides access to Gemini, GPT, Claude, DeepSeek, Qwen, and other models through a single API key.

### NVIDIA Inference

NVIDIA Inference can be used through the local proxy in `capx/serving/nv_server.py`.

1. Save one or more NVIDIA keys:
   ```bash
   printf '%s\n%s\n' 'nvapi-key-1' 'nvapi-key-2' > .nvinferencekey
   ```
2. Launch the proxy:
   ```bash
   uv run --no-sync --active capx/serving/nv_server.py --key-file .nvinferencekey --port 8110
   ```
3. Use provider-qualified model IDs. Important examples:
   ```text
   openai/openai/gpt-5.4
   gcp/google/gemini-3.1-pro-preview
   ```

The NVIDIA proxy supports key rotation across multiple keys in the file. If all keys are rate-limited, requests can still fail with upstream `429`.

### Option B: vLLM (local models)

```bash
uv run python -m capx.serving.vllm_server --model Qwen/Qwen2.5-Coder-7B-Instruct --port 8080 --tensor-parallel-size 4
```

For Molmo2-backed pointing used by some LIBERO perception flows:

```bash
CUDA_VISIBLE_DEVICES=7 uv run --no-sync --active python -m capx.serving.vllm_server \
  --model allenai/Molmo2-8B \
  --host 127.0.0.1 \
  --port 8122 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.55 \
  --max-model-len 4096 \
  --max-num-batched-tokens 8192 \
  --trust-remote-code
```

### Option C: Custom providers

Providers live under `capx/serving/providers/` and implement a simple `generate_code` method. Extend to Gemini/Claude/Bedrock by adding new provider classes.

> **Note:** `.openrouterkey` is git-ignored. Never commit API keys to the repository.
