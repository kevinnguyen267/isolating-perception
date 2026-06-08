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

    return [
        {
            "type": "text",
            "text": (
                "Assume these two images show the exact same physical setup, and there are exactly 6 blocks: red, orange, yellow, green, blue, purple. "
                "It is possible that a block is not visible in either image.\n\n"
                "Hints:\n"
                "- If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "- The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (f"Predicates:\n{', '.join(sorted(domain['predicates']))}"),
        },
        {
            "type": "text",
            "text": "Determine the true grounded predicates and list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]
