# LIBERO Successful-Trajectory Collection

Inventory of every successful rollout (`taskcompleted_1`) collected across the
Gemini 3.1 Pro and Opus 4.8 S2 LIBERO campaigns, the 7-task comparison run, and
the trajectory-collection top-ups (2026-06-12 through 2026-06-16).

**The trajectory data lives under `outputs/` (gitignored — videos + per-turn
JSON, several GB). This file is the tracked index.** Each trajectory directory
contains `code.py`, `all_responses.json` (campaign/topup runs include Gemini/Opus
reasoning summaries), `summary.txt`, and `video_combined.mp4`.

## Totals

- **257 raw successful trajectories** (Gemini 105 + Opus 149 + GPT-5.5 3)
- **30 distinct environments** with at least one success (of 130 S2 tasks)
- **204 trajectories** when deduped to best-model-per-environment
- **9 environments reached >=10** successes; 21 are partial (1-9)
- (1 additional success dir(s) with a malformed/empty task label excluded: `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/____S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`)
- GPT-5.5's 3 trajectories are leftovers from a prior 90_19 Bedrock comparison probe.

> Note: raw counts include multiple sources for the same env (e.g. the 7-task
> comparison run and the full campaign both ran goal_1, 90_19, etc.), so the per-env
> tables below sum every successful rollout for that env across all sessions.

## By suite

| Suite | Envs | Gemini | Opus | GPT-5.5 | Union |
|---|--:|--:|--:|--:|--:|
| libero_object | 1 | 9 | 0 | 0 | 9 |
| libero_spatial | 3 | 7 | 29 | 0 | 29 |
| libero_goal | 5 | 29 | 41 | 0 | 49 |
| libero_10 | 1 | 0 | 12 | 0 | 12 |
| libero_90 | 20 | 60 | 67 | 3 | 105 |
| **Total** | **30** | **105** | **149** | **3** | **204** |

## Per-environment counts

| Env | Suite | Gemini | Opus | GPT-5.5 | Union | >=10? |
|---|---|--:|--:|--:|--:|:--:|
| 10_2 | libero_10 | 0 | 12 | 0 | 12 | yes |
| 90_14 | libero_90 | 5 | 0 | 0 | 5 |  |
| 90_15 | libero_90 | 0 | 4 | 0 | 4 |  |
| 90_18 | libero_90 | 0 | 1 | 0 | 1 |  |
| 90_19 | libero_90 | 2 | 13 | 3 | 13 | yes |
| 90_20 | libero_90 | 3 | 15 | 0 | 15 | yes |
| 90_24 | libero_90 | 1 | 0 | 0 | 1 |  |
| 90_26 | libero_90 | 2 | 0 | 0 | 2 |  |
| 90_28 | libero_90 | 4 | 0 | 0 | 4 |  |
| 90_29 | libero_90 | 2 | 1 | 0 | 2 |  |
| 90_33 | libero_90 | 11 | 1 | 0 | 11 | yes |
| 90_38 | libero_90 | 3 | 4 | 0 | 4 |  |
| 90_44 | libero_90 | 10 | 18 | 0 | 18 | yes |
| 90_50 | libero_90 | 1 | 1 | 0 | 1 |  |
| 90_53 | libero_90 | 1 | 0 | 0 | 1 |  |
| 90_56 | libero_90 | 2 | 0 | 0 | 2 |  |
| 90_60 | libero_90 | 5 | 1 | 0 | 5 |  |
| 90_65 | libero_90 | 0 | 2 | 0 | 2 |  |
| 90_68 | libero_90 | 8 | 0 | 0 | 8 |  |
| 90_74 | libero_90 | 0 | 5 | 0 | 5 |  |
| 90_76 | libero_90 | 0 | 1 | 0 | 1 |  |
| goal_1 | libero_goal | 16 | 11 | 0 | 16 | yes |
| goal_2 | libero_goal | 0 | 5 | 0 | 5 |  |
| goal_4 | libero_goal | 13 | 10 | 0 | 13 | yes |
| goal_7 | libero_goal | 0 | 10 | 0 | 10 | yes |
| goal_8 | libero_goal | 0 | 5 | 0 | 5 |  |
| object_3 | libero_object | 9 | 0 | 0 | 9 |  |
| spatial_0 | libero_spatial | 7 | 21 | 0 | 21 | yes |
| spatial_1 | libero_spatial | 0 | 3 | 0 | 3 |  |
| spatial_8 | libero_spatial | 0 | 5 | 0 | 5 |  |

## Trajectory paths

Every successful trajectory directory, grouped by environment and model
(paths relative to repo root, under gitignored `outputs/`).

### 10_2 (libero_10)
- **opus-4.8** (12):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_2/trial_26_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_2/trial_27_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_20_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_27_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_31_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_34_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_10__2__S2_resume_3/trial_36_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_14 (libero_90)
- **gemini-3.1-pro** (5):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_14__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/90_14__topup_1/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/90_14__topup_3/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/90_14__topup_4/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/90_14__topup_5/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_15 (libero_90)
- **opus-4.8** (4):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/90_15_S2__topup_4/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/90_15_S2__topup_5/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/90_15_S2__topup_5/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__15__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_18 (libero_90)
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__18__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_19 (libero_90)
- **gemini-3.1-pro** (2):
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_19__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_19__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (13):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_13_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_15_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__19__S2_resume_2_n20/trial_17_sandboxrc_0_reward_1.000_taskcompleted_1`
- **gpt-5.5** (3):
  - `outputs/libero-opus4_8-20260612-1810/openai_gpt-5.5/libero_90__19__S2_gpt55/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openai_gpt-5.5/libero_90__19__S2_gpt55_medium/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openai_gpt-5.5/libero_90__19__S2_gpt55_medium/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_20 (libero_90)
- **gemini-3.1-pro** (3):
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_20__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_20__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_20__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (15):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_13_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_18_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_20_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_22_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__20__S2_resume_2_n30/trial_30_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_24 (libero_90)
- **gemini-3.1-pro** (1):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_24__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_26 (libero_90)
- **gemini-3.1-pro** (2):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_26__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_26__S2_resume_2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_28 (libero_90)
- **gemini-3.1-pro** (4):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_28__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_28__S2_resume_2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_28__S2_resume_3/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_28__S2_resume_5/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_29 (libero_90)
- **gemini-3.1-pro** (2):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_29__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_29__S2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__29__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_33 (libero_90)
- **gemini-3.1-pro** (11):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_3/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_3/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_3/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_4/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_5/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_33__S2_resume_5/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__33__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_38 (libero_90)
- **gemini-3.1-pro** (3):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_38__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_38__S2_resume_3/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_38__S2_resume_4/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (4):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__38__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__38__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__38__S2_resume_2_n50/trial_25_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__38__S2_resume_2_n50/trial_39_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_44 (libero_90)
- **gemini-3.1-pro** (10):
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/90_44__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2_resume_2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2_resume_3/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2_resume_3/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2_resume_4/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_44__S2_resume_4/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (18):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_20_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_21_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_22_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_25_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_26_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_30_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_32_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__44__S2_resume_2_n40/trial_40_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_50 (libero_90)
- **gemini-3.1-pro** (1):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_50__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__50__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_53 (libero_90)
- **gemini-3.1-pro** (1):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_53__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_56 (libero_90)
- **gemini-3.1-pro** (2):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_56__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_56__S2_resume_2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_60 (libero_90)
- **gemini-3.1-pro** (5):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_60__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_60__S2_resume_2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_60__S2_resume_2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_60__S2_resume_3/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_60__S2_resume_4/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__60__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_65 (libero_90)
- **opus-4.8** (2):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__65__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__65__S2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_68 (libero_90)
- **gemini-3.1-pro** (8):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2_resume_2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2_resume_2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2_resume_2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/90_68__S2_resume_3/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-union-20260616-2237/openrouter_google_gemini-3.1-pro-preview/90_68__G_b1/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_74 (libero_90)
- **opus-4.8** (5):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__74__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__74__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__74__S2_resume_2_n50/trial_13_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__74__S2_resume_2_n50/trial_30_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-union-20260616-2237/openrouter_anthropic_claude-opus-4/90_74__O_b1/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`

### 90_76 (libero_90)
- **opus-4.8** (1):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_90__76__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`

### goal_1 (libero_goal)
- **gemini-3.1-pro** (16):
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_3/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_3/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_1__S2_resume_5/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (11):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2_resume_2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2_resume_2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2_resume_2/trial_15_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2_resume_3/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__1__S2_resume_3/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`

### goal_2 (libero_goal)
- **opus-4.8** (5):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_2_S2__topup_2/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_2_S2__topup_4/trial_12_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_2_S2__topup_6/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__2__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__2__S2_resume_2_n50/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`

### goal_4 (libero_goal)
- **gemini-3.1-pro** (13):
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_4__S2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_4__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-20260615-2220/openrouter_google_gemini-3.1-pro-preview/goal_4__S2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2_resume_3/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2_resume_3/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2_resume_4/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/goal_4__S2_resume_5/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/goal_4__topup_1/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/goal_4__topup_2/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/goal_4__topup_2/trial_12_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/goal_4__topup_3/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (10):
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_2_n50/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_2_n50/trial_17_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_2_n50/trial_47_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_2_n50/trial_48_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_3_n50/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_3_n50/trial_27_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_3_n50/trial_37_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_3_n50/trial_50_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__4__S2_resume_4_n20/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`

### goal_7 (libero_goal)
- **opus-4.8** (10):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_1/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_1/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_1/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_1/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_1/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_7_S1__topup_2/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__7__S1/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__7__S1/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__7__S1/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__7__S1_clean_v1/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`

### goal_8 (libero_goal)
- **opus-4.8** (5):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_8_S2__topup_1/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_8_S2__topup_6/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_8_S2__topup_6/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/goal_8_S2__topup_7/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_goal__8__S2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`

### object_3 (libero_object)
- **gemini-3.1-pro** (9):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/object_3__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/object_3__S2_resume_2/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/object_3__S2_resume_2/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/object_3__S2_resume_3/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/object_3__S2_resume_4/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/object_3__topup_3/trial_08_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/object_3__topup_4/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/object_3__topup_8/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/object_3__topup_8/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`

### spatial_0 (libero_spatial)
- **gemini-3.1-pro** (7):
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/spatial_0__S2/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/spatial_0__S2_resume_2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-campaign-20260615-2314/openrouter_google_gemini-3.1-pro-preview/spatial_0__S2_resume_4/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/spatial_0__topup_3/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/spatial_0__topup_5/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/spatial_0__topup_6/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-gemini31-topup-20260616-1957/openrouter_google_gemini-3.1-pro-preview/spatial_0__topup_6/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
- **opus-4.8** (21):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_3/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_4/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_4/trial_12_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_6/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_6/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_0_S2__topup_7/trial_02_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v1/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v1/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v2_n30/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v2_n30/trial_04_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v2_n30/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v2_n30/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v2_n30/trial_29_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v3_n60/trial_06_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v3_n60/trial_35_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_clean_v4_n30/trial_24_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_resume_4/trial_01_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S1_resume_4/trial_05_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S2/trial_03_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__0__S2_resume_2_n50/trial_26_sandboxrc_0_reward_1.000_taskcompleted_1`

### spatial_1 (libero_spatial)
- **opus-4.8** (3):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_1_S2__topup_2/trial_12_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_1_S2__topup_6/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__1__S2/trial_10_sandboxrc_0_reward_1.000_taskcompleted_1`

### spatial_8 (libero_spatial)
- **opus-4.8** (5):
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_8_S2__topup_2/trial_09_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_8_S2__topup_4/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus48-topup-20260616-1957/openrouter_anthropic_claude-opus-4/spatial_8_S2__topup_7/trial_11_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__8__S2/trial_07_sandboxrc_0_reward_1.000_taskcompleted_1`
  - `outputs/libero-opus4_8-20260612-1810/openrouter_anthropic_claude-opus-4/libero_spatial__8__S2_resume_2_n50/trial_36_sandboxrc_0_reward_1.000_taskcompleted_1`

