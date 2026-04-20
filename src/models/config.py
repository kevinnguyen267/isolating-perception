import os

from dotenv import load_dotenv

load_dotenv()
VLLM_PORT = int(os.getenv("VLLM_PORT", "12300"))
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", f"http://localhost:{VLLM_PORT}/v1")

MODEL_CONFIG = {
    "GPT-5.4": {
        "model_id": "gpt-5.4-2026-03-05",
    },
    "Qwen3.5-122B-A10B": { 
        "model_id": "Qwen/Qwen3.5-122B-A10B",
        "vllm_serve_args": [
            "-tp", "4",
            "--max-model-len", "32768",
            "--enable-expert-parallel",
            "--mm-encoder-tp-mode", "data",
            "--mm-processor-cache-type", "shm",
            "--enable-prefix-caching",
            "--reasoning-parser", "qwen3",
        ],
    },
    "Qwen3-VL-235B-A22B": {
        "model_id": "Qwen/Qwen3-VL-235B-A22B-Instruct",
        "vllm_serve_args": [
            "-tp", "4",
            "--max-model-len", "32768",
            "--enable-expert-parallel",
            "--mm-encoder-tp-mode", "data",
            "--limit-mm-per-prompt.video", "0",
            "--async-scheduling",
            "--quantization", "fp8"
        ],
    },
}
