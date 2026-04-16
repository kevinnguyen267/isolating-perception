from modes import (
    formalizer_1,
    formalizer_2,
    formalizer_3,
    formalizer_4,
    formalizer_5,
    formalizer_6,
    planner_1,
    planner_2,
    planner_3,
)

MODE_REGISTRY: dict[str, dict] = {
    "formalizer-1": {
        "kind": "formalizer",
        "module": formalizer_1,
        "description": "Formalizer variant 1",
    },
    "formalizer-2": {
        "kind": "formalizer",
        "module": formalizer_2,
        "description": "Formalizer variant 2",
    },
    "formalizer-3": {
        "kind": "formalizer",
        "module": formalizer_3,
        "description": "Formalizer variant 3",
    },
    "formalizer-4": {
        "kind": "formalizer",
        "module": formalizer_4,
        "description": "Formalizer variant 4",
    },
    "formalizer-5": {
        "kind": "formalizer",
        "module": formalizer_5,
        "description": "Formalizer variant 5",
    },
    "formalizer-6": {
        "kind": "formalizer",
        "module": formalizer_6,
        "description": "Formalizer variant 6",
    },
    "planner-1": {
        "kind": "planner",
        "module": planner_1,
        "description": "Planner variant 1",
    },
    "planner-2": {
        "kind": "planner",
        "module": planner_2,
        "description": "Planner variant 2",
    },
    "planner-3": {
        "kind": "planner",
        "module": planner_3,
        "description": "Planner variant 3",
    },
}

ALL_MODES = list(MODE_REGISTRY.keys())


def get_mode(name: str) -> dict:
    return MODE_REGISTRY[name]
