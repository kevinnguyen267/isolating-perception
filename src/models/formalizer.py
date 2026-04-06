import re
from pathlib import Path
from typing import List

from utils.parse import (
    create_problem_from_sections,
    extract_output_from_response,
    parse_section,
)
from utils.vlm import image_block


def extract_dataset_info(
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


# Prompts for input type: image(s)
# - PDDL predicate grounding from multiple images in a single step (no merging)
# - PDDL predicate grounding from one image (later merged in a second step)
# - Scene graph generation from one image (later merged in a second step)


def build_grounding_prompt_imgs(
    objects: set[str],
    predicates: set[str],
    image_paths: List[Path],
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from multiple images."""
    return [
        {
            "type": "text",
            "text": (
                "You are given a scene from multiple viewpoints, a set of objects, and a set of predicates.\n"
                "Describe the objects, their positions, and their spatial relationships.\n\n"
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


def build_grounding_prompt_img(
    objects: set[str],
    predicates: set[str],
    image_path: Path,
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from a single image."""
    return [
        {
            "type": "text",
            "text": (
                "You are given a scene, a set of objects, and a set of predicates.\n"
                "Describe the objects, their positions, and their spatial relationships.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        image_block(image_path),
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


def build_scene_graph_prompt_img(
    objects: set[str],
    predicates: set[str],
    image_path: Path,
) -> List[dict]:
    """Builds a prompt to generate a scene graph from a single image."""
    return [
        {
            "type": "text",
            "text": (
                "You are given a scene, a set of objects, and a set of predicates.\n"
                "Describe the objects, their positions, and their spatial relationships.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        image_block(image_path),
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, generate a scene graph.",
        },
    ]


# Prompts for input type: instruction text
# - PDDL predicate grounding from instruction (no merging)


def build_grounding_prompt_from_instruction(
    objects: set[str],
    predicates: set[str],
    instruction: str,
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from an instruction."""
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


# Prompts for merging
# - Merging multiple lists of PDDL grounded predicates into one consistent list of PDDL grounded predicates
# - Merging multiple scene graphs into one consistent list of PDDL grounded predicates


def _extract_observations_from_responses(responses: list[str]) -> str:
    """Helper function to extract and format observations from multiple VLM responses for merging prompts."""
    observations = ""
    for i, response in enumerate(responses, 1):
        formatted = "\n".join(extract_output_from_response(response)[0])
        observations += f"Observation {i}:\n{formatted}\n\n"
    return observations


def build_merge_grounded_prompt(
    objects: set[str],
    predicates: set[str],
    per_image_responses: list[str],
) -> List[dict]:
    """Builds a prompt to merge multiple per-image predicate lists into one."""
    observations = _extract_observations_from_responses(per_image_responses)

    return [
        {
            "type": "text",
            "text": (
                "You are given multiple observations of the same scene from different viewpoints, "
                "a set of objects, and a set of predicates.\n"
                "Each observation is a list of grounded predicates generated independently from a single image.\n\n"
                "Your task is to reason about all observations and produce a single, consistent list of true grounded predicates "
                "that best represents the scene.\n"
                "Resolve any conflicts between observations by reasoning about which predicates are most likely correct.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is mentioned in any observation, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y.\n\n"
                f"{observations}"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, determine the true grounded predicates and list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]


def build_merge_scene_graph_prompt(
    objects: set[str],
    predicates: set[str],
    per_image_responses: list[str],
) -> List[dict]:
    """Builds a prompt to merge multiple per-image scene graph lists into a single list of grounded predicates."""
    observations = _extract_observations_from_responses(per_image_responses)

    return [
        {
            "type": "text",
            "text": (
                "You are given multiple observations of the same scene from different viewpoints, "
                "a set of objects, and a set of predicates.\n"
                "Each observation is a scene graph generated independently from a single image.\n\n"
                "Your task is to reason about all observations and produce a single, consistent list of true grounded predicates "
                "that best represents the scene.\n"
                "Resolve any conflicts between observations by reasoning about which predicates are most likely correct.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is mentioned in any observation, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y.\n\n"
                f"{observations}"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(predicates))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, determine the true grounded predicates and list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]


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
