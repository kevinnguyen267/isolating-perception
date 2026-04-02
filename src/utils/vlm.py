import base64
from pathlib import Path
from typing import List

from models.config import VLLM_BASE_URL
from openai import OpenAI
from openai.types.chat import ChatCompletion


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


def get_client(model_id: str):
    """Return an OpenAI client configured for the specified model."""
    return (
        OpenAI()
        if model_id.startswith("gpt")
        else OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)
    )


def create_completion(
    client: OpenAI,
    model_id: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    seed: int,
) -> ChatCompletion:
    """Create a chat completion using the appropriate client for the model."""
    if model_id.startswith("gpt"):
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
    elif model_id == "Qwen/Qwen3.5-122B-A10B":
        # Recommended parameters for "thinking mode for general tasks" /
        # "non-thinking mode for reasoning tasks" from HF
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=1.0,
            top_p=0.95,
            presence_penalty=1.5,
            seed=seed,
            extra_body={
                "top_k": 20,
                "min_p": 0.0,
                "repetition_penalty": 1.0,
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
    else:
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )


def generate_response(
    model_id: str,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    seed: int,
) -> str:
    """Generate a response using GPT (api_key) or local vLLM (base_url)."""
    client = get_client(model_id)

    messages = [{"role": "user", "content": user_content}]
    response = create_completion(
        client, model_id, messages, max_tokens, temperature, seed
    )

    if response.usage:
        print(f"    User content: {user_content}...")
        print(
            "    Usage - "
            f"Prompt: {response.usage.prompt_tokens}, "
            f"Completion: {response.usage.completion_tokens}, "
            f"Total: {response.usage.total_tokens}"
        )

    message = response.choices[0].message
    thinking = getattr(message, "reasoning", None) or ""
    content = message.content or ""

    return (
        "=" * 80
        + "\nTHINKING:\n"
        + "=" * 80
        + f"\n{thinking}\n\n"
        + "=" * 80
        + "\nRESPONSE:\n"
        + "=" * 80
        + f"\n{content}"
        if thinking
        else content
    )
