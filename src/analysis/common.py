"""Helpers shared by the analysis scripts."""

import re
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/

from utils.parse import extract_normalized_problem

TABLE = "<table>"
HELD = "<held>"
MISSING = "<missing>"

_ACTION_RE = re.compile(r"\(([a-zA-Z][\w-]*)((?:\s+[\w-]+)*)\s*\)")


def latest_run(model_dir: Path, exclude: list[str] = ()) -> Path | None:
    """Most recent run (by timestamp) under `model_dir` that has an eval_report.json.

    Runs whose path matches any glob in `exclude` are skipped.
    """
    runs = sorted(
        run
        for run in model_dir.glob("*/")
        if (run / "eval_report.json").exists()
        and not any(fnmatch(str(run), pattern) for pattern in exclude)
    )
    return runs[-1] if runs else None


def parse_gt(gt_text: str) -> tuple[set[str], str, set[str], set[str]]:
    """Return (blocks, robot, init facts, goal facts) of a ground-truth problem."""
    _, _, objects, init, goal = extract_normalized_problem(gt_text)
    blocks, robot = set(), "robot_1"
    for obj in objects:
        name, _, kind = obj.strip("()").partition(" - ")
        if kind.strip() == "block":
            blocks.add(name.strip())
        elif kind.strip() == "robot":
            robot = name.strip()
    return blocks, robot, init, goal


def support_map(facts: set[str], blocks: set[str]) -> dict[str, str]:
    """Map each block to what it rests on: a block, TABLE, HELD, or MISSING if unplaced.

    An `(on X Y)` fact takes precedence over a conflicting `(ontable X)`.
    """
    support = {b: MISSING for b in blocks}
    for fact in sorted(facts):
        tokens = fact.strip("() ").split()
        if len(tokens) < 2 or tokens[1] not in support:
            continue
        pred, block, args = tokens[0].lower(), tokens[1], tokens[1:]
        if pred == "on" and len(args) == 2:
            support[block] = args[1]
        elif pred == "ontable" and len(args) == 1 and support[block] == MISSING:
            support[block] = TABLE
        elif pred == "holding" and len(args) == 1:
            support[block] = HELD
    return support


def plan_implied_facts(
    plan_text: str, blocks: set[str], robot: str
) -> tuple[set[str], set[str]]:
    """Recover the init and goal facts a plan commits to (Appendix D).

    The first action to touch a block reveals where the plan assumed it started:
    `(unstack X Y)` implies `(on X Y)` and `(pick-up X)` implies `(ontable X)`, along with
    `(clear X)` and an empty hand. Executing the plan from there gives its goal state.
    Blocks the plan never touches appear in neither state.
    """
    support = {b: MISSING for b in blocks}
    clear: dict[str, bool | None] = {b: None for b in blocks}
    hand_empty: bool | None = None
    init: set[str] = set()

    def assume(block: str, fact: str, value: str) -> None:
        if support[block] == MISSING:
            init.add(fact)
            support[block] = value

    def assume_clear(block: str) -> None:
        if clear[block] is None:
            init.add(f"(clear {block})")
            clear[block] = True

    def assume_hand_empty() -> None:
        nonlocal hand_empty
        if hand_empty is None:
            init.add(f"(handempty {robot})")
            hand_empty = True

    for match in _ACTION_RE.finditer(plan_text):
        action = match.group(1).lower()
        args = [a for a in match.group(2).split() if a in blocks]
        if action == "unstack" and len(args) == 2:
            x, y = args
            assume(x, f"(on {x} {y})", y)
            assume_clear(x)
            assume_hand_empty()
            support[x], clear[x], clear[y], hand_empty = HELD, False, True, False
        elif action == "pick-up" and len(args) == 1:
            (x,) = args
            assume(x, f"(ontable {x})", TABLE)
            assume_clear(x)
            assume_hand_empty()
            support[x], clear[x], hand_empty = HELD, False, False
        elif action == "put-down" and len(args) == 1:
            (x,) = args
            support[x], clear[x], hand_empty = TABLE, True, True
        elif action == "stack" and len(args) == 2:
            x, y = args
            assume_clear(y)
            support[x], clear[x], clear[y], hand_empty = y, True, False, True

    goal: set[str] = set()
    for b in blocks:
        if support[b] == TABLE:
            goal.add(f"(ontable {b})")
        elif support[b] == HELD:
            goal.add(f"(holding {b})")
        elif support[b] != MISSING:
            goal.add(f"(on {b} {support[b]})")
        if clear[b]:
            goal.add(f"(clear {b})")
    if hand_empty is not None:
        goal.add(f"(handempty {robot})" if hand_empty else f"(handfull {robot})")
    return init, goal


def predicted_states(
    problem_dir: Path, mode: str, blocks: set[str], robot: str
) -> tuple[set[str], set[str]] | None:
    """Init and goal facts a mode predicted for one problem, or None if it wrote none.

    Planner states are recovered from plan.txt; every other mode wrote problem.pddl.
    """
    if mode.startswith("planner"):
        plan = problem_dir / "plan.txt"
        return plan_implied_facts(
            plan.read_text() if plan.exists() else "", blocks, robot
        )
    problem = problem_dir / "problem.pddl"
    if not problem.exists():
        return None
    _, _, _, init, goal = extract_normalized_problem(problem.read_text())
    return init, goal
