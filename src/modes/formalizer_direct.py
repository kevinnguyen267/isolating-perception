"""VLM-as-formalizer (direct)"""

from pathlib import Path
from typing import List

from modes._shared_formalizer import build_goal_prompt  # noqa: F401
from modes._utils import get_hints
from utils.parse import extract_domain_sections
from utils.vlm import image_block


def build_init_prompts(
    objects: list[set[str]],
    domain_text: str,
    image_paths: List[Path],
    text_paths: List[Path],
) -> List[List[dict]]:
    """Return prompt for directly generating the grounded predicates from all images in the initial state.

    - This mode returns a single-element list containing the prompt (no downstream merge required).
    """
    domain = extract_domain_sections(domain_text)
    all_objects = set().union(*objects)

    if not text_paths:
        return [
            [
                {
                    "type": "text",
                    "text": (
                        "Given images from different views of the same scene, a set of objects, and a set of predicates, determine the true grounded predicates.\n\n"
                        f"{get_hints(domain['name'])}"  # type: ignore
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
        ]
    else:
        if len(image_paths) != 2 or len(text_paths) != 1:
            raise ValueError(
                f"Expected exactly two images and one text file when text paths are provided, but got {len(image_paths)} images and {len(text_paths)} text files."
            )
        text = text_paths[0].read_text()
        return [
            [
                {
                    "type": "text",
                    "text": (
                        "Given an image and additional textual information of the same scene, a set of objects, and a set of predicates, determine the true grounded predicates.\n\n"
                        f"{get_hints(domain['name'])}"  # type: ignore
                    ),
                },
                image_block(image_paths[0]),
                {
                    "type": "text",
                    "text": (
                        f"Additional information:\n{text}\n\n"
                        f"Objects:\n{', '.join(sorted(all_objects))}\n\n"
                        f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
                    ),
                },
                {
                    "type": "text",
                    "text": "After determining the true grounded predicates, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
                },
            ]
        ]
