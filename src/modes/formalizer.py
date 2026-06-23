from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections, extract_normalized_problem
from utils.vlm import image_block


def build_grounded_prompt(
    domain_text: str,
    problem_text: str,
    image_paths: List[Path],
) -> List[dict]:
    """Return prompt for directly generating the grounded predicates from provided images."""
    domain = extract_domain_sections(domain_text)
    objects = extract_normalized_problem(problem_text)[2]

    return [
        {
            "type": "text",
            "text": (
                "You are a scene formalizer. You are given a list of objects, a list of predicates, "
                "and two images of the same physical scene from different camera views.\n\n"
                "Output the grounded predicates that are true in the scene.\n\n"
                "Hints:\n"
                "- If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "- The predicate (on ?x - block ?y - block) is defined as block x is on block y.\n"
                "- It is possible that a block is not visible in either image, but it still exists in the scene.\n"
            ),
        },
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": "List the true grounded predicates enclosed in a single triple-backtick block, each in the format (predicate arg1 arg2 ...).",
        },
    ]