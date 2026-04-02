import re
from pathlib import Path
from typing import List

from utils.parse import (
    create_problem_from_sections,
    extract_output_from_response,
    parse_section,
)
from utils.vlm import generate_response, image_block


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
                "You are given a scene, a set of objects, and a set of predicates.\n"
                "Describe the objects, their positions, and their spatial relationships.\n\n"
                "Every object exists exactly once and is visible. If your analysis contradicts this statement, re-examine the scene and pay closer attention to the object(s) contributing to the contradiction.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, determine the true grounded predicates and list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
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
                "Given an instruction, a set of objects, and a set of predicates, determine the true grounded predicates.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is mentioned in the instruction, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the true grounded predicates, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]


def _generate_grounded_preds(
    model_id: str,
    context: List[Path] | str,
    objects: set[str],
    predicates: set[str],
    max_tokens: int,
    temperature: float,
    seed: int,
) -> str:
    """Prompts the VLM to generate grounded predicates from the provided context.

    If the context is a list of image paths, prompts the VLM to generate grounded predicates from the images.
    If the context is an instruction string, prompts the VLM to generate grounded predicates from the instruction.

    Returns: VLM response
    """
    # Build context for prompting VLM
    if isinstance(context, str):
        prompt = _build_grounding_prompt_from_instruction(objects, predicates, context)
    else:
        prompt = _build_grounding_prompt_from_imgs(objects, predicates, context)

    # Prompt the VLM to generate grounded predicates
    return generate_response(
        model_id,
        prompt,
        max_tokens,
        temperature,
        seed,
    )


def _get_objects_and_predicates(
    dataset_problem_dir: Path,
    gt_domain: str,
) -> tuple[set[str], set[str], List[Path], str]:
    """Extract objects, predicates, image paths, and instruction from the dataset.

    Returns: (objects, predicates, image_paths, instruction)
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

    return objects, predicates, image_paths, instruction


def build_formalizer_prompts(
    dataset_problem_dir: Path,
    gt_domain: str,
) -> tuple[List[dict], List[dict], set[str]]:
    """Build prompts for the (image-based) and goal (instruction-based).

    Returns: (init_prompt, goal_prompt, objects)
    """
    objects, predicates, image_paths, instruction = _get_objects_and_predicates(
        dataset_problem_dir, gt_domain
    )

    init_prompt = _build_grounding_prompt_from_imgs(objects, predicates, image_paths)
    goal_prompt = _build_grounding_prompt_from_instruction(
        objects, predicates, instruction
    )

    return init_prompt, goal_prompt, objects


def assemble_pddl_problem(
    init_response: str,
    goal_response: str,
    objects: set[str],
    gt_domain: str,
    gt_problem: str,
) -> tuple[str, str, str, str, str]:
    """Assemble a PDDL problem from pre-obtained VLM responses.

    Returns: (problem, init_response, goal_response, init_response_extracted, goal_response_extracted)
    """
    init_preds, init_response_extracted = extract_output_from_response(init_response)
    goal_preds, goal_response_extracted = extract_output_from_response(goal_response)

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
        init_response_extracted,
        goal_response_extracted,
    )


def generate_pddl_problem(
    model_id: str,
    dataset_problem_dir: Path,
    gt_domain: str,
    gt_problem: str,
    max_tokens: int,
    temperature: float,
    seed: int,
) -> tuple[str, str, str, str, str]:
    """Generates a PDDL problem file given context from the dataset.

    Returns: (problem, init_response, goal_response, init_response_extracted, goal_response_extracted)
    """
    # Build context for prompting VLM
    objects, predicates, image_paths, instruction = _get_objects_and_predicates(
        dataset_problem_dir, gt_domain
    )

    # Prompt VLM to generate grounded predicates for the init and goal sections
    init_response = _generate_grounded_preds(
        model_id,
        image_paths,
        objects,
        predicates,
        max_tokens,
        temperature,
        seed,
    )
    goal_response = _generate_grounded_preds(
        model_id,
        instruction,
        objects,
        predicates,
        max_tokens,
        temperature,
        seed,
    )
    
    # Assemble problem using the generated predicates
    return assemble_pddl_problem(
        init_response,
        goal_response,
        objects,
        gt_domain,
        gt_problem,
    )
