import base64
import os
import re
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from models.vlm_server import ensure_vllm_server
from openai import OpenAI

load_dotenv()
VLLM_PORT = int(os.getenv("VLLM_PORT", "15100"))
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", f"http://localhost:{VLLM_PORT}/v1")


def _encode_image_base64(image_path: Path) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _guess_mime_type(image_path: Path) -> str:
    """Guess MIME type from file extension."""
    suffix = image_path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    return mime_map.get(suffix, "image/png")


def _build_multimodal_content(
    domain_text: str,
    instruction: str,
    image_paths: List[Path],
) -> tuple:
    """Combines domain context, text instruction, and images into a single message payload."""
    system_text = (
        "You are helping a robotic planning task. "
        "Given the image of a scene and an instruction, generate "
        "the PDDL file with objects, initial state, and goal specification. "
        "Your output should adhere to the constraints defined in the provided domain file. "
        "You must output the PDDL file in the correct format. "
        "Output ONLY the PDDL problem text, "
        "enclosed in a ```pddl ... ``` code block."
    )

    content: List[dict] = []

    content.append(
        {
            "type": "text",
            "text": (
                f"For the current domain, this is the domain file:\n"
                f"```pddl\n{domain_text}\n```\n\n"
                f"The image of the scene has been provided. "
                f"Please first analyze the image and then generate the PDDL problem.\n\n"
            ),
        }
    )

    for img_path in image_paths:
        b64 = _encode_image_base64(img_path)
        mime = _guess_mime_type(img_path)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )

    content.append({"type": "text", "text": f"Instruction: {instruction}\n"})

    return system_text, content


def _extract_pddl_block(raw_output: str) -> str:
    """Extract the PDDL problem text from a fenced code block, falling back to raw output."""
    match = re.search(r"```(?:pddl)?\s*\n?(.*?)```", raw_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_output.strip()


def _generate_via_openai_client(
    model_id: str,
    system_text: str,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    base_url: str | None,
    api_key: str = "EMPTY",
) -> str:
    """Generate text using an OpenAI-compatible chat-completion endpoint.
    Works for both local vLLM (with base_url) and GPT (with api_key)."""
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_content},  # type: ignore
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    raw_text = response.choices[0].message.content or ""
    return _extract_pddl_block(raw_text)


def generate_pddl_problem(
    model_name: str,
    model_id: str,
    dataset_dir: Path,
    max_tokens: int,
    temperature: float,
    api_key: Optional[str] = None,
) -> str:
    """Generate a PDDL problem file from a domain file, text instruction, and images."""
    domain_text = (dataset_dir / "domain.pddl").read_text()
    instruction = (dataset_dir / "instruction.txt").read_text()
    image_paths = sorted((dataset_dir / "observations").glob("*.*"))
    if not image_paths:
        raise FileNotFoundError(f"No images found in {dataset_dir / 'observations'}")

    system_text, user_content = _build_multimodal_content(
        domain_text, instruction, image_paths
    )

    if model_name == "GPT-5.4":
        if api_key is None:
            raise ValueError("--api_key is required for GPT")
        return _generate_via_openai_client(
            model_id=model_id,
            system_text=system_text,
            user_content=user_content,
            max_tokens=max_tokens,
            temperature=temperature,
            base_url=None,
            api_key=api_key,
        )
    else:
        ensure_vllm_server(model_id, VLLM_PORT)  # local vLLM server
        return _generate_via_openai_client(
            model_id=model_id,
            system_text=system_text,
            user_content=user_content,
            max_tokens=max_tokens,
            temperature=temperature,
            base_url=VLLM_BASE_URL,
            api_key="EMPTY",
        )
