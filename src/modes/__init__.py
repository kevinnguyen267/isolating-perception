from modes import (
    formalizer,
    formalizer_priors,
    perceiver,
    planner,
    planner_priors,
)

MODE_REGISTRY: dict[str, dict] = {
    "formalizer": {
        "kind": "formalizer",
        "module": formalizer,
    },
    "formalizer_priors": {
        "kind": "formalizer",
        "module": formalizer_priors,
    },
    "perceiver": {
        "kind": "formalizer",
        "module": perceiver,
    },
    "planner": {
        "kind": "planner",
        "module": planner,
    },
    "planner_priors": {
        "kind": "planner",
        "module": planner_priors,
    },
}

for mode_name, mode_config in MODE_REGISTRY.items():
    assert "kind" in mode_config
    assert "module" in mode_config
    assert mode_config["kind"] in {"formalizer", "planner"}

ALL_MODES = list(MODE_REGISTRY.keys())


def get_mode(name: str) -> dict:
    return MODE_REGISTRY[name]
