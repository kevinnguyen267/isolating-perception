import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import torch

VLLM_SERVE_CONFIG = {
    "Qwen/Qwen3-VL-235B-A22B-Instruct": {
        "tp_size": torch.cuda.device_count(),
        "expert_parallel": True,
        "max_model_len": 8192,
        "gpu_memory_utilization": 0.9,
        "mm_encoder_tp_mode": "data",
    }
}


def _vllm_health_ok(port: int, timeout: float = 3.0) -> bool:
    """Return True if the vLLM server on *port* responds to /health."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _vllm_model_matches(model_id: str, port: int) -> bool:
    """Return True if the running vLLM server is serving *model_id*."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            served = [m["id"] for m in data.get("data", [])]
            return model_id in served
    except Exception:
        return False


def _launch_vllm_server(model_id: str, port: int) -> None:
    """Launch a vLLM server for *model_id* and block until it is healthy."""
    cfg = VLLM_SERVE_CONFIG[model_id]

    vllm_bin = shutil.which("vllm")
    if vllm_bin is None:
        raise RuntimeError("vllm CLI not found. Install with: pip install vllm")

    cmd = [
        vllm_bin,
        "serve",
        model_id,
        "--tensor-parallel-size",
        str(cfg["tp_size"]),
        "--port",
        str(port),
        "--max-model-len",
        str(cfg["max_model_len"]),
        "--gpu-memory-utilization",
        str(cfg["gpu_memory_utilization"]),
    ]
    if cfg.get("expert_parallel"):
        cmd.append("--enable-expert-parallel")
    if cfg.get("mm_encoder_tp_mode"):
        cmd.extend(["--mm-encoder-tp-mode", cfg["mm_encoder_tp_mode"]])

    print(f"Launching vLLM server: {' '.join(cmd)}")
    log_path = Path(f"logs/vllm_{model_id.replace('/', '_')}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as log_file:
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    print(f"vLLM log: {log_path}")

    # Wait for server to become healthy
    print("Waiting for vLLM server to be ready...", end="", flush=True)
    max_wait = 1200  # 20 minutes
    waited = 0
    interval = 5
    while waited < max_wait:
        time.sleep(interval)
        waited += interval
        if _vllm_health_ok(port):
            print(f" ready! ({waited}s)")
            return
        if waited % 30 == 0:
            print(f" {waited}s...", end="", flush=True)

    raise RuntimeError(
        f"vLLM server did not become healthy within {max_wait}s. "
        f"Check logs at {log_path}"
    )


def ensure_vllm_server(model_id: str, port: int) -> None:
    """Ensure a vLLM server is running for *model_id*, else launch one."""
    if _vllm_health_ok(port):
        if _vllm_model_matches(model_id, port):
            return
        raise RuntimeError(
            f"A vLLM server is running on port {port} but serving a different model. "
            f"Stop it first or use a different VLLM_PORT."
        )
    _launch_vllm_server(model_id, port)
