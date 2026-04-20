"""VLM-as-formalizer (intermediate semi-symbolic representation)"""

from pathlib import Path
from typing import List

from modes._shared_formalizer import build_goal_prompt  # noqa: F401
from utils.parse import extract_domain_sections
from utils.vlm import image_block


def build_init_prompts(
    objects: list[set[str]],
    domain_text: str,
    image_paths: List[Path],
) -> List[List[dict]]:
    """Return prompt for generating an intermediate scene graph for each image in the initial state.

    - This mode returns a multi-element list (one per image) of prompts (downstream merge required).
    """
    domain = extract_domain_sections(domain_text)

    return [
        (
            [
                {
                    "type": "text",
                    "text": (
                        "Given an image of a scene, a set of objects, and a set of predicates, generate a scene graph.\n\n"
                        "Hints:\n"
                        "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                        "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
                    ),
                },
                image_block(image_paths[i]),
                {
                    "type": "text",
                    "text": (
                        f"Objects:\n{', '.join(sorted(objects[i]))}\n\n"
                        f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
                    ),
                },
                {
                    "type": "text",
                    "text": "Enclose the generated scene graph in triple backticks.",
                },
            ]
        )
        for i in range(len(image_paths))
    ]


def build_merge_prompt(
    objects: list[set[str]],
    domain_text: str,
    image_paths: List[Path],
    scene_graphs: List[set],
) -> List[dict]:
    """Return prompt for merging the intermediate scene graphs into a single set of grounded predicates."""
    domain = extract_domain_sections(domain_text)
    all_objects = set().union(*objects)

    observations = "\n".join(
        f"Observation {i + 1}: {', '.join(sorted(preds))}"
        for i, preds in enumerate(scene_graphs)
    )

    return [
        {
            "type": "text",
            "text": (
                "Given multiple scene graphs, each extracted from a different view of the same scene, "
                "merge them into a single set of true grounded predicates that are true of the scene, reconciling overlaps and disagreements across views.\n\n"
                "Hints:\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Scene graphs from each observation:\n{observations}\n\n"
                f"Objects: {', '.join(sorted(all_objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the true grounded predicates, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]
