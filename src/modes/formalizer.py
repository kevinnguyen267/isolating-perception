from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections
from utils.vlm import image_block


def build_grounded_prompt(
    domain_text: str,
    image_paths: List[Path],
) -> List[dict]:
    """Return prompt for directly generating the grounded predicates from provided images."""
    domain = extract_domain_sections(domain_text)

    all_objects = {
        "red_block",
        "orange_block",
        "yellow_block",
        "green_block",
        "blue_block",
        "purple_block",
    }
    return [
        {
            "type": "text",
            "text": (
                "Given images from different views of the same scene, a set of objects, and a set of predicates, determine the true grounded predicates.\n\n"
                "Hints:\n"
                "- If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "- The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Objects:\n{', '.join(sorted(all_objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the true grounded predicates, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]
