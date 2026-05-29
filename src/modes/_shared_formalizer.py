from typing import List

from modes._utils import get_hints
from utils.parse import extract_domain_sections


def build_goal_prompt(
    objects: list[set[str]],
    domain_text: str,
    instruction: str,
) -> List[dict]:
    """Return prompt for generating the grounded predicates in the goal state."""
    domain = extract_domain_sections(domain_text)
    all_objects = set().union(*objects)
    
    hints = get_hints(domain["name"], img=False)  # type: ignore
    if hints:
        hints += "\n\n"

    return [
        {
            "type": "text",
            "text": (
                "Given an instruction, a set of objects, and a set of predicates, determine the true grounded predicates after the instruction is executed.\n\n"
                f"{hints}"  # type: ignore
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(all_objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the true grounded predicates after the instruction is executed, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]
