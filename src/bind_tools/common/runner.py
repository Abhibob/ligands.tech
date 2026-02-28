"""Subprocess and Docker execution helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import InputMissingError, TimeoutError, UpstreamError


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    command: list[str] = field(default_factory=list)


def detect_device() -> str:
    """Auto-detect compute device. Checks BIND_TOOLS_DEVICE env var first."""
    env_device = os.environ.get("BIND_TOOLS_DEVICE")
    if env_device:
        return env_device
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


def run_subprocess(
    cmd: list[str],
    *,
    timeout_s: int | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> RunResult:
    """Run a subprocess with timeout handling."""
    merged_env = {**os.environ, **(env or {})}
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=cwd,
            env=merged_env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - start
        raise TimeoutError(
            f"Command timed out after {timeout_s}s: {' '.join(cmd)}"
        ) from exc
    except FileNotFoundError as exc:
        elapsed = time.monotonic() - start
        raise InputMissingError(f"Command not found: {cmd[0]}") from exc

    elapsed = time.monotonic() - start
    return RunResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        elapsed_seconds=elapsed,
        command=cmd,
    )


def run_docker(
    image: str,
    cmd: list[str],
    *,
    volumes: dict[str, str] | None = None,
    device: str = "cpu",
    timeout_s: int | None = None,
    workdir: str = "/data",
) -> RunResult:
    """Run a command inside a Docker container."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        raise InputMissingError("Docker is not installed or not in PATH")

    docker_cmd = [docker_bin, "run", "--rm"]

    # Platform -- gnina image is x86_64, force Rosetta on ARM hosts
    import platform
    if platform.machine() in ("arm64", "aarch64"):
        docker_cmd.extend(["--platform", "linux/amd64"])

    # GPU passthrough
    if device != "cpu":
        docker_cmd.extend(["--gpus", "all"])

    # Volume mounts
    for host_path, container_path in (volumes or {}).items():
        docker_cmd.extend(["-v", f"{host_path}:{container_path}"])

    docker_cmd.extend(["-w", workdir, image])
    docker_cmd.extend(cmd)

    return run_subprocess(docker_cmd, timeout_s=timeout_s)


def ensure_file(path: str | Path, label: str = "file") -> Path:
    """Validate that a file exists and return its resolved Path."""
    p = Path(path).resolve()
    if not p.is_file():
        raise InputMissingError(f"{label} not found: {p}")
    return p


def ensure_dir(path: str | Path, label: str = "directory", create: bool = False) -> Path:
    """Validate or create a directory and return its resolved Path."""
    p = Path(path).resolve()
    if create:
        p.mkdir(parents=True, exist_ok=True)
    if not p.is_dir():
        raise InputMissingError(f"{label} not found: {p}")
    return p
