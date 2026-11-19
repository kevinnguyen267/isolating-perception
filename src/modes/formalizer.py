from pathlib import Path
from typing import List

from modes.planner import PHYSICAL_PRIORS
from utils.parse import extract_domain_sections, extract_normalized_problem
from utils.vlm import image_block


def build_grounded_prompt(
    domain_text: str,
    problem_text: str,
    image_paths: List[Path],
    dataset: str,
    priors: bool = False,
) -> List[dict]:
    """Return prompt for directly generating the grounded predicates from provided images.

    With `priors`, the prompt also states the physical constraints of the scene
    (`PHYSICAL_PRIORS`).
    """
    domain = extract_domain_sections(domain_text)
    objects = extract_normalized_problem(problem_text)[2]
    naming_hint = "\n\n"
    if "(blue_block_1 - block)" in objects:
        naming_hint = "\nFor example, blue_block_1 refers to the blue colored block with the number '1' on it.\n\n"
    hidden_object_hint = ""
    if dataset == "blocksworld_hidden":
        hidden_object_hint = (
            "\n- Exactly one object is hidden from view in both images. The hidden object's location can be "
            "inferred from the visible objects."
        )

    return [
        {
            "type": "text",
            "text": (
                "You are a scene formalizer. You are given a list of objects, a list of predicates, "
                "and two images of the same physical scene from different camera views.\n\n"
                f"{PHYSICAL_PRIORS if priors else ''}"
                "Output the grounded predicates that are true in the scene.\n\n"
                "Hints:\n"
                "- If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object."
                f"{hidden_object_hint}"
            ),
        },
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(objects))}"
                f"{naming_hint}"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": "List the true grounded predicates enclosed in a single triple-backtick block, each in the format (predicate arg1 arg2 ...).",
        },
    ]
