from __future__ import annotations

from collections.abc import Sequence
from threading import Lock
from typing import Any
import os
import pickle
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation as SciRotation
import websockets.sync.client

try:
    from openpi_client import msgpack_numpy as _msgpack_numpy
except ImportError:  # pragma: no cover - fallback for envs without openpi-client
    import msgpack_numpy as _msgpack_numpy


DEFAULT_OPENPI_HOST = "127.0.0.1"
DEFAULT_OPENPI_PORT = 8000


def _convert_to_uint8(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if np.issubdtype(array.dtype, np.floating):
        array = np.clip(array * 255.0, 0.0, 255.0).astype(np.uint8)
    return np.ascontiguousarray(array, dtype=np.uint8)


def _resize_with_pad(image: np.ndarray, height: int, width: int) -> np.ndarray:
    pil_image = Image.fromarray(_convert_to_uint8(image))
    cur_width, cur_height = pil_image.size
    if (cur_height, cur_width) == (height, width):
        return np.array(pil_image, copy=True)

    ratio = max(cur_width / width, cur_height / height)
    resized_width = int(cur_width / ratio)
    resized_height = int(cur_height / ratio)
    resized = pil_image.resize((resized_width, resized_height), resample=Image.BILINEAR)

    canvas = Image.new(resized.mode, (width, height), 0)
    pad_x = max(0, (width - resized_width) // 2)
    pad_y = max(0, (height - resized_height) // 2)
    canvas.paste(resized, (pad_x, pad_y))
    return np.array(canvas, copy=True)


def _quat_xyzw_to_axis_angle(quat_xyzw: np.ndarray) -> np.ndarray:
    quat_xyzw = np.asarray(quat_xyzw, dtype=np.float64).reshape(4)
    return SciRotation.from_quat(quat_xyzw).as_rotvec()


def _quat_wxyz_to_xyzw(quat_wxyz: np.ndarray) -> np.ndarray:
    quat_wxyz = np.asarray(quat_wxyz, dtype=np.float64).reshape(4)
    return np.array([quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]], dtype=np.float64)


def _quat_xyzw_to_wxyz(quat_xyzw: np.ndarray) -> np.ndarray:
    quat_xyzw = np.asarray(quat_xyzw, dtype=np.float64).reshape(4)
    return np.array([quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]], dtype=np.float64)


def build_openpi_libero_input(
    obs: dict[str, Any],
    *,
    prompt: str,
    raw_libero_obs: dict[str, Any] | None = None,
    resize_size: int = 224,
) -> dict[str, Any]:
    """Convert a CaP-X or raw LIBERO observation into the upstream OpenPI LIBERO input contract."""
    base_rgb = np.ascontiguousarray(np.asarray(obs["agentview"]["images"]["rgb"])[:, ::-1])
    wrist_rgb = np.ascontiguousarray(np.asarray(obs["robot0_eye_in_hand"]["images"]["rgb"])[:, ::-1])
    base_rgb = _resize_with_pad(base_rgb, resize_size, resize_size)
    wrist_rgb = _resize_with_pad(wrist_rgb, resize_size, resize_size)

    if raw_libero_obs is not None and all(
        key in raw_libero_obs for key in ("robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")
    ):
        eef_pos = np.asarray(raw_libero_obs["robot0_eef_pos"], dtype=np.float64).reshape(-1)
        eef_quat_xyzw = np.asarray(raw_libero_obs["robot0_eef_quat"], dtype=np.float64).reshape(4)
        gripper_qpos = np.asarray(raw_libero_obs["robot0_gripper_qpos"], dtype=np.float64).reshape(-1)
        state = np.concatenate([eef_pos, _quat_xyzw_to_axis_angle(eef_quat_xyzw), gripper_qpos])
    else:
        cart = np.asarray(obs["robot_cartesian_pos"], dtype=np.float64).reshape(-1)
        eef_pos = cart[:3]
        eef_quat_xyzw = _quat_wxyz_to_xyzw(cart[3:7])
        gripper = np.repeat(cart[7], 2)
        state = np.concatenate([eef_pos, _quat_xyzw_to_axis_angle(eef_quat_xyzw), gripper])

    return {
        "observation/image": base_rgb,
        "observation/wrist_image": wrist_rgb,
        "observation/state": state.astype(np.float32),
        "prompt": str(prompt),
    }


def apply_libero_delta_action(
    position: np.ndarray,
    quaternion_wxyz: np.ndarray,
    action: Sequence[float] | np.ndarray,
    *,
    translation_scale: float = 1.0,
    rotation_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Apply an OpenPI/LIBERO delta action to a Cartesian pose."""
    action = np.asarray(action, dtype=np.float64).reshape(-1)
    if action.shape[0] < 7:
        raise ValueError(f"Expected at least 7 action values from OpenPI, got shape {action.shape}")

    current_pos = np.asarray(position, dtype=np.float64).reshape(3)
    current_quat_xyzw = _quat_wxyz_to_xyzw(quaternion_wxyz)
    current_rot = SciRotation.from_quat(current_quat_xyzw)

    target_pos = current_pos + action[:3] * translation_scale
    delta_rot = SciRotation.from_rotvec(action[3:6] * rotation_scale)
    target_rot = delta_rot * current_rot
    target_quat_wxyz = _quat_xyzw_to_wxyz(target_rot.as_quat())
    return target_pos, target_quat_wxyz, float(action[6])


class OpenPIWebsocketClient:
    """Thin synchronous client for the upstream OpenPI websocket policy server."""

    def __init__(
        self,
        host: str = DEFAULT_OPENPI_HOST,
        port: int = DEFAULT_OPENPI_PORT,
        *,
        api_key: str | None = None,
        uri: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        if uri is not None:
            self._uri = uri
        elif host.startswith("ws://") or host.startswith("wss://"):
            self._uri = host if port is None else f"{host}:{port}"
        else:
            self._uri = f"ws://{host}:{port}"
        self._api_key = api_key
        self._packer = _msgpack_numpy.Packer()
        self._lock = Lock()
        self._ws = None
        self._metadata: dict[str, Any] | None = None
        self._prefer_helper = False

    def _connect(self) -> None:
        headers = {"Authorization": f"Api-Key {self._api_key}"} if self._api_key else None
        self._ws = websockets.sync.client.connect(
            self._uri,
            compression=None,
            max_size=None,
            additional_headers=headers,
            open_timeout=120,
            ping_interval=None,
            ping_timeout=None,
        )
        metadata = self._ws.recv()
        if isinstance(metadata, str):
            raise RuntimeError(f"OpenPI server returned a string during handshake: {metadata}")
        self._metadata = _msgpack_numpy.unpackb(metadata)

    @property
    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            self._connect()
        return self._metadata or {}

    def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._prefer_helper:
            return self._infer_via_helper_or_raise(payload, "helper preferred after prior websocket failure")

        with self._lock:
            if self._ws is None:
                self._connect()
            try:
                assert self._ws is not None
                self._ws.send(self._packer.pack(payload))
                response = self._ws.recv()
            except Exception as exc:
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                self._ws = None
                self._metadata = None
                fallback = self._infer_via_helper(payload, str(exc))
                if fallback is not None:
                    return fallback
                raise

        if isinstance(response, str):
            fallback = self._infer_via_helper(payload, response)
            if fallback is not None:
                return fallback
            raise RuntimeError(f"OpenPI server returned an error:\n{response}")
        data = _msgpack_numpy.unpackb(response)
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict response from OpenPI server, got {type(data)!r}")
        return data

    def _infer_via_helper(
        self,
        payload: dict[str, Any],
        error_text: str,
        *,
        force: bool = False,
    ) -> dict[str, Any] | None:
        helper_python = self._resolve_helper_python()
        if helper_python is None:
            return None

        helper_script = Path(__file__).with_name("openpi_client_helper.py")
        if not helper_script.exists():
            return None

        # Only use the helper on the known websocket/msgpack interoperability failure path.
        if not force and not any(
            token in error_text
            for token in (
                "_parse_image",
                "IndexError: tuple index out of range",
                "ConnectionClosedError",
                "received 1011",
                "Internal server error",
            )
        ):
            return None

        with tempfile.TemporaryDirectory(prefix="openpi_helper_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            payload_path = tmpdir_path / "payload.pkl"
            output_path = tmpdir_path / "output.pkl"
            payload_path.write_bytes(pickle.dumps(payload))

            cmd = [
                helper_python,
                str(helper_script),
                "--host",
                self._host,
                "--port",
                str(self._port),
                "--payload",
                str(payload_path),
                "--output",
                str(output_path),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            result = pickle.loads(output_path.read_bytes())
            if not isinstance(result, dict):
                raise TypeError(f"Expected dict result from OpenPI helper, got {type(result)!r}")
            self._prefer_helper = True
            return result

    def _infer_via_helper_or_raise(self, payload: dict[str, Any], error_text: str) -> dict[str, Any]:
        result = self._infer_via_helper(payload, error_text, force=True)
        if result is None:
            raise RuntimeError(f"OpenPI helper path unavailable while handling: {error_text}")
        return result

    def _resolve_helper_python(self) -> str | None:
        if helper_python := os.getenv("OPENPI_CLIENT_PYTHON"):
            return helper_python

        candidates: list[Path] = []
        if openpi_root := os.getenv("OPENPI_ROOT"):
            candidates.append(Path(openpi_root).expanduser() / ".venv" / "bin" / "python")
        candidates.append(Path("/tmp/openpi/.venv/bin/python"))

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def close(self) -> None:
        with self._lock:
            if self._ws is not None:
                self._ws.close()
                self._ws = None
                self._metadata = None
