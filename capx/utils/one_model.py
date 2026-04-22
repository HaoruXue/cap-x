"""Websocket client for the one-model PolicyServer.

The wire contract is documented in
``one_model/inference/policy_server.py`` and
``one_model/inference/libero_adapter.py``:

- Transport: WebSocket with one-model's custom `_pack_numpy`/`_unpack_numpy`
  msgpack encoding (numpy arrays get serialized as
  ``{"__ndarray__": True, "data": bytes, "dtype": str, "shape": [...]}``).
  This is NOT the ``msgpack_numpy`` default convention; do not try to
  substitute ``OpenPIWebsocketClient``.
- Handshake: server sends metadata on connect.
- Reset: client sends ``{"__reset__": True}``, server replies
  ``{"__reset_ack__": True}``.
- Inference: client sends an observation dict, server returns
  ``{"actions": (AH, AD), "server_timing": {...}}``. When the server is
  configured with ``--io-adapter libero_robosuite`` the returned actions
  are a (AH, 7) robosuite-ready chunk, byte-identical to what upstream
  OpenPI's LIBERO head emits.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

import msgpack
import numpy as np
import websockets.sync.client


DEFAULT_ONE_MODEL_HOST = "127.0.0.1"
DEFAULT_ONE_MODEL_PORT = 8000


def _pack_numpy(obj: Any) -> Any:
    """Recursively convert numpy arrays to one-model's MsgPack-friendly dicts."""
    if isinstance(obj, np.ndarray):
        return {
            "__ndarray__": True,
            "data": obj.tobytes(),
            "dtype": str(obj.dtype),
            "shape": list(obj.shape),
        }
    if isinstance(obj, dict):
        return {k: _pack_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_pack_numpy(v) for v in obj]
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _unpack_numpy(obj: Any) -> Any:
    """Recursively convert one-model's MsgPack dicts back to numpy arrays."""
    if isinstance(obj, dict):
        if obj.get("__ndarray__"):
            return np.frombuffer(obj["data"], dtype=np.dtype(obj["dtype"])).reshape(obj["shape"])
        return {k: _unpack_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_unpack_numpy(v) for v in obj]
    if isinstance(obj, bytes):
        # Msgpack decodes strings to bytes when raw=True; with raw=False we
        # still sometimes see bytes for binary-ish fields.
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return obj
    return obj


class OneModelWebsocketClient:
    """Thin synchronous client for one-model's PolicyServer.

    Mirrors :class:`capx.utils.openpi.OpenPIWebsocketClient`'s public
    interface (``metadata``, ``infer``, ``close``) so call sites can be
    dispatched on a backend flag without further plumbing.
    """

    def __init__(
        self,
        host: str = DEFAULT_ONE_MODEL_HOST,
        port: int = DEFAULT_ONE_MODEL_PORT,
        *,
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
        self._lock = Lock()
        self._ws: websockets.sync.client.ClientConnection | None = None
        self._metadata: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        self._ws = websockets.sync.client.connect(
            self._uri,
            compression=None,
            max_size=None,
            open_timeout=300,
            ping_interval=None,
            ping_timeout=None,
        )
        metadata_frame = self._ws.recv()
        if isinstance(metadata_frame, str):
            raise RuntimeError(
                f"one-model server returned a string during handshake: {metadata_frame}"
            )
        self._metadata = _unpack_numpy(msgpack.unpackb(metadata_frame, raw=False))

    @property
    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            self._connect()
        return self._metadata or {}

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send an observation dict and return the server's response dict.

        The payload is packed with one-model's `_pack_numpy` convention;
        the response is unpacked symmetrically. Any connection error
        invalidates the client's cached socket, so the caller can retry.
        """
        with self._lock:
            if self._ws is None:
                self._connect()
            try:
                assert self._ws is not None
                self._ws.send(msgpack.packb(_pack_numpy(payload), use_bin_type=True))
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
            raise RuntimeError(f"one-model server returned an error:\n{response}")
        data = _unpack_numpy(msgpack.unpackb(response, raw=False))
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict response from one-model server, got {type(data)!r}")
        return data

    def reset(self) -> None:
        """Send a reset signal so the policy clears any internal state (e.g. action broker)."""
        with self._lock:
            if self._ws is None:
                self._connect()
            try:
                assert self._ws is not None
                self._ws.send(msgpack.packb({"__reset__": True}, use_bin_type=True))
                ack = self._ws.recv()
            except Exception:
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                self._ws = None
                self._metadata = None
                raise
        if isinstance(ack, str):
            raise RuntimeError(f"one-model reset failed:\n{ack}")
        ack_dict = _unpack_numpy(msgpack.unpackb(ack, raw=False))
        if not (isinstance(ack_dict, dict) and ack_dict.get("__reset_ack__")):
            raise RuntimeError(f"one-model reset returned unexpected frame: {ack_dict!r}")

    def close(self) -> None:
        with self._lock:
            if self._ws is not None:
                try:
                    self._ws.close()
                except Exception:
                    pass
                self._ws = None
                self._metadata = None
