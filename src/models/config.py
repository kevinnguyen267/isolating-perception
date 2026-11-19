import os

from dotenv import load_dotenv

load_dotenv()

# vLLM connection settings
# Experiments never start a server: point a run at one that scripts/serve_vllm.sh
# already launched, with VLLM_PORT (or VLLM_BASE_URL for a server elsewhere).
_VLLM_PORT_ENV = os.getenv("VLLM_PORT")
VLLM_PORT = int(_VLLM_PORT_ENV) if _VLLM_PORT_ENV else None
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL") or (
    f"http://localhost:{VLLM_PORT}/v1" if VLLM_PORT else None
)

# Vertex AI settings
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
VERTEX_BATCH_BUCKET = os.getenv("VERTEX_BATCH_BUCKET")  # gs://<bucket>[/<prefix>]

# vllm_serve_args below are not used by the experiments; scripts/serve_vllm.sh
# reads them so that the launch flags for a model live in one place.
MODEL_CONFIG = {
    "Gemini-3.1-Pro": {
        "openrouter_model_id": "google/gemini-3.1-pro-preview",
        "gemini_model_id": "gemini-3.1-pro-preview",
    },
    "Qwen3.5-122B-A10B": {
        "model_id": "Qwen/Qwen3.5-122B-A10B",
        "openrouter_model_id": "qwen/qwen3.5-122b-a10b",
        "vllm_serve_args": [
            "--max-model-len", "40960",
            "--enable-expert-parallel",
            "--mm-encoder-tp-mode", "data",
            "--mm-processor-cache-type", "shm",
            "--enable-prefix-caching",
            "--reasoning-parser", "qwen3",
        ],
    },
    "Gemma-4-31B": {
        "model_id": "google/gemma-4-31B-it",
        "openrouter_model_id": "google/gemma-4-31b-it",
        "vllm_serve_args": [
            "--max-model-len", "40960",
            "--reasoning-parser", "gemma4",
        ],
    },
    "Gemma-4-12B": {
        "model_id": "google/gemma-4-12B-it",
        "openrouter_model_id": "google/gemma-4-12b-it",
        "vllm_serve_args": [
            "--max-model-len", "40960",
            "--reasoning-parser", "gemma4",
        ],
    }
}
