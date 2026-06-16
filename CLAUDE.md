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
proxy), run the Bedrock proxy on a different port and **export
`OPENROUTER_SERVER_URL`** so the client routes there. `--server-url` on
`launch.py` is *not* honored when the model name starts with
`openrouter/` — the client (`capx/llm/client.py:191`) hardcodes the
OpenRouter path. The env var is the override:

```bash
export OPENROUTER_SERVER_URL=http://127.0.0.1:8112/chat/completions
```

### Adaptive thinking on Opus 4.7/4.8

Opus 4.7/4.8 on Bedrock require **adaptive thinking** — the legacy
`thinking={"type":"enabled","budget_tokens":N}` form (which
`capx/llm/client.py:217` still builds for `CLAUDE_MODELS`) is rejected
with a 400. The proxy translates `reasoning_effort` (low/medium/high/
xhigh/max) into:

```python
thinking = {"type": "adaptive", "display": "summarized"}
output_config = {"effort": <effort>}   # default "high"
```

`display: "summarized"` matters: the Bedrock default is `"omitted"`,
which returns a thinking block with empty `text` and only an encrypted
`signature` — no plaintext reasoning. With `summarized`, you get a
short paraphrased chain-of-thought (~100–800 chars). The proxy then
surfaces it on the OpenAI-style response as
`choices[0].message.reasoning`, which `query_model` already reads and
trial.py persists into `all_responses.json` per turn.

**`temperature` / `top_p` / `top_k`** are deprecated on Opus 4.7+ and
return 400 if non-default. The proxy strips them.

Reference: [AWS Builder, "Claude Opus 4.7 on Amazon Bedrock — APIs,
Features, and Migration Guide"](https://builder.aws.com/content/3Cl90CMMnqzCrkk6mXcmnGo1WTG/claude-opus-47-on-amazon-bedrock-apis-features-and-migration-guide).

## OpenRouter proxy — reasoning passthrough

`openrouter_server.py` forwards the model's thinking summary. OpenRouter
returns it as a non-standard `reasoning` field on the message; the OpenAI SDK
stashes it either as an attribute or in `model_extra`, so the proxy reads both
via `_extract_reasoning()` and copies it onto the response `Message`.
`query_model` (`capx/llm/client.py:277`) reads `message.reasoning` and trial.py
persists it into `all_responses.json` per turn. Without this copy the field
arrives empty downstream even though OpenRouter sent it.

**This is a summary, not verbatim chain-of-thought.** For
`google/gemini-3.1-pro-preview` the API returns two `reasoning_details`
entries: a `reasoning.text` block (the paraphrased summary we capture,
~500–4000 chars, written as tidy bolded section headers) and a
`reasoning.encrypted` block (the actual raw thinking, encrypted by Google,
not decodable). Same limitation as Bedrock/Opus 4.7+ — don't claim full CoT in
downstream analyses.

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

## LIBERO rollout campaigns

The standing experiment plan (Opus 4.8 via Bedrock, S1 then S2, ≥10
successes per task or unsolvable verdict) lives in
[`docs/experiment-sop.md`](docs/experiment-sop.md). Read that before
starting a campaign — it covers preflight, the manifest schema, and
known gotchas (notably `OPENROUTER_SERVER_URL` and the
reasoning-is-summarized-not-verbatim caveat).

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
