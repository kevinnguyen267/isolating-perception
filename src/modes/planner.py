from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections, extract_normalized_problem
from utils.vlm import image_block


def build_prompt(
    domain_text: str,
    problem_text: str,
    init_paths: List[Path],
    goal_paths: List[Path],
) -> List[dict]:
    """Return prompt for generating a plan (sequence of actions) to solve the task."""
    domain = extract_domain_sections(domain_text)
    objects = extract_normalized_problem(problem_text)[2]

    return [
        {
            "type": "text",
            "text": (
                "You are a task planner. You are given a list of objects, a list of actions, "
                "and two states: a current state and a target state. Each state is shown as two "
                "images of the same physical scene from different camera views.\n\n"
                "Output the ordered sequence of actions that transforms the current state into the "
                "target state.\n\n"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Actions:\n{', '.join(sorted(domain['actions']))}"
            ),
        },
        {
            "type": "text",
            "text": (
                "The following two images show the same physical setup from different views "
                "(the CURRENT state). It is possible that a block is not visible in "
                "either image, but it still exists in the scene."
            ),
        },
        *(image_block(p) for p in init_paths),
        {
            "type": "text",
            "text": (
                "The following two images show the same physical setup from different views "
                "(the TARGET state). It is possible that a block is not visible in "
                "either image, but it still exists in the scene."
            ),
        },
        *(image_block(p) for p in goal_paths),
        {
            "type": "text",
            "text": (f"Actions:\n{', '.join(sorted(domain['actions']))}"),
        },
        {
            "type": "text",
            "text": "List the ordered sequence of actions that achieves the target state from "
            "the current state, one action per line, enclosed in a single triple-backtick block, "
            "each in the format (action arg1 arg2 ...).",
        },
    ]
