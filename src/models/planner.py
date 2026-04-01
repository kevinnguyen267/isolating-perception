from pathlib import Path
from typing import List

from utils.parse import extract_output_from_response
from utils.vlm import generate_response, image_block


def _build_prompt(
    objects: set[str],
    actions: set[str],
    image_paths: List[Path],
    instruction: str,
) -> List[dict]:
    """Builds a prompt to generate grounded predicates from the images, given the set of objects and predicates."""
    return [
        {
            "type": "text",
            "text": (
                "You are given a scene of the current state, an instruction that specifies the goal state, a set of objects, and a set of actions.\n"
                "Describe the objects, their positions, and their spatial relationships in both the current and goal states.\n"
                "Every object exists exactly once and is visible. If your analysis contradicts this statement, re-examine the scene and pay closer attention to the object(s) contributing to the contradiction.\n\n"
                "Hints:\n"
                "If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
            ),
        },
        *(image_block(p) for p in image_paths),
        {
            "type": "text",
            "text": (
                f"Instruction:\n{instruction}\n\n"
                f"Objects:\n{', '.join(sorted(objects))}\n\n"
                f"Actions:\n{', '.join(sorted(actions))}\n\n"
            ),
        },
        {
            "type": "text",
            "text": "First, complete your detailed analysis. Then, determine the actions that achieve the goal from the current state and list them enclosed in triple backticks in the format (action arg1 arg2 ...).",
        },
    ]


def build_planner_prompt(
    dataset_problem_dir: Path,
) -> List[dict]:
    """Build the planner prompt.

    Returns: prompt (list of message content blocks)
    """
    # TODO: Placeholder: given objects for blocksworld_real
    objects = set(
        [
            "robot1 - robot",
            "red_block - block",
            "orange_block - block",
            "yellow_block - block",
            "green_block - block",
            "blue_block - block",
            "purple_block - block",
        ]
    )

    # TODO: Placeholder: given objects for blocksworld_sim
    # bboxes_path = dataset_problem_dir / "annotated_bbox.json"
    # with bboxes_path.open() as f:
    #     bboxes = json.load(f)
    # object_names = set(bboxes.keys())
    # objects = set()
    # for name in object_names:
    #     objects.add(f"{name} - block")
    # object_names.add("robot1")
    # objects.add("robot1 - robot")

    # Extract image paths and instruction from the dataset directory
    image_paths = sorted((dataset_problem_dir / "observations").glob("*.*"))
    if not image_paths:
        raise FileNotFoundError(
            f"No images found in {dataset_problem_dir / 'observations'}"
        )
    try:
        instruction = (dataset_problem_dir / "instruction.txt").read_text()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"No instruction found in {dataset_problem_dir / 'instruction.txt'}"
        )

    # TODO: Placeholder: actions for blocksworld_real
    actions = {
        """(:action pick-up
            :parameters (?x - block ?robot - robot)
            :precondition (and
                (clear ?x) 
                (ontable ?x) 
                (handempty ?robot)
            )
            :effect (and
                (not (ontable ?x))
                (not (clear ?x))
                (not (handempty ?robot))
                (handfull ?robot)
                (holding ?x)
            )
        )""",
        """(:action put-down
            :parameters (?x - block ?robot - robot)
            :precondition (and 
                (holding ?x)
                (handfull ?robot)
            )
            :effect (and 
                (not (holding ?x))
                (clear ?x)
                (handempty ?robot)
                (not (handfull ?robot))
                (ontable ?x))
            )""",
        """(:action stack
            :parameters (?x - block ?y - block ?robot - robot)
            :precondition (and
                (holding ?x) 
                (clear ?y)
                (handfull ?robot)
            )
            :effect (and 
                (not (holding ?x))
                (not (clear ?y))
                (clear ?x)
                (handempty ?robot)
                (not (handfull ?robot))
                (on ?x ?y)
            )
        )""",
        """(:action unstack
            :parameters (?x - block ?y - block ?robot - robot)
            :precondition (and
                (on ?x ?y)
                (clear ?x)
                (handempty ?robot)
            )
            :effect (and 
                (holding ?x)
                (clear ?y)
                (not (clear ?x))
                (not (handempty ?robot))
                (handfull ?robot)
                (not (on ?x ?y))
            )
        )""",
    }

    return _build_prompt(objects, actions, image_paths, instruction)


def generate_plan(
    model_id: str,
    dataset_problem_dir: Path,
    max_tokens: int,
    temperature: float,
    seed: int,
    quantization: bool,
) -> tuple[str, str]:
    """Generates a plan given context from the dataset.

    Returns: (plan, response)
    """
    # Build prompt
    prompt = build_planner_prompt(dataset_problem_dir)

    # Prompt the VLM to generate a plan
    response = generate_response(
        model_id,
        prompt,
        max_tokens,
        temperature,
        seed,
        quantization,
    )
    _, plan_str = extract_output_from_response(response)

    return (plan_str, response)
