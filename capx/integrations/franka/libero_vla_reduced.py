from __future__ import annotations

import logging
from typing import Any

import numpy as np

from capx.envs.base import BaseEnv
from capx.integrations.base_api import ApiBase
from capx.integrations.franka.common import (
    apply_tcp_offset,
    close_gripper as _close_gripper,
    extract_arm_joints,
    open_gripper as _open_gripper,
    solve_ik_with_convergence,
)
from capx.integrations.franka.openpi_tooling import FrankaLiberoOpenPIToolMixin
from capx.integrations.motion.pyroki import init_pyroki
from capx.utils.openpi import OpenPIWebsocketClient


logger = logging.getLogger(__name__)


class FrankaLiberoVLAApiReduced(FrankaLiberoOpenPIToolMixin, ApiBase):
    """Minimal LIBERO API that isolates OpenPI plus motion primitives."""

    _TCP_OFFSET = np.array([0.0, 0.0, -0.1], dtype=np.float64)
    _openpi_client: OpenPIWebsocketClient | None
    _openpi_client_endpoint: tuple[str, int] | None

    def __init__(self, env: BaseEnv) -> None:
        super().__init__(env)
        self.ik_solve_fn = init_pyroki()
        self.camera_name = "agentview"
        self.wrist_camera_name = "robot0_eye_in_hand"
        self.cfg: np.ndarray | None = None
        self._openpi_client = None
        self._openpi_client_endpoint = None

        try:
            self.ik_solve_fn(
                target_pose_wxyz_xyz=np.array([1, 0, 0, 0, 0.3, 0, 0.5]),
                prev_cfg=None,
            )
        except Exception:
            pass

    def functions(self) -> dict[str, Any]:
        return {
            "get_observation": self.get_observation,
            "get_openpi_server_info": self.get_openpi_server_info,
            "plan_with_openpi": self.plan_with_openpi,
            "execute_openpi_step": self.execute_openpi_step,
            "execute_openpi_plan": self.execute_openpi_plan,
            "get_openpi_action_chunk": self.get_openpi_action_chunk,
            "get_openpi_subgoal": self.get_openpi_subgoal,
            "solve_ik": self.solve_ik,
            "move_to_joints": self.move_to_joints,
            "goto_pose": self.goto_pose,
            "goto_home_joint_position": self.goto_home_joint_position,
            "open_gripper": self.open_gripper,
            "close_gripper": self.close_gripper,
        }

    def get_observation(self) -> dict[str, Any]:
        """Get the observation of the environment."""
        obs = self._env.get_observation()
        obs[self.camera_name]["images"]["depth"] = obs[self.camera_name]["images"]["depth"].squeeze(-1)
        obs[self.wrist_camera_name]["images"]["depth"] = obs[self.wrist_camera_name]["images"]["depth"].squeeze(-1)
        return obs

    def solve_ik(
        self,
        position: np.ndarray,
        quaternion_wxyz: np.ndarray,
    ) -> np.ndarray:
        """Solve inverse kinematics for the panda_hand link."""
        pos = np.asarray(position, dtype=np.float64).reshape(3)
        pos = np.clip(pos, [-0.1, -0.5, 0.005], [0.75, 0.5, 0.9])
        quat_wxyz = np.asarray(quaternion_wxyz, dtype=np.float64).reshape(4)
        offset_pos = apply_tcp_offset(pos, quat_wxyz, self._TCP_OFFSET)

        orientations = [
            ("requested", quat_wxyz),
            ("top-down", np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float64)),
            ("45-tilt", np.array([0.707, 0.707, 0.0, 0.0], dtype=np.float64)),
            ("side-approach", np.array([0.707, 0.0, 0.707, 0.0], dtype=np.float64)),
        ]

        for label, quat in orientations:
            try:
                off_pos = apply_tcp_offset(pos, quat, self._TCP_OFFSET) if label != "requested" else offset_pos
                self.cfg = solve_ik_with_convergence(self.ik_solve_fn, quat, off_pos, self.cfg)
                if label != "requested":
                    logger.info("IK solved with fallback orientation: %s", label)
                return extract_arm_joints(self.cfg)
            except Exception:
                logger.warning("IK failed with orientation '%s', trying next fallback", label)
                continue

        raise RuntimeError(f"IK failed for position {pos} with all orientation fallbacks")

    def move_to_joints(self, joints: np.ndarray) -> None:
        """Move the robot to a given joint configuration in a blocking manner."""
        joints = np.asarray(joints, dtype=np.float64).reshape(7)
        self._env.move_to_joints_blocking(joints)

    def open_gripper(self) -> None:
        """Open gripper fully."""
        _open_gripper(self._env, steps=30)

    def close_gripper(self) -> None:
        """Close gripper fully."""
        _close_gripper(self._env, steps=30)

    def goto_pose(
        self,
        position: np.ndarray,
        quaternion_wxyz: np.ndarray,
        z_approach: float = 0.0,
    ) -> None:
        """Go to pose using inverse kinematics with optional approach motion."""
        pos = np.asarray(position, dtype=np.float64).reshape(3)
        quat = np.asarray(quaternion_wxyz, dtype=np.float64).reshape(4)

        if z_approach > 0.0:
            approach_pos = pos.copy()
            approach_pos[2] += z_approach
            joints = self.solve_ik(approach_pos, quat)
            self.move_to_joints(joints)

        joints = self.solve_ik(pos, quat)
        self.move_to_joints(joints)

    def goto_home_joint_position(self) -> None:
        """Return the arm to its reset joint configuration with high manipulability."""
        home = getattr(self._env, "home_joint_position", None)
        if home is None:
            raise RuntimeError("Home joint position is unavailable in the current environment.")
        joints = np.asarray(home, dtype=np.float64).reshape(7)
        self._env.move_to_joints_blocking(joints)
