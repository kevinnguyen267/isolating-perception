from pathlib import Path
from typing import List

from utils.parse import extract_domain_sections, extract_normalized_problem
from utils.vlm import image_block

# Structural guidance added by the `*_priors` modes.
PHYSICAL_PRIORS = (
    "All blocks are the same physical size, support is vertical and discrete, and a block "
    "can only be supported by one other block or the table.\n\n"
)


def build_prompt(
    domain_text: str,
    problem_text: str,
    init_paths: List[Path],
    goal_paths: List[Path],
    dataset: str,
    priors: bool = False,
) -> List[dict]:
    """Return prompt for generating a plan (sequence of actions) to solve the task.

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
            "Hints:\n- Exactly one object is hidden from view in both images. The hidden object's location can be "
            "inferred from the visible objects.\n\n"
        )

    return [
        {
            "type": "text",
            "text": (
                "You are given a list of objects, a list of actions, "
                "and two states: a current state and a target state. Each state is shown as two "
                "images of the same physical scene from different camera views.\n\n"
                f"{PHYSICAL_PRIORS if priors else ''}"
                "Output the ordered sequence of actions that transforms the current state into the "
                "target state.\n\n"
                f"{hidden_object_hint}"
                f"Objects:\n{', '.join(sorted(objects))}"
                f"{naming_hint}"
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
