import base64
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from models.vllm_server import ensure_vllm_server
from openai import OpenAI

load_dotenv()
VLLM_PORT = int(os.getenv("VLLM_PORT", "15100"))
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", f"http://localhost:{VLLM_PORT}/v1")


def _guess_mime_type(image_path: Path) -> str:
    """Guess MIME type from file extension."""
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    suffix = image_path.suffix.lower()
    if suffix not in mime_map:
        raise ValueError(f"Unsupported image format: {suffix}")
    return mime_map[suffix]


def image_block(path: Path) -> dict:
    mime = _guess_mime_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def generate_response(
    model_id: str,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> str:
    """Generate a response using GPT (api_key) or local vLLM (base_url)."""
    messages = [{"role": "user", "content": user_content}]

    if model_id == "gpt-5.4":
        client = OpenAI()

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,  # type: ignore
            max_completion_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
    else:
        ensure_vllm_server(model_id, VLLM_PORT, quantization)
        client = OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)

        if model_id == "Qwen/Qwen3.5-122B-A10B":
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,  # type: ignore
                max_tokens=max_tokens,
                temperature=0.6,
                top_p=0.95,
                presence_penalty=0.0,
                seed=seed,
                extra_body={
                    "top_k": 20,
                    "min_p": 0.0,
                    "repetition_penalty": 1.0,
                },
            )
        else:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,  # type: ignore
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
            )

    return response.choices[0].message.content or ""
