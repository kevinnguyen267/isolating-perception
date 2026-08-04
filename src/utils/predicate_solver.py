from collections import Counter

from utils.parse import ALIAS_MAP

# Shared internals of the placement encoding; see spatial_solver for their contracts.
from utils.spatial_solver import (
    _ABOVE,
    _BELOW,
    _NONE_VALUES,
    _ROBOT_OBJECT,
    _Placement,
    _best_supported_model,
)

# Arity each predicate must have to be read as a claim. A response also carries prose,
# headers, and malformed lines; those state nothing about the scene, so they are dropped.
_ARITY = {
    "on": 2,
    "ontable": 1,
    "clear": 1,
    "handempty": 1,
    "handfull": 1,
    "holding": 1,
}

# One `(on X Y)` claim has to outweigh one `(clear Y)` claim from a disagreeing view: an
# empty cell is usually implied by a stack line rather than observed (see `stack_solver`),
# so it is the weaker evidence. spatial_solver adds one soft constraint per relation and
# one per empty cell, weighted by exactly these numbers, so the ratio is set here -- the
# empty-cell evidence is only ever meant to break otherwise symmetric ties.
_ON_WEIGHT = 2
_EMPTY_WEIGHT = 1

# No view said anything about the robot, as distinct from a view that said the hand is
# empty. Only the latter is a vote.
_NO_VOTE = object()


def parse_predicates(lines: list[str]) -> list[list[str]]:
    """Parse `(pred arg ...)` lines into `[pred, *args]`, with aliases normalized.

    Lines that are not a known predicate at its expected arity are skipped. Aliases are
    resolved here rather than downstream in :func:`normalize_problem`, because the views
    vote against each other: `red_1` from one view and `red_block_1` from another have to
    be the same object before the solver counts their claims.
    """
    parsed = []
    for line in lines:
        tokens = line.strip().strip("()").split()
        if not tokens:
            continue
        pred, args = tokens[0], tokens[1:]
        if len(args) != _ARITY.get(pred, -1):
            continue
        parsed.append([pred] + [ALIAS_MAP.get(a, a) for a in args])
    return parsed


def _collect_claims(
    views: list[list[str]],
) -> tuple[Counter[tuple[str, str]], Counter[tuple[str, str]], set[str], Counter]:
    """Tally every view's predicates into solver input.

    Returns: (weights, empty_obs, subjects, held_votes) where `weights` maps an
    ``(upper, lower)`` relation to its claim support, `empty_obs` maps an
    ``(object, direction)`` cell to the evidence that it is empty, `subjects` is every
    block named, and `held_votes` counts each view's answer for what the robot holds.
    """
    weights: Counter[tuple[str, str]] = Counter()
    empty_obs: Counter[tuple[str, str]] = Counter()
    subjects: set[str] = set()
    held_votes: Counter[str | None] = Counter()

    for view in views:
        # A view that names no object it holds but reports `handfull` abstains: it says
        # the hand is not empty without saying what fills it, which no vote can express.
        held = _NO_VOTE
        for pred, *args in parse_predicates(view):
            if pred == "on":
                upper, lower = args
                subjects.update((upper, lower))
                weights[(upper, lower)] += _ON_WEIGHT
            elif pred in ("ontable", "clear"):
                subjects.add(args[0])
                direction = _BELOW if pred == "ontable" else _ABOVE
                empty_obs[(args[0], direction)] += _EMPTY_WEIGHT
            elif pred == "holding":
                # `holding` names an object, so it beats a contradicting `handempty`.
                held = args[0]
            elif pred == "handempty" and held is _NO_VOTE:
                held = None
        if held is not _NO_VOTE:
            held_votes[held] += 1

    return weights, empty_obs, subjects, held_votes


def _resolve_held(held_votes: Counter) -> str | None:
    """Resolve the views' votes into the single object being held.

    Each view answers for itself, so they can disagree. The most-voted answer wins; a tie
    falls back to an empty hand, as does an input with no votes at all.
    """
    if not held_votes:
        return None

    (winner, votes), *rest = held_votes.most_common()
    if rest and rest[0][1] == votes:
        return None  # tied views; assume the hand is empty
    return None if winner in _NONE_VALUES else winner


def predicates_to_pddl(views: list[list[str]]) -> set[str]:
    """Ground several views' predicates into one physically possible set of facts.

    Args:
        views: One list of raw `(pred arg ...)` lines per view of the same scene.

    Returns:
        The Blocksworld facts of the placement satisfying the best-supported claims:
        `(on X Y)` / `(ontable X)` for what each block rests on, `(clear X)` for a block
        with nothing above it, and `(handempty <robot>)` or `(handfull <robot>)` plus
        `(holding X)` for the robot. Blocks no view mentioned stay absent, so a block
        every view dropped stays dropped. A held block is detached from the stack graph:
        it gets no facts of its own, and any block claimed to rest on it becomes
        `ontable` instead.
    """
    weights, empty_obs, subjects, held_votes = _collect_claims(views)
    held = _resolve_held(held_votes)
    robot_facts = (
        {f"(handempty {_ROBOT_OBJECT})"}
        if held is None
        else {f"(handfull {_ROBOT_OBJECT})", f"(holding {held})"}
    )

    # Every block named as a subject (even one only ever seen isolated) or as the endpoint
    # of a relation gets a cell.
    objects = sorted(subjects | {o for pair in weights for o in pair})
    if not objects:
        return robot_facts

    above_of: dict[str, str] = {}
    below_of: dict[str, str] = {}
    if weights:
        placement = _Placement(objects)
        model = _best_supported_model(placement, weights, empty_obs)
        if model is None:
            # Distinct-cell constraints are always satisfiable (spread the objects out),
            # so the only realistic cause is a timeout that expired before the first model.
            print(
                f"  [predicate_solver] no model for {len(objects)} objects; "
                "no relations resolved"
            )
            return robot_facts

        for upper, lower in weights:
            if model.eval(placement.stacked(upper, lower), model_completion=True):
                above_of[lower] = upper
                below_of[upper] = lower

    facts = set(robot_facts)
    for obj in objects:
        if obj == held:
            continue
        below = below_of.get(obj)
        if below is None or below == held:
            facts.add(f"(ontable {obj})")
        else:
            facts.add(f"(on {obj} {below})")
        above = above_of.get(obj)
        if above is None or above == held:
            facts.add(f"(clear {obj})")
    return facts
