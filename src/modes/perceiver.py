from pathlib import Path
from typing import List

from utils.parse import extract_normalized_problem
from utils.vlm import image_block


def build_grounded_prompt(
    domain_text: str,
    problem_text: str,
    image_paths: List[Path],
    dataset: str,
) -> List[dict]:
    """Return prompt for describing the scene of the provided image as vertical stacks."""
    objects = extract_normalized_problem(problem_text)[2]
    naming_hint = "\n\n"
    if "(blue_block_1 - block)" in objects:
        naming_hint = "\nFor example, blue_block_1 refers to the blue colored block with the number '1' on it.\n\n"

    return [
        {
            "type": "text",
            "text": (
                "You are given a list of objects and two images of the same physical scene from different camera views."
            ),
        },
        {
            "type": "text",
            "text": (f"Objects:\n{', '.join(sorted(objects))}" f"{naming_hint}"),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                "First, list out the objects in each image.\n"
                f"Next, create a mapping for each image in the following format for every vertical stack in that image:\n"
                "<bottom object>, <object above>, <object above>, ..., <top object>\n"
                "For each mapping, add a line for the robot in the following format:\n"
                "<robot>: <object held, or 'none'> where 'none' indicates that the robot is not holding any object or the robot is not visible in the image."
            ),
        },
        {
            "type": "text",
            "text": (
                "Finally, output the mapping for the first image enclosed in <image1> and </image1> tags, "
                "and the mapping for the second image enclosed in <image2> and </image2> tags."
            ),
        },
    ]
