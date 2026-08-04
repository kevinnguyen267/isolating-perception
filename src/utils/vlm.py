import base64
import json
import os
import time
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import List

from google import genai
from google.genai import types
from openai import OpenAI
from openai.types.chat import ChatCompletion

from models import config
from utils.usage import record_completion_tokens


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


@lru_cache(maxsize=None)
def get_client(model_id: str, use_openrouter: bool = False):
    """Return an OpenAI client configured for the specified model."""
    if use_openrouter:
        if not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
        return OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
    if model_id.startswith("gpt"):
        return OpenAI()
    if config.VLLM_BASE_URL is None:
        raise RuntimeError(_NO_SERVER_MSG)
    return OpenAI(api_key="EMPTY", base_url=config.VLLM_BASE_URL, timeout=1800)


_NO_SERVER_MSG = (
    "No vLLM server configured for this run. Start one with\n"
    "    scripts/serve_vllm.sh --model <model_name> --gpus <csv>\n"
    "and point the run at it with VLLM_PORT (or VLLM_BASE_URL)."
)

NO_VERTEX_CREDENTIALS_MSG = (
    "No Vertex AI credentials. Set GOOGLE_CLOUD_PROJECT (and run\n"
    "    gcloud auth application-default login\n"
    "once) to use a real project, or GEMINI_API_KEY / GOOGLE_API_KEY to use\n"
    "express mode, which cannot run batch jobs."
)


def verify_vllm_server(model_id: str) -> str:
    """Check that a vLLM server is up and serving *model_id*; return its base URL.

    Called once at startup so a missing or mismatched server fails immediately
    instead of after the dataset and prompts have been built.
    """
    if config.VLLM_BASE_URL is None:
        raise RuntimeError(_NO_SERVER_MSG)
    try:
        with urllib.request.urlopen(f"{config.VLLM_BASE_URL}/models", timeout=10) as resp:
            served = [m["id"] for m in json.loads(resp.read().decode()).get("data", [])]
    except Exception as e:
        raise RuntimeError(
            f"No vLLM server reachable at {config.VLLM_BASE_URL} ({e}). "
            "Start one with scripts/serve_vllm.sh, or check VLLM_PORT."
        ) from e
    if model_id not in served:
        raise RuntimeError(
            f"The vLLM server at {config.VLLM_BASE_URL} serves {served}, not "
            f"{model_id}. Point VLLM_PORT at the right server."
        )
    return config.VLLM_BASE_URL


def _create_completion(
    client: OpenAI,
    use_openrouter: bool,
    model_id: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    seed: int,
    thinking: bool,
) -> ChatCompletion:
    """Create a chat completion using the appropriate client for the model."""
    if use_openrouter:
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )

    if model_id.startswith("gpt"):
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_completion_tokens=max_tokens,
        )
    else:
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": thinking},
            },
        )


def _format_response(thinking: str, content: str) -> str:
    """Combine thinking and content into a single string (thinking is optional)."""
    if not thinking:
        return content
    return (
        "=" * 80
        + "\nTHINKING:\n"
        + "=" * 80
        + f"\n{thinking}\n\n"
        + "=" * 80
        + "\nRESPONSE:\n"
        + "=" * 80
        + f"\n{content}"
    )


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """Return a Vertex AI client.

    Uses the project and application default credentials when
    GOOGLE_CLOUD_PROJECT is set, and express mode (API key) otherwise. Only the
    non-API key mode can submit batch jobs.
    """
    if config.GOOGLE_CLOUD_PROJECT:
        return genai.Client(
            vertexai=True,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_LOCATION,
        )
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(NO_VERTEX_CREDENTIALS_MSG)
    return genai.Client(vertexai=True, api_key=api_key)


def _content_to_gemini_parts(user_content: List[dict]) -> List[types.Part]:
    """Convert OpenAI-style content blocks into Gen AI SDK Parts."""
    parts: List[types.Part] = []
    for block in user_content:
        block_type = block.get("type")
        if block_type == "text":
            parts.append(types.Part.from_text(text=block["text"]))
        elif block_type == "image_url":
            # Blocks are produced by image_block() as data:{mime};base64,{b64} URLs
            url = block["image_url"]["url"]
            header, _, data = url.partition(",")
            mime_type = header.removeprefix("data:").split(";", 1)[0]
            parts.append(
                types.Part.from_bytes(data=base64.b64decode(data), mime_type=mime_type)
            )
        else:
            raise ValueError(f"Unsupported content block type: {block_type!r}")
    return parts


def content_to_gemini_parts_dict(user_content: List[dict]) -> List[dict]:
    """Convert OpenAI-style content blocks into REST-format Gemini part dicts."""
    parts: List[dict] = []
    for block in user_content:
        block_type = block.get("type")
        if block_type == "text":
            parts.append({"text": block["text"]})
        elif block_type == "image_url":
            # Blocks are produced by image_block() as data:{mime};base64,{b64} URLs.
            url = block["image_url"]["url"]
            header, _, data = url.partition(",")
            mime_type = header.removeprefix("data:").split(";", 1)[0]
            parts.append({"inlineData": {"mimeType": mime_type, "data": data}})
        else:
            raise ValueError(f"Unsupported content block type: {block_type!r}")
    return parts


def gemini_generation_config_dict(
    max_tokens: int, temperature: float, seed: int
) -> dict:
    """REST-format generationConfig mirroring the synchronous Gemini config."""
    return {
        "maxOutputTokens": max_tokens,
        "temperature": temperature,
        "seed": seed,
        "thinkingConfig": {"includeThoughts": True},
    }


def parse_gemini_response_dict(response: dict) -> str:
    """Parse a REST-format GenerateContentResponse dict into a single string."""
    candidates = response.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []

    thinking_parts: List[str] = []
    content_parts: List[str] = []
    for part in parts:
        text = part.get("text")
        if not text:
            continue
        if part.get("thought"):
            thinking_parts.append(text)
        else:
            content_parts.append(text)

    return _format_response("".join(thinking_parts), "".join(content_parts))


def _generate_with_retries(
    client: genai.Client,
    model_id: str,
    contents: List[types.Content],
    config: types.GenerateContentConfig,
    max_retries: int = 5,
    initial_delay: float = 2.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
):
    """Call Gemini generate_content, retrying transient errors with exponential backoff."""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model=model_id,
                contents=contents,  # type: ignore
                config=config,
            )
        except Exception as e:
            if attempt == max_retries:
                raise
            print(
                f"    Gemini call failed (attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)


def _generate_response_gemini(
    model_id: str,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    seed: int,
) -> str:
    """Generate a response using a Gemini model on Vertex AI."""
    client = get_gemini_client()

    contents = [
        types.Content(role="user", parts=_content_to_gemini_parts(user_content))
    ]
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )

    response = _generate_with_retries(client, model_id, contents, config)

    usage = response.usage_metadata  # type: ignore
    if usage:
        thoughts = getattr(usage, "thoughts_token_count", None)
        record_completion_tokens(usage.candidates_token_count, thoughts)
        thoughts_str = f"Thinking: {thoughts}, " if thoughts else ""
        print(
            "    Usage - "
            f"Prompt: {usage.prompt_token_count}, "
            f"Completion: {usage.candidates_token_count}, "
            f"{thoughts_str}"
            f"Total: {usage.total_token_count}"
        )

    thinking_parts: List[str] = []
    content_parts: List[str] = []
    for part in response.candidates[0].content.parts or []:  # type: ignore
        text = getattr(part, "text", None)
        if not text:
            continue
        if getattr(part, "thought", False):
            thinking_parts.append(text)
        else:
            content_parts.append(text)

    return _format_response("".join(thinking_parts), "".join(content_parts))


def generate_response(
    model_id: str,
    use_openrouter: bool,
    use_gemini: bool,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    seed: int,
    thinking: bool,
) -> str:
    """Generate a response using the Gemini Agent Platform (Gen AI SDK), GPT/OpenRouter
    (api_key), or local vLLM (base_url)."""
    if use_gemini:
        return _generate_response_gemini(
            model_id, user_content, max_tokens, temperature, seed
        )

    client = get_client(model_id, use_openrouter)

    messages = [{"role": "user", "content": user_content}]
    response = _create_completion(
        client,
        use_openrouter,
        model_id,
        messages,
        max_tokens,
        temperature,
        seed,
        thinking,
    )

    message = response.choices[0].message
    thinking_content = getattr(message, "reasoning", None) or ""
    content = message.content or ""

    if response.usage:
        record_completion_tokens(response.usage.completion_tokens)
        print(
            "    Usage - "
            f"Prompt: {response.usage.prompt_tokens}, "
            f"Completion: {response.usage.completion_tokens}, "
            f"Total: {response.usage.total_tokens}"
        )

    return _format_response(thinking_content, content)
