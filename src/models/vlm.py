import base64
import os
import re
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from models.vllm_server import ensure_vllm_server
from openai import OpenAI
from utils.parse import create_problem_from_sections, parse_section

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


def _image_block(path: Path) -> dict:
    mime = _guess_mime_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def _build_grounding_prompt_from_imgs(
    objects: set[str],
    predicates: set[str],
    image_paths: List[Path],
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from the images, given the set of objects and predicates."""
    return [
        {
            "type": "text",
            "text": (
                "Given observations of the same static scene from different perspectives, the set of objects, and the set of predicates, "
                "reconcile all views into a single consistent world state and determine the true grounded predicates.\n\n"
                "Hints:\n"
                "Every object exists exactly once in the scene.\n"
                "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) means block x is on block y."
            ),
        },
        *(_image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}"
            ),
        },
    ]


def _build_grounding_prompt_from_instruction(
    objects: set[str],
    predicates: set[str],
    instruction: str,
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from the instruction, given the set of objects and predicates."""
    return [
        {
            "type": "text",
            "text": (
                "Given an instruction, the set of objects, and the set of predicates, determine the true grounded predicates.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is mentioned in the instruction, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) means block x is on block y.\n\n"
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}"
            ),
        },
    ]


def _generate_response(
    model_id: str,
    user_content: List[dict],
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> str:
    """Generate a response using GPT (api_key) or local vLLM (base_url)."""
    if model_id == "gpt-5.4":
        client = OpenAI()
    else:
        ensure_vllm_server(model_id, VLLM_PORT, quantization)
        client = OpenAI(api_key="EMPTY", base_url=VLLM_BASE_URL)

    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": user_content},  # type: ignore
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
    )

    return response.choices[0].message.content or ""


def _cleanup_response_and_extract_preds(
    objects: set[str],
    predicates: set[str],
    response: str,
    model_id: str,
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> tuple[set[str], str]:
    """Use a second prompt to clean up the VLM response and extract the final set of grounded predicates.

    Returns: (grounded_preds, cleanup_response)"""
    object_names = set(o.split(" ")[0] for o in objects)
    pred_names = set(p.split(" ")[0] for p in predicates)

    cleanup_prompt = [
        {
            "type": "text",
            "text": (
                "Extract all true grounded predicates from the response below.\n\n"
                "Rules:\n"
                f"- Valid objects: {', '.join(sorted(object_names))}\n"
                f"- Valid predicates: {', '.join(sorted(pred_names))}\n"
                "- Fix any typos in object names to match the valid objects list.\n"
                "- Fix any typos in predicates to match the valid predicates list.\n"
                "- Remove any predicates not in the valid predicates list.\n"
                "Output each predicate on its own line as: (predicate_name arg1 arg2 ...)\n"
                "No extra text, headers, or formatting.\n\n"
                f"Response:\n{response}"
            ),
        },
    ]
    cleanup_response = _generate_response(
        model_id,
        cleanup_prompt,
        max_tokens,
        temperature,
        seed,
        quantization,
    )

    lines = cleanup_response.strip().splitlines()
    grounded_preds = set()
    for pred in lines:
        tokens = pred.replace("(", " ").replace(")", " ").replace(",", " ").split()
        if not tokens:
            continue
        grounded_preds.add(f"({tokens[0]} {' '.join(tokens[1:])})")
    return grounded_preds, cleanup_response


def _generate_grounded_preds(
    model_id: str,
    context: List[Path] | str,
    objects: set[str],
    predicates: set[str],
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> tuple[set[str], str, str]:
    """Generate grounded predicates in two steps.

    If context is a list of image paths, generate grounded predicates from the images.
    If context is a string instruction, generate grounded predicates from the instruction.

    First, generate grounded predicates from either the images or the
    instruction. Then, use a second prompt to clean up the VLM response
    and extract the final set of grounded predicates.

    Returns: (grounded_preds, VLM_response, cleanup_VLM_response)
    """
    if isinstance(context, str):
        prompt = _build_grounding_prompt_from_instruction(objects, predicates, context)
    else:
        prompt = _build_grounding_prompt_from_imgs(objects, predicates, context)

    response = _generate_response(
        model_id,
        prompt,
        max_tokens,
        temperature,
        seed,
        quantization,
    )

    grounded_preds, cleanup_response = _cleanup_response_and_extract_preds(
        objects,
        predicates,
        response,
        model_id,
        max_tokens,
        temperature,
        seed,
        quantization,
    )

    return grounded_preds, response, cleanup_response


def generate_pddl_problem(
    model_id: str,
    dataset_problem_dir: Path,
    gt_domain: str,
    gt_problem: str,
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> tuple[str, str, str, str, str]:
    """Generates a PDDL problem file given context from the dataset.

    Returns: (problem, init_response, goal_response, init_cleanup_response, goal_cleanup_response)
    """
    # TODO: Placeholder: given objects for blocksworld_real
    objects = set(
        [
            "robot1 - robot",
            "red_block - block",
            "orange_block - block",
            "yellow_block - block",
            "green_block - block",
            "blue_block - block",
            "purple_block - block",
        ]
    )

    # TODO: Placeholder: given objects for blocksworld_sim
    # bboxes_path = dataset_problem_dir / "annotated_bbox.json"
    # with bboxes_path.open() as f:
    #     bboxes = json.load(f)
    # object_names = set(bboxes.keys())
    # objects = set()
    # for name in object_names:
    #     objects.add(f"{name} - block")
    # object_names.add("robot1")
    # objects.add("robot1 - robot")

    # Extract predicates from the domain
    predicates = parse_section(gt_domain, ":predicates")
    predicates = set(p.strip("()") for p in predicates)

    # Extract image paths and instruction from the dataset directory
    image_paths = sorted((dataset_problem_dir / "observations").glob("*.*"))
    if not image_paths:
        raise FileNotFoundError(
            f"No images found in {dataset_problem_dir / 'observations'}"
        )
    try:
        instruction = (dataset_problem_dir / "instruction.txt").read_text()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"No instruction found in {dataset_problem_dir / 'instruction.txt'}"
        )

    # Generate init and goal grounded predicates
    init_preds, init_response, init_cleanup_response = _generate_grounded_preds(
        model_id,
        image_paths,
        objects,
        predicates,
        max_tokens,
        temperature,
        seed,
        quantization,
    )
    goal_preds, goal_response, goal_cleanup_response = _generate_grounded_preds(
        model_id,
        instruction,
        objects,
        predicates,
        max_tokens,
        temperature,
        seed,
        quantization,
    )

    # Extract domain name from the ground truth domain file
    match = re.search(r"\(domain\s+(\w+)\)", gt_domain)
    if not match:
        raise ValueError(
            "Could not extract domain name from the ground truth domain file."
        )
    domain_name = match.group(1)

    # Extract problem name from the ground truth problem file
    match = re.search(r"\(problem\s+(\w+)\)", gt_problem)
    if not match:
        raise ValueError(
            "Could not extract problem name from the ground truth problem file."
        )
    problem_name = match.group(1)

    problem = create_problem_from_sections(
        problem_name,
        domain_name,
        objects,
        init_preds,
        goal_preds,
    )
    return (
        problem,
        init_response,
        goal_response,
        init_cleanup_response,
        goal_cleanup_response,
    )
