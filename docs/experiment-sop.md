# LIBERO Rollout Experiment SOP

Standard operating procedure for collecting LIBERO rollouts on a single
multi-GPU node, using a single model (Opus 4.8 via the local Bedrock proxy).

This document is **operational** — meant to be followed step-by-step and
amended in place as we learn things. The experiment design itself is:

> For each LIBERO task, generate rollouts at a fixed tier (S1 first, then
> S2). Stop a task as soon as we have **≥10 successful trials**. If the
> first 10 rollouts produce 0 successes, declare the task unsolvable at
> this tier and move on. Record everything either way.

## 1. Configuration we lock in

| Knob | Value | Notes |
|------|-------|-------|
| Model | `openrouter/anthropic/claude-opus-4` | maps to `bedrock/us.anthropic.claude-opus-4-8` via proxy |
| Reasoning effort | `high` | hardcoded in proxy for Anthropic models when no `reasoning_effort` is sent. Revisit only if persistent failures suggest harder thinking is needed. |
| Thinking display | `summarized` | proxy default; gives us paraphrased plaintext reasoning. Bedrock does not expose verbatim chain-of-thought for Opus 4.7+. |
| Tier | S1 (privileged), then S2 (perception) | tier per-task is recorded in the manifest |
| Trials per task | 10 minimum, more until ≥10 successes or 10 fails-in-a-row | |
| Parallelism | 10 concurrent rollouts per `launch.py` invocation | revisit upward once we measure GPU/Bedrock saturation |
| Region | `us-west-2` | |
| Output format | per-trial folders + a top-level `manifest.jsonl` | |

## 2. Pre-flight (do this once per machine)

1. **Project install** — see [`README.md`](../README.md). For LIBERO we use
   the `.venv-libero` venv (Python 3.12) per
   [`docs/libero-tasks.md`](libero-tasks.md). Bedrock deps are added with
   `uv sync --active --extra libero --extra contactgraspnet --extra bedrock`.
2. **AWS credentials.** `aws sts get-caller-identity` should succeed; if
   `AWS_PROFILE` is unset, `unset AWS_PROFILE` and rely on instance role.
3. **Bedrock proxy.** Pick a free port (8112 if 8110 is taken — see
   [CLAUDE.md](../CLAUDE.md)). Start in a screen/tmux session:
   ```bash
   uv run --no-sync --active capx/serving/bedrock_server.py \
       --port 8112 --region us-west-2
   ```
4. **Route the client at the proxy** — must export this env var, since
   `--server-url` is ignored for `openrouter/` models:
   ```bash
   export OPENROUTER_SERVER_URL=http://127.0.0.1:8112/chat/completions
   ```
5. **Perception servers (S2 only).** Start once and share across all runs:
   ```bash
   uv run --no-sync --active capx/serving/launch_servers.py --profile default
   # SAM3 (8114) + GraspNet (8115) + PyRoKi (8116) on auto-allocated GPUs
   ```
   For S1 only PyRoKi is needed — `_start_api_servers` will spin it up
   per-run from the YAML if it isn't already there.
6. **(Optional) Molmo on 8122** — only needed if S2 runs hit the SAM3
   text-prompt fallback path. See [CLAUDE.md](../CLAUDE.md). Skip until we
   see SAM3 fall through.

Sanity check before starting any real run:
```bash
curl -s http://127.0.0.1:8112/health        # {"status":"ok"}
curl -s http://127.0.0.1:8114/              # SAM3
curl -s http://127.0.0.1:8115/              # GraspNet (S2)
curl -s http://127.0.0.1:8116/              # PyRoKi
```

## 3. Output layout (the bookkeeping)

Everything for one experiment session lives under a single top-level dir:

```
outputs/libero-opus4_8-<YYYYMMDD>-<HHMM>/
├── manifest.jsonl          # one line per (task, tier) attempt — APPEND ONLY
├── runs.log                # combined stdout/stderr from all launch.py runs
├── README.md               # who/why/when, any deviations from this SOP
└── <suite>__<task_id>__<tier>/
    └── openrouter_anthropic_claude-opus-4/
        ├── initial_prompt.txt
        ├── summaries.txt
        └── trial_NN_sandboxrc_R_reward_RR_taskcompleted_T/
            ├── code.py
            ├── all_responses.json   # includes reasoning summaries
            ├── summary.txt
            ├── prompts_and_responses/
            └── *.mp4                # if record_video
```

### `manifest.jsonl` schema

One JSON object per line. Every `launch.py` invocation gets its own line,
and the post-processing step appends a **roll-up line** when a task reaches
its stop condition. Pick fields once and never rename them.

Per-run line:
```json
{
  "type": "run",
  "ts": "2026-06-12T17:42:11Z",
  "suite": "libero_spatial",
  "task_id": 0,
  "task_language": "Pick up the black bowl ...",
  "tier": "S1",
  "config_path": "env_configs/libero/franka_libero_spatial_0_privileged.yaml",
  "model": "openrouter/anthropic/claude-opus-4",
  "reasoning_effort": "high",
  "trials_requested": 10,
  "num_workers": 10,
  "output_dir": "outputs/.../libero_spatial__0__S1/openrouter_anthropic_claude-opus-4",
  "git_commit": "<sha>",
  "git_dirty": false,
  "trials_completed": 10,
  "successes": 7,
  "failures": 3,
  "trial_ids_success": [1,3,4,5,7,8,10],
  "trial_ids_failure": [2,6,9],
  "elapsed_s": 412.3
}
```

Per-task roll-up line (added when a task stops):
```json
{
  "type": "task_summary",
  "ts": "2026-06-12T18:09:55Z",
  "suite": "libero_spatial",
  "task_id": 0,
  "tier": "S1",
  "stop_reason": "ten_successes",   // or "unsolvable_in_first_10"
  "total_trials": 14,
  "total_successes": 10,
  "total_failures": 4,
  "runs": ["<run output_dir>", "..."]
}
```

Why JSONL: append-only, survives crashes, trivial to parse with `jq`.

## 4. Run loop

For one (suite, task_id, tier):

1. **Pick the YAML.** If a config for that exact (suite, task, tier) doesn't
   exist, create one by copying the closest sibling and editing
   `low_level.suite_name`, `low_level.task_id`, `apis`, `privileged`. Name
   it `franka_libero_<suite>_<task_id>[_privileged].yaml`.
2. **Launch a 10-trial batch:**
   ```bash
   uv run --no-sync --active capx/envs/launch.py \
       --config-path env_configs/libero/franka_libero_<suite>_<task>__<tier>.yaml \
       --total-trials 10 --num-workers 10 \
       --output-dir outputs/<session>/<suite>__<task>__<tier>
   ```
3. **Parse the summary.** Each trial folder name encodes
   `taskcompleted_{0|1}` — count successes by globbing
   `trial_*_taskcompleted_1`. Append a `type:"run"` manifest line.
4. **Decide the next move:**
   - **Successes ≥ 10** → write the `task_summary` line with
     `stop_reason: "ten_successes"`. Done.
   - **0 successes in this batch AND it was the first batch** →
     write `task_summary` with `stop_reason: "unsolvable_in_first_10"`.
     Done.
   - **Otherwise** (1–9 successes) → re-launch with
     `--total-trials <N>` chosen so cumulative successes hit 10. Use a
     fresh `--output-dir` suffixed with `_resume_2`, `_resume_3`, … so we
     never overwrite earlier trial folders. Append another `type:"run"`
     line.

A small wrapper script makes step 2-4 deterministic and resumable; see
§7 for the sketch. Don't write it yet — first manually run a couple of
tasks to confirm the bookkeeping schema holds up.

## 5. Concurrency budget on this box

- **Inside one `launch.py`:** `--num-workers 10` shares one set of
  perception servers + one Bedrock proxy across 10 worker processes.
  This is the default unit of parallelism we orchestrate at.
- **Across `launch.py` invocations:** running multiple at once is
  possible (`_start_api_servers` skips ports already in use), but **don't
  do it for the first session.** Bedrock per-account TPS will be the
  first bottleneck and SAM3 has a single-process FIFO. Measure with one
  task at a time before scaling out.
- **GPU note (TODO):** by default MuJoCo offscreen rendering lands on
  GPU 0 for every worker — see CLAUDE.md commentary. Acceptable on B200s
  but a real bottleneck on smaller cards. Revisit if we add a second
  parallel `launch.py`.

## 6. What's captured per trial (verified)

Every trial folder contains (`capx/utils/launch_utils.py:376` is the
writer; `capx/envs/trial.py:753-862` is the source of `all_responses`):

- `code.py` — the final code that ran in the env.
- `raw_response.sh` — raw model text for the initial turn.
- `all_responses.json` — list of turns, each carrying:
  - `decision`: `initial` / `regenerate` / `finish`
  - `code_blocks`, `block_idx`
  - `initial_prompt` or `multi_turn_prompt` (multi-turn only when
    `save_multiturn_prompts: true` in config)
  - **`reasoning`** — Bedrock's adaptive-thinking summary string. Note
    this is paraphrased, not verbatim — a hard Bedrock limitation for
    Opus 4.7+. May be empty/short on trivial turns.
- `summary.txt` — pretty-printed turn log with stdout/stderr.
- `prompts_and_responses/` — flattened initial prompt + per-turn prompts.
- Videos (`combined.mp4`, `turn_NN.mp4`) when `record_video: true`.

Top-level files: `initial_prompt.txt` (the formatted system + user
prompt), `summaries.txt` (per-trial result lines), `aaa_done_flag` (touch
file written when the run finishes cleanly).

## 7. Driver script (sketch — not yet written)

A future `scripts/run_libero_grid.py` would:

1. Read a TOML/YAML worklist of `(suite, task_id, tier)` triples.
2. For each, ensure a YAML config exists (auto-generate if missing).
3. Loop the §4 logic, appending to `manifest.jsonl` and aborting cleanly
   on Ctrl-C with the manifest still consistent.
4. Resume on restart by reading `manifest.jsonl` and skipping any
   (suite, task, tier) that already has a `task_summary` line.

Hold off on writing this until we run the first 3-5 tasks by hand and
confirm the manifest schema covers everything we end up wanting to query.

## 8. Known gotchas

- **`OPENROUTER_SERVER_URL` env var is mandatory.** If unset, the client
  silently routes to `http://localhost:8110` which on this box is a
  long-running OpenRouter proxy from a different workspace.
- **Reasoning is summarized, not verbatim.** Bedrock encrypts Opus 4.7+
  thinking by default; we request `display:"summarized"` to get any
  plaintext at all. Don't claim "we have full chain-of-thought" in
  downstream analyses.
- **`temperature` is 1.0 by default** in `LaunchArgs`, but the proxy
  strips it for Opus 4.x (Bedrock rejects it). No-op, but worth noting in
  the manifest that the value is not actually applied.
- **LIBERO needs `.venv-libero`.** Do not try to run LIBERO from the
  main robosuite venv — the robosuite forks conflict.
- **Each `launch.py` insertion of model name** into `output_dir`
  (`runner.py:101`) means our `--output-dir` gets a
  `/openrouter_anthropic_claude-opus-4/` segment appended. Manifest
  paths must reflect this.
