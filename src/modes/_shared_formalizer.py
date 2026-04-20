from typing import List

from utils.parse import extract_domain_sections


def build_goal_prompt(
    objects: list[set[str]],
    domain_text: str,
    instruction: str,
) -> List[dict]:
    """Return prompt for generating the grounded predicates in the goal state."""
    domain = extract_domain_sections(domain_text)
    all_objects = set().union(*objects)

    return [
        {
            "type": "text",
            "text": (
                "Given an instruction, a set of objects, and a set of predicates, determine the true grounded predicates.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is mentioned in the instruction, assume the gripper is empty and not holding any object.\n"
                "The predicate (on ?x - block ?y - block) is defined as block x is on block y.\n\n"
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(all_objects))}\n\n"
                f"Predicates:\n{', '.join(sorted(domain['predicates']))}"
            ),
        },
        {
            "type": "text",
            "text": "After determining the true grounded predicates, list them enclosed in triple backticks in the format (predicate arg1 arg2 ...).",
        },
    ]
