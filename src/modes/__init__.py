from modes import (
    formalizer_direct,
    formalizer_int_pddl,
    formalizer_int_sg,
    planner,
)

MODE_REGISTRY: dict[str, dict] = {
    "formalizer-direct": {
        "kind": "formalizer",
        "module": formalizer_direct,
    },
    "formalizer-intermediate-sg": {
        "kind": "formalizer",
        "module": formalizer_int_sg,
    },
    "formalizer-intermediate-pddl": {
        "kind": "formalizer",
        "module": formalizer_int_pddl,
    },
    "planner": {
        "kind": "planner",
        "module": planner,
    },
}

for mode_name, mode_config in MODE_REGISTRY.items():
    assert "kind" in mode_config
    assert "module" in mode_config
    assert mode_config["kind"] in {"formalizer", "planner"}

ALL_MODES = list(MODE_REGISTRY.keys())


def get_mode(name: str) -> dict:
    return MODE_REGISTRY[name]
