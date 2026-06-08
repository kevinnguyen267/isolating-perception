import os

from dotenv import load_dotenv

load_dotenv()
VLLM_PORT = int(os.getenv("VLLM_PORT", "12300"))
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", f"http://localhost:{VLLM_PORT}/v1")

MODEL_CONFIG = {
    "GPT-5.5": {
        "model_id": "gpt-5.5-2026-04-23",
    },
    "Gemini-3.1-Pro": {
        "openrouter_model_id": "google/gemini-3.1-pro-preview",
        "gemini_model_id": "gemini-3.1-pro-preview",
    },
    "Qwen3.6-Plus": {
        "openrouter_model_id": "qwen/qwen3.6-plus",
    },
    "Qwen3.5-122B-A10B": { 
        "model_id": "Qwen/Qwen3.5-122B-A10B",
        "openrouter_model_id": "qwen/qwen3.5-122b-a10b",
        "vllm_serve_args": [
            "-tp", "4",
            "--max-model-len", "65536",
            "--enable-expert-parallel",
            "--mm-encoder-tp-mode", "data",
            "--mm-processor-cache-type", "shm",
            "--enable-prefix-caching",
            "--reasoning-parser", "qwen3",
        ],
    },
    "InternVL3.5-38B": {
        "model_id": "OpenGVLab/InternVL3_5-38B", 
        "vllm_serve_args": [
            "-tp", "2",
            "--max-model-len", "32768",
            "--trust-remote-code"
        ],
    },
    "Gemma-4-31B": { 
        "model_id": "google/gemma-4-31B-it",
        "openrouter_model_id": "google/gemma-4-31b-it",
        "vllm_serve_args": [
            "-tp", "2",
            "--max-model-len", "32768",
        ],
    }
}
