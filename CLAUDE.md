# CLAUDE.md

Notes for Claude Code working in this repo. Keep this file focused and current — additions only when something is non-obvious from reading the code.

## CaP-Bench tier ↔ config mapping

The paper (Section 3, Table 1) defines 8 evaluation tiers but the repo does
not label its YAML configs with the tier names. Mapping below, derived from
matching paper definitions against `apis:` / `privileged:` / `use_*` flags.
Each of the 7 core tasks (`cube_lifting`, `cube_stack`, `cube_restack`,
`spill_wipe`, `nut_assembly`, `two_arm_lift`, `two_arm_handover`) ships the
same 7 base variants — examples below use `cube_stack`.

| Tier | Paper definition | Config (relative to `env_configs/<task>/`) | Distinguishing fields |
|------|------------------|--------------------------------------------|------------------------|
| **S1** | Single-turn · high-level · **privileged** (GT poses + masks) | `franka_robosuite_cube_stack_privileged.yaml` | `privileged: true`, `apis: [FrankaControlPrivilegedApi]`, no SAM3/GraspNet |
| **S2** | Single-turn · high-level · noisy perception (default for prior work) | `franka_robosuite_cube_stack.yaml` | `privileged: false`, `apis: [FrankaControlApi]` |
| **S3** | Single-turn · low-level primitives **with** in-context examples | `franka_robosuite_cube_stack_reduced_api.yaml` | `apis: [FrankaControlApiReduced]` (docstrings include `Example:` blocks) |
| **S4** | Single-turn · low-level · examples removed | `franka_robosuite_cube_stack_reduced_api_exampleless.yaml` | `apis: [FrankaControlApiReducedExampleless]` (strips `Example:` from `combined_doc()`) |
| **M1** | Multi-turn · text-only feedback (stdout/stderr) | `franka_robosuite_cube_stack_multiturn.yaml` | high-level API, neither `use_visual_feedback` nor `use_img_differencing` |
| **M2** | Multi-turn · raw RGB piped back each turn | `franka_robosuite_cube_stack_multiturn_vf.yaml` | `use_visual_feedback: true` |
| **M3** | Multi-turn · Visual Differencing Module (VLM → text) | `franka_robosuite_cube_stack_multiturn_vdm.yaml` | `use_img_differencing: true`, high-level API |
| **M4** | Multi-turn · low-level (S3 APIs) + VDM | `franka_robosuite_cube_stack_multiturn_vdm_reduced_api.yaml` | `use_img_differencing: true`, `apis: [FrankaControlApiReduced]` |

Note: `*_multiturn_vdm_reduced_api_skill_lib.yaml` is **not** a paper tier — it
swaps in `FrankaControlApiReducedSkillLibrary` and is part of CaP-Agent0's
auto-synthesized skill-library variant on top of M4.

`two_arm_*` configs drop the `franka_robosuite_` prefix and shorten
`reduced_api` → `reduced` (e.g. `two_arm_handover_reduced_exampleless.yaml`),
but the tier mapping is the same.

## API class quick reference

| Class | Tier | What it exposes |
|-------|------|-----------------|
| `FrankaControlPrivilegedApi` (`capx/integrations/franka/control_privileged.py`) | S1 | High-level + ground-truth state, no perception modules |
| `FrankaControlApi` (`capx/integrations/franka/control.py`) | S2, M1, M2, M3 | High-level: `get_object_pose`, `sample_grasp_pose`, `goto_pose`, `home_pose`, `open_gripper`, `close_gripper` |
| `FrankaControlApiReduced` (`capx/integrations/franka/control_reduced.py`) | S3, M4 | Low-level: `segment_sam3_text_prompt`, `plan_grasp`, `solve_ik`, `move_to_joints`, `traj_plan`, etc. |
| `FrankaControlApiReducedExampleless` (`capx/integrations/franka/control_reduced_exampleless.py`) | S4 | Same surface as Reduced; strips `Example:` blocks from docstrings |
| `FrankaControlApiReducedSkillLibrary` (`capx/integrations/franka/control_reduced_skill_library.py`) | (CaP-Agent0, not a tier) | Reduced + auto-synthesized skill library |

## Bedrock proxy

`capx/serving/bedrock_server.py` is the OpenAI-compat shim for Amazon
Bedrock — drop-in replacement for `openrouter_server.py`. Install deps with
`uv sync --extra bedrock`. AWS credentials come from `AWS_PROFILE` /
`~/.aws`. Default region is `us-west-2`.

```bash
uv run --no-sync --active capx/serving/bedrock_server.py --port 8110 --region us-west-2
```

The default model in `LaunchArgs` (`capx/envs/launch.py:52`) is
`openrouter/anthropic/claude-opus-4`, which the proxy maps to
`bedrock/us.anthropic.claude-opus-4-8`. Opus 4.x on Bedrock rejects
`temperature` and `top_p`; the proxy strips them automatically for any
resolved model containing `claude-opus-4`.

If port 8110 is already taken (e.g. by another long-running OpenRouter
proxy), run the Bedrock proxy on a different port and pass it via
`--server-url http://127.0.0.1:<port>/chat/completions` to `launch.py`.

## Perception servers for LIBERO tiers

`FrankaLiberoApi` (S2/M*) eagerly initializes clients for SAM3, GraspNet,
PyRoKi, **and Molmo**. The first three are declared as `api_servers:` in
the LIBERO YAMLs and auto-launch via `_start_api_servers`. Molmo is the
odd one out:

- **Not required** for the published LIBERO / CaP-Agent0 results — per
  maintainer in [issue #17](https://github.com/capgym/cap-x/issues/17).
  But it is recommended and used by the LIBERO `get_object_pose` fallback
  when SAM3 text-prompt finds nothing (`capx/integrations/franka/libero.py:410`).
- **No launcher in `capx/serving/`** and not listed in
  `SERVER_REGISTRY`. `init_molmo()` does not probe at startup; failures
  surface only on the first call to `point_prompt_molmo` (or the SAM3
  fallback path).
- **Recommended bringup** (vLLM, port 8122, separate venv because the
  `molmo` extra conflicts with `robosuite`/`verl`):

  ```bash
  uv venv .venv-molmo --python 3.10
  source .venv-molmo/bin/activate
  uv sync --active --extra molmo
  vllm serve allenai/Molmo2-8B \
      --trust-remote-code --port 8122 \
      --max-num-batched-tokens 36864 --dtype bfloat16 \
      --limit-mm-per-prompt.image 2
  ```

Tier → required servers (LIBERO):
- **S1** (`FrankaLiberoPrivilegedApi`): PyRoKi only
- **S2** (`FrankaLiberoApi`): SAM3 + GraspNet + PyRoKi (+ Molmo if you
  want the get_object_pose / point_prompt_molmo path)

## Smoke test

After install + proxy is up, the cheapest end-to-end check is the quick
smoke variant of the regression suite:

```bash
./scripts/regression_test.sh quick    # 10 trials, ~30s
```

Or a tighter manual run:

```bash
uv run --no-sync --active capx/envs/launch.py \
  --config-path env_configs/cube_stack/franka_robosuite_cube_stack.yaml \
  --server-url http://127.0.0.1:8110/chat/completions \
  --total-trials 4 --num-workers 2
```

Pass threshold for `quick` is ≥2/10 completed (see
`scripts/regression_test.sh:30`).
