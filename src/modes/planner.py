"""VLM-as-planner"""

from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections
from utils.vlm import image_block

def build_prompt(
    objects: list[set[str]],
    domain_text: str,
    image_paths: List[Path],
    instruction: str,
) -> List[dict]:
    """Return prompt for generating a plan (sequence of actions) to solve the task."""
    domain = extract_domain_sections(domain_text)
    all_objects = set().union(*objects)
    
    return [
        {
            "type": "text",
            "text": (
                "Given images of the current state of a scene from different views, an instruction that specifies the target state, a set of objects, and a set of actions, "
                "determine the actions that achieve the target state from the current state."
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(all_objects))}\n\n"
                f"Actions:\n{', '.join(sorted(domain['actions']))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the actions that achieve the target state from the current state, list them enclosed in triple backticks in the format (action arg1 arg2 ...).",
        },
    ]
