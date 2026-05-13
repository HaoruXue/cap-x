from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests
import tyro


logger = logging.getLogger(__name__)


@dataclass
class Args:
    """Launch the upstream OpenPI websocket policy server from a separate checkout."""

    openpi_root: str | None = None
    """Path to the OpenPI checkout. Falls back to the OPENPI_ROOT environment variable."""

    host: str = "127.0.0.1"
    """Host to poll for readiness. OpenPI itself binds 0.0.0.0 upstream."""

    port: int = 8000
    """Port exposed by the upstream OpenPI websocket server."""

    env: str | None = "libero"
    """Default OpenPI environment when using a built-in checkpoint: libero, droid, aloha, aloha_sim."""

    policy_config: str | None = None
    """OpenPI policy config name to serve, e.g. pi05_libero."""

    policy_dir: str | None = None
    """OpenPI checkpoint directory or remote asset URI, e.g. gs://openpi-assets/checkpoints/pi05_libero."""

    default_prompt: str | None = None
    """Fallback prompt injected by OpenPI when the observation omits one."""

    record: bool = False
    """Enable OpenPI policy recording for debugging."""

    ready_timeout: float = 300.0
    """Seconds to wait for the upstream /healthz endpoint before failing."""

    health_path: str = "/healthz"
    """HTTP health endpoint exposed by the upstream OpenPI websocket server."""

    log_file: str | None = None
    """Optional file to capture the upstream OpenPI server logs."""


def _resolve_openpi_root(args: Args) -> Path:
    root_str = args.openpi_root or os.getenv("OPENPI_ROOT")
    if not root_str:
        raise RuntimeError(
            "OpenPI root not set. Pass --openpi-root or export OPENPI_ROOT=/path/to/openpi."
        )

    root = Path(root_str).expanduser().resolve()
    serve_script = root / "scripts" / "serve_policy.py"
    pyproject = root / "pyproject.toml"
    if not serve_script.exists():
        raise FileNotFoundError(f"OpenPI serve script not found: {serve_script}")
    if not pyproject.exists():
        raise FileNotFoundError(f"OpenPI project file not found: {pyproject}")
    return root


def _build_command(args: Args, openpi_root: Path) -> list[str]:
    if shutil.which("uv") is None:
        raise RuntimeError("`uv` is required to launch OpenPI from its own project environment.")

    cmd = [
        "uv",
        "run",
        "--project",
        str(openpi_root),
        "--no-sync",
        str(openpi_root / "scripts" / "serve_policy.py"),
        "--port",
        str(args.port),
    ]

    if args.default_prompt:
        cmd.extend(["--default-prompt", args.default_prompt])
    if args.record:
        cmd.append("--record")

    using_checkpoint = args.policy_config is not None or args.policy_dir is not None
    if using_checkpoint:
        if not args.policy_config or not args.policy_dir:
            raise ValueError(
                "Pass both --policy-config and --policy-dir to launch a custom OpenPI checkpoint."
            )
        cmd.extend(
            [
                "policy:checkpoint",
                "--policy.config",
                args.policy_config,
                "--policy.dir",
                args.policy_dir,
            ]
        )
    else:
        if not args.env:
            raise ValueError("Pass --env when not launching a custom OpenPI checkpoint.")
        cmd.extend(["--env", args.env])

    return cmd


def _wait_for_ready(
    process: subprocess.Popen[str],
    host: str,
    port: int,
    health_path: str,
    timeout: float,
) -> None:
    url = f"http://{host}:{port}{health_path}"
    deadline = time.monotonic() + timeout
    last_error = "connection not ready yet"

    while time.monotonic() < deadline:
        rc = process.poll()
        if rc is not None:
            raise RuntimeError(f"OpenPI exited before becoming ready (exit code {rc}).")

        try:
            response = requests.get(url, timeout=2)
            if response.ok:
                logger.info("OpenPI is ready at %s", url)
                return
            last_error = f"health check returned {response.status_code}: {response.text.strip()}"
        except requests.RequestException as exc:
            last_error = str(exc)

        time.sleep(1.0)

    raise TimeoutError(f"Timed out waiting for OpenPI at {url}: {last_error}")


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main(args: Args) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    openpi_root = _resolve_openpi_root(args)
    cmd = _build_command(args, openpi_root)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    log_handle = None
    stdout = stderr = None
    if args.log_file:
        log_path = Path(args.log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
        stdout = stderr = log_handle

    logger.info("Launching OpenPI from %s", openpi_root)
    logger.info("CMD: %s", " ".join(cmd))
    process = subprocess.Popen(cmd, env=env, stdout=stdout, stderr=stderr, text=True)

    def _forward_signal(signum: int, _frame: object | None) -> None:
        if process.poll() is None:
            process.send_signal(signum)

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)

    try:
        _wait_for_ready(
            process=process,
            host=args.host,
            port=args.port,
            health_path=args.health_path,
            timeout=args.ready_timeout,
        )
        rc = process.wait()
    except Exception:
        _terminate_process(process)
        raise
    finally:
        if log_handle is not None:
            log_handle.close()

    if rc != 0:
        raise SystemExit(rc)


if __name__ == "__main__":
    main(tyro.cli(Args))
