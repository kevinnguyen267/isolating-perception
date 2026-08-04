from modes import (
    formalizer,
    perceiver,
    planner,
)

MODE_REGISTRY: dict[str, dict] = {
    "formalizer": {
        "kind": "formalizer",
        "module": formalizer,
    },
    "perceiver": {
        "kind": "formalizer",
        "module": perceiver,
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
