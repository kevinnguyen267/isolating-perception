import json
import os
import shutil
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

from models.config import MODEL_CONFIG, VLLM_PORT


def _vllm_health_ok(port: int, timeout: float = 3.0) -> bool:
    """Return True if the vLLM server on *port* responds to /health."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _vllm_model_matches(model_name: str, port: int) -> bool:
    """Return True if the running vLLM server is serving *model_id*."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            served = [m["id"] for m in data.get("data", [])]
            return MODEL_CONFIG[model_name]["model_id"] in served
    except Exception:
        return False


def _launch_vllm_server(model_name: str, port: int) -> None:
    """Launch a vLLM server for *model_id* and block until it is healthy."""
    cfg = MODEL_CONFIG[model_name]
    if "vllm_serve_args" not in cfg:
        raise ValueError(f"Model {model_name} is not configured for vLLM serving.")

    vllm_bin = shutil.which("vllm")
    if vllm_bin is None:
        raise RuntimeError("vllm CLI not found. Install with: pip install vllm")

    cmd = [
        vllm_bin,
        "serve",
        cfg["model_id"],
        "--port",
        str(port),
    ]
    cmd.extend(cfg["vllm_serve_args"])

    print(f"Launching vLLM server: {' '.join(cmd)}")
    log_path = Path(f"logs/vllm_{cfg['model_id'].replace('/', '_')}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
        (log_path.parent / f"{log_path.stem}.pid").write_text(str(proc.pid))
    print(f"vLLM log: {log_path.resolve()}")

    # Wait for server to become healthy
    print("Waiting for vLLM server to be ready...", end="", flush=True)
    max_wait = 1200  # 20 minutes
    waited = 0
    interval = 5
    while waited < max_wait:
        time.sleep(interval)
        waited += interval
        if proc.poll() is not None:
            raise RuntimeError(
                f"vLLM exited with code {proc.returncode}. Check {log_path.resolve()}"
            )
        if _vllm_health_ok(port):
            print(f" ready! ({waited}s)")
            return
        if waited % 30 == 0:
            print(f" {waited}s...", end="", flush=True)

    raise RuntimeError(
        f"vLLM server did not become healthy within {max_wait}s. Check logs at {log_path.resolve()} for details."
    )


def ensure_vllm_server(model_name: str, port: int = VLLM_PORT) -> None:
    """Ensure a vLLM server is running for *model_id*, else launch one."""
    if _vllm_health_ok(port):
        if _vllm_model_matches(model_name, port):
            return
        raise RuntimeError(
            f"A vLLM server is running on port {port} but serving a different model. "
            f"Stop it first or use a different VLLM_PORT."
        )
    _launch_vllm_server(model_name, port)


def kill_vllm_server() -> None:
    """Kill any running vLLM server started by this script (identified by PID files in logs/)."""
    logs_dir = Path("logs")
    for pid_path in logs_dir.glob("vllm_*.pid"):
        pid = int(pid_path.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to vLLM server (PID {pid}).")
        except ProcessLookupError:
            print(f"Process {pid} not found. Server already stopped.")
        finally:
            pid_path.unlink(missing_ok=True)
            pid_path.with_suffix(".log").unlink(missing_ok=True)
