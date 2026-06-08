from modes import (
    formalizer,
    formalizer_direct,
    formalizer_direct_explicit_angles,
    formalizer_direct_explicit_angles_simple,
    planner,
    planner_explicit_angles,
    planner_explicit_angles_simple,
)

MODE_REGISTRY: dict[str, dict] = {
    "formalizer": {
        "kind": "formalizer",
        "module": formalizer,
    },
    "formalizer-direct": {
        "kind": "formalizer",
        "module": formalizer_direct,
    },
    "planner": {
        "kind": "planner",
        "module": planner,
    },
    "formalizer-direct-explicit-angles": {
        "kind": "formalizer",
        "module": formalizer_direct_explicit_angles,
    },
    "planner-explicit-angles": {
        "kind": "planner",
        "module": planner_explicit_angles,
    },
    "formalizer-direct-explicit-angles-simple": {
        "kind": "formalizer",
        "module": formalizer_direct_explicit_angles_simple,
    },
    "planner-explicit-angles-simple": {
        "kind": "planner",
        "module": planner_explicit_angles_simple,
    },
}

for mode_name, mode_config in MODE_REGISTRY.items():
    assert "kind" in mode_config
    assert "module" in mode_config
    assert mode_config["kind"] in {"formalizer", "planner"}

ALL_MODES = list(MODE_REGISTRY.keys())


def get_mode(name: str) -> dict:
    return MODE_REGISTRY[name]
