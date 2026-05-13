from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
from typing import Any

import numpy as np
import tyro
from libero import benchmark
from libero.envs import OffScreenRenderEnv
from libero.utils import get_libero_path

from capx.envs.scripts.run_openpi_libero_eval import (
    LIBERO_DUMMY_ACTION,
    LIBERO_ENV_RESOLUTION,
    _get_max_steps,
)
from capx.envs.simulators.libero import FrankaLiberoEnv
from capx.utils.openpi import OpenPIWebsocketClient, build_openpi_libero_input


@dataclasses.dataclass
class Args:
    host: str = "127.0.0.1"
    port: int = 8000
    resize_size: int = 224
    replan_steps: int = 5
    seed: int = 7
    num_steps_wait: int = 10
    compare_steps: int = 40
    trials_per_task: int = 3
    cases: list[str] = dataclasses.field(
        default_factory=lambda: [
            "libero_spatial:0",
            "libero_object:0",
            "libero_goal:0",
        ]
    )
    output_json: str = "outputs/openpi_native_alignment/alignment_report.json"


def _make_direct_env(task: Any, seed: int) -> OffScreenRenderEnv:
    task_bddl_file = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    env_args = {
        "bddl_file_name": task_bddl_file,
        "camera_heights": LIBERO_ENV_RESOLUTION,
        "camera_widths": LIBERO_ENV_RESOLUTION,
    }
    env = OffScreenRenderEnv(**env_args)
    env.seed(seed)
    return env


def _parse_case(case: str) -> tuple[str, int]:
    suite, task_id = case.split(":")
    return suite, int(task_id)


def _quat_distance(q1: np.ndarray, q2: np.ndarray) -> float:
    q1 = np.asarray(q1, dtype=np.float64).reshape(4)
    q2 = np.asarray(q2, dtype=np.float64).reshape(4)
    q1 = q1 / max(np.linalg.norm(q1), 1e-8)
    q2 = q2 / max(np.linalg.norm(q2), 1e-8)
    dot = float(np.clip(abs(np.dot(q1, q2)), -1.0, 1.0))
    return float(2.0 * np.arccos(dot))


def _rgb_mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))


def _query_openpi_actions(
    client: OpenPIWebsocketClient,
    raw_obs: dict[str, Any],
    prompt: str,
    *,
    resize_size: int,
) -> np.ndarray:
    openpi_input = build_openpi_libero_input(
        {
            "agentview": {"images": {"rgb": raw_obs["agentview_image"][::-1]}},
            "robot0_eye_in_hand": {"images": {"rgb": raw_obs["robot0_eye_in_hand_image"][::-1]}},
            "robot_cartesian_pos": np.zeros(8, dtype=np.float64),
        },
        prompt=prompt,
        raw_libero_obs=raw_obs,
        resize_size=resize_size,
    )
    return np.asarray(client.infer(openpi_input)["actions"], dtype=np.float64)


def _compare_case(
    *,
    client: OpenPIWebsocketClient,
    suite_name: str,
    task_id: int,
    trial_idx: int,
    seed: int,
    num_steps_wait: int,
    replan_steps: int,
    resize_size: int,
    compare_steps: int,
) -> dict[str, Any]:
    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[suite_name]()
    task = task_suite.get_task(task_id)
    initial_states = task_suite.get_task_init_states(task_id)

    direct_env = _make_direct_env(task, seed)
    direct_env.reset()
    direct_obs = direct_env.set_init_state(initial_states[trial_idx])
    for _ in range(num_steps_wait):
        direct_obs, _, _, _ = direct_env.step(LIBERO_DUMMY_ACTION)

    capx_env = FrankaLiberoEnv(
        suite_name=suite_name,
        task_id=task_id,
        privileged=False,
        max_steps=1000,
        seed=seed,
        control_freq=20,
    )
    capx_env.reset(seed=trial_idx + 1)
    capx_raw_obs = capx_env.get_openpi_native_raw_obs(sync_from_primary=False)

    per_step: list[dict[str, Any]] = []
    action_plan: list[np.ndarray] = []
    step_idx = 0
    direct_done = False
    capx_done = False

    while step_idx < compare_steps:
        if not action_plan:
            chunk = _query_openpi_actions(
                client,
                direct_obs,
                task.language,
                resize_size=resize_size,
            )
            if chunk.ndim != 2 or chunk.shape[1] < 7:
                raise ValueError(f"Unexpected OpenPI action chunk shape: {chunk.shape}")
            action_plan = [np.asarray(a[:7], dtype=np.float64) for a in chunk[:replan_steps]]

        action = action_plan.pop(0)
        direct_obs, direct_reward, direct_done, _ = direct_env.step(action.tolist())
        _, capx_reward, capx_done, _ = capx_env.execute_openpi_native_action(
            action,
            sync_from_primary=False,
        )
        capx_raw_obs = capx_env.get_openpi_native_raw_obs(sync_from_primary=False)

        direct_eef_pos = np.asarray(direct_obs["robot0_eef_pos"], dtype=np.float64)
        capx_eef_pos = np.asarray(capx_raw_obs["robot0_eef_pos"], dtype=np.float64)
        direct_eef_quat = np.asarray(direct_obs["robot0_eef_quat"], dtype=np.float64)
        capx_eef_quat = np.asarray(capx_raw_obs["robot0_eef_quat"], dtype=np.float64)
        direct_gripper = np.asarray(direct_obs["robot0_gripper_qpos"], dtype=np.float64)
        capx_gripper = np.asarray(capx_raw_obs["robot0_gripper_qpos"], dtype=np.float64)

        per_step.append(
            {
                "step": step_idx,
                "eef_pos_l2": float(np.linalg.norm(direct_eef_pos - capx_eef_pos)),
                "eef_quat_angle": _quat_distance(direct_eef_quat, capx_eef_quat),
                "gripper_l2": float(np.linalg.norm(direct_gripper - capx_gripper)),
                "agentview_rgb_mae": _rgb_mae(
                    np.asarray(direct_obs["agentview_image"]),
                    np.asarray(capx_raw_obs["agentview_image"]),
                ),
                "wrist_rgb_mae": _rgb_mae(
                    np.asarray(direct_obs["robot0_eye_in_hand_image"]),
                    np.asarray(capx_raw_obs["robot0_eye_in_hand_image"]),
                ),
                "direct_reward": float(direct_reward),
                "capx_reward": float(capx_reward),
                "direct_done": bool(direct_done),
                "capx_done": bool(capx_done),
            }
        )

        step_idx += 1
        if direct_done or capx_done:
            break

    return {
        "suite_name": suite_name,
        "task_id": task_id,
        "trial_idx": trial_idx,
        "prompt": task.language,
        "steps_executed": len(per_step),
        "direct_done": bool(direct_done),
        "capx_done": bool(capx_done),
        "done_match": bool(direct_done == capx_done),
        "max_eef_pos_l2": max((s["eef_pos_l2"] for s in per_step), default=0.0),
        "max_eef_quat_angle": max((s["eef_quat_angle"] for s in per_step), default=0.0),
        "max_gripper_l2": max((s["gripper_l2"] for s in per_step), default=0.0),
        "max_agentview_rgb_mae": max((s["agentview_rgb_mae"] for s in per_step), default=0.0),
        "max_wrist_rgb_mae": max((s["wrist_rgb_mae"] for s in per_step), default=0.0),
        "mean_eef_pos_l2": float(np.mean([s["eef_pos_l2"] for s in per_step])) if per_step else 0.0,
        "mean_agentview_rgb_mae": float(np.mean([s["agentview_rgb_mae"] for s in per_step])) if per_step else 0.0,
        "per_step": per_step,
    }


def run(args: Args) -> dict[str, Any]:
    output_path = pathlib.Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = OpenPIWebsocketClient(host=args.host, port=args.port)
    results: list[dict[str, Any]] = []

    for case in args.cases:
        suite_name, task_id = _parse_case(case)
        benchmark_dict = benchmark.get_benchmark_dict()
        task_suite = benchmark_dict[suite_name]()
        available_trials = len(task_suite.get_task_init_states(task_id))
        num_trials = min(args.trials_per_task, available_trials)
        for trial_idx in range(num_trials):
            logging.info("Comparing %s task=%d trial=%d", suite_name, task_id, trial_idx)
            result = _compare_case(
                client=client,
                suite_name=suite_name,
                task_id=task_id,
                trial_idx=trial_idx,
                seed=args.seed,
                num_steps_wait=args.num_steps_wait,
                replan_steps=args.replan_steps,
                resize_size=args.resize_size,
                compare_steps=min(args.compare_steps, _get_max_steps(suite_name)),
            )
            results.append(result)

    summary = {
        "cases": args.cases,
        "trials_per_task": args.trials_per_task,
        "compare_steps": args.compare_steps,
        "results": results,
        "overall": {
            "num_rollouts": len(results),
            "done_match_rate": (
                float(np.mean([1.0 if r["done_match"] else 0.0 for r in results])) if results else 0.0
            ),
            "direct_success_rate": (
                float(np.mean([1.0 if r["direct_done"] else 0.0 for r in results])) if results else 0.0
            ),
            "capx_success_rate": (
                float(np.mean([1.0 if r["capx_done"] else 0.0 for r in results])) if results else 0.0
            ),
            "max_eef_pos_l2": max((r["max_eef_pos_l2"] for r in results), default=0.0),
            "max_eef_quat_angle": max((r["max_eef_quat_angle"] for r in results), default=0.0),
            "max_agentview_rgb_mae": max((r["max_agentview_rgb_mae"] for r in results), default=0.0),
            "max_wrist_rgb_mae": max((r["max_wrist_rgb_mae"] for r in results), default=0.0),
        },
    }

    output_path.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = run(tyro.cli(Args))
    print(json.dumps(summary["overall"], indent=2))
