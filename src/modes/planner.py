"""VLM-as-planner"""

from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections
from utils.vlm import image_block


def build_prompt(
    domain_text: str,
    init_paths: List[Path],
    goal_paths: List[Path],
) -> List[dict]:
    """Return prompt for generating a plan (sequence of actions) to solve the task."""
    domain = extract_domain_sections(domain_text)

    return [
        {
            "type": "text",
            "text": (
                "Assume the following two images show the exact same physical setup (current state), and there are exactly 6 blocks: red, orange, yellow, green, blue, purple. "
                "It is possible that a block is not visible in either image.\n\n"
            ),
        },
        *(image_block(p) for p in init_paths),
        {
            "type": "text",
            "text": (
                "Assume the following two images show the exact same physical setup (target state), and there are exactly 6 blocks: red, orange, yellow, green, blue, purple. "
                "It is possible that a block is not visible in either image.\n\n"
            ),
        },
        *(image_block(p) for p in goal_paths),
        {
            "type": "text",
            "text": (f"Actions:\n{', '.join(sorted(domain['actions']))}"),
        },
        {
            "type": "text",
            "text": "Determine the actions that achieve the target state from the current state and list them enclosed in triple backticks in the format (action arg1 arg2 ...).",
        },
    ]
