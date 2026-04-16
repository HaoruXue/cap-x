from __future__ import annotations

from collections.abc import Sequence
from threading import Lock
from typing import Any

import msgpack_numpy
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation as SciRotation
import websockets.sync.client


DEFAULT_OPENPI_HOST = "127.0.0.1"
DEFAULT_OPENPI_PORT = 8000


def _convert_to_uint8(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if np.issubdtype(array.dtype, np.floating):
        array = np.clip(array * 255.0, 0.0, 255.0).astype(np.uint8)
    return array


def _resize_with_pad(image: np.ndarray, height: int, width: int) -> np.ndarray:
    pil_image = Image.fromarray(_convert_to_uint8(image))
    cur_width, cur_height = pil_image.size
    if (cur_height, cur_width) == (height, width):
        return np.asarray(pil_image)

    ratio = max(cur_width / width, cur_height / height)
    resized_width = int(cur_width / ratio)
    resized_height = int(cur_height / ratio)
    resized = pil_image.resize((resized_width, resized_height), resample=Image.BILINEAR)

    canvas = Image.new(resized.mode, (width, height), 0)
    pad_x = max(0, (width - resized_width) // 2)
    pad_y = max(0, (height - resized_height) // 2)
    canvas.paste(resized, (pad_x, pad_y))
    return np.asarray(canvas)


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
    base_rgb = np.asarray(obs["agentview"]["images"]["rgb"])[:, ::-1]
    wrist_rgb = np.asarray(obs["robot0_eye_in_hand"]["images"]["rgb"])[:, ::-1]
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
        if uri is not None:
            self._uri = uri
        elif host.startswith("ws://") or host.startswith("wss://"):
            self._uri = host if port is None else f"{host}:{port}"
        else:
            self._uri = f"ws://{host}:{port}"
        self._api_key = api_key
        self._packer = msgpack_numpy.Packer()
        self._lock = Lock()
        self._ws = None
        self._metadata: dict[str, Any] | None = None

    def _connect(self) -> None:
        headers = {"Authorization": f"Api-Key {self._api_key}"} if self._api_key else None
        self._ws = websockets.sync.client.connect(
            self._uri,
            compression=None,
            max_size=None,
            additional_headers=headers,
        )
        metadata = self._ws.recv()
        if isinstance(metadata, str):
            raise RuntimeError(f"OpenPI server returned a string during handshake: {metadata}")
        self._metadata = msgpack_numpy.unpackb(metadata)

    @property
    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            self._connect()
        return self._metadata or {}

    def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._ws is None:
                self._connect()
            try:
                assert self._ws is not None
                self._ws.send(self._packer.pack(payload))
                response = self._ws.recv()
            except Exception:
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                self._ws = None
                self._metadata = None
                raise

        if isinstance(response, str):
            raise RuntimeError(f"OpenPI server returned an error:\n{response}")
        data = msgpack_numpy.unpackb(response)
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict response from OpenPI server, got {type(data)!r}")
        return data

    def close(self) -> None:
        with self._lock:
            if self._ws is not None:
                self._ws.close()
                self._ws = None
                self._metadata = None
