from pathlib import Path
from typing import List

from utils.parse import (
    create_problem_from_sections,
    extract_normalized_problem,
    extract_output_from_response,
    parse_section,
)
from utils.vlm import (
    generate_response,
    image_block,
)


def _build_grounding_prompt_from_imgs(
    objects: set[str],
    predicates: set[str],
    grounded_preds: set[str],
    image_paths: List[Path],
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from the images, given the set of objects and predicates."""
    return [
        {
            "type": "text",
            "text": (
                "You are given a scene, a set of objects, a set of predicates, and a set of grounded predicates.\n\n"
                "Ensure the grounded predicates are consistent with the scene and no true grounded predicates were omitted.\n\n"
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
                f"Grounded Predicates:\n{', '.join(sorted(grounded_preds))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, determine the true grounded predicates and list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]


def regenerate_pddl_problem(
    model_id: str,
    dataset_problem_dir: Path,
    gt_domain: str,
    gen_problem: str,
    max_tokens: int,
    temperature: float,
    seed: int,
) -> tuple[str, str, str]:
    """Regenerates the init section of the PDDL problem using the VLM, while keeping the objects and goal predicates fixed.

    Returns: (problem, init_response, init_response_extracted)
    """
    # Extract all other sections from generated problem
    problem_name, domain_name, objects, init_preds, goal_preds = (
        extract_normalized_problem(gen_problem)
    )

    # Extract predicates from the domain
    predicates = parse_section(gt_domain, ":predicates")
    predicates = set(p.strip("()") for p in predicates)

    # Extract image paths and instruction from the dataset directory
    image_paths = sorted((dataset_problem_dir / "observations").glob("*.*"))
    if not image_paths:
        raise FileNotFoundError(
            f"No images found in {dataset_problem_dir / 'observations'}"
        )

    # Build context for re-prompting VLM
    prompt = _build_grounding_prompt_from_imgs(
        objects, predicates, init_preds, image_paths
    )

    # Re-prompt the VLM to regenerate grounded predicates for the init section
    init_response = generate_response(
        model_id,
        prompt,
        max_tokens,
        temperature,
        seed,
    )
    regen_init_preds, regen_init_preds_str = extract_output_from_response(init_response)

    # Build problem
    problem = create_problem_from_sections(
        problem_name,
        domain_name,
        objects,
        regen_init_preds,
        goal_preds,
    )

    return (
        problem,
        init_response,
        regen_init_preds_str,
    )
