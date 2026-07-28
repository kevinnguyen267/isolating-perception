import os
from collections import Counter
from itertools import combinations

from z3 import And, Context, Int, Optimize, Or, Z3Exception, unknown, unsat

_ABOVE = "above"
_BELOW = "below"
_NONE_VALUES = {"", "none", "null", "nothing"}

# Override with SPATIAL_SOLVER_TIMEOUT_MS (0 disables the cap).
_SOLVER_TIMEOUT_MS = 5 * 60 * 1000

# Subjects that name the robot rather than a block. Matched case-insensitively against the
# left-hand side of a line, so that a robot line is recognized however many fields follow.
_ROBOT_NAMES = {"robot", "robot_1", "robot_arm", "robot arm", "gripper", "arm", "hand"}
# Every dataset declares exactly one ``robot - robot`` object, so the robot facts always use
# this name regardless of what the input called it. ``ALIAS_MAP`` maps it to ``robot_1``.
_ROBOT_OBJECT = "robot"


def _split_line(line: str) -> tuple[str, str, str] | None:
    """Split ``<object>: <above>, <below>`` into ``(object, above, below)``.

    Returns ``None`` for a blank line, or for a malformed one (no ``:`` or not exactly
    two comma-separated fields).
    """
    line = line.strip()
    if not line:
        return None
    if ":" not in line:
        return None

    subject, _, rhs = line.partition(":")
    fields = [f.strip() for f in rhs.split(",")]
    if len(fields) != 2:
        return None

    above, below = fields
    below = below.split()[0] if below else "none"  # ignore extra tokens
    return subject.strip(), above, below


def _split_robot_line(line: str) -> str | None:
    """Return the object held by the robot in ``<robot>: <object held, or 'none'>``.

    Returns ``"none"`` when the robot holds nothing, and ``None`` when the line does not
    describe the robot at all (including blank and malformed lines).

    Only the first comma-separated field is read, so a line that mimics the two-field object
    shape (``robot: red_1, none``) is still understood as the robot holding ``red_1``.
    """
    line = line.strip()
    if ":" not in line:
        return None

    subject, _, rhs = line.partition(":")
    if subject.strip().lower() not in _ROBOT_NAMES:
        return None

    held = rhs.split(",")[0].strip().rstrip(".")  # the format example ends in a period
    return held.split()[0] if held else "none"  # ignore extra tokens


def partition_robot_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split raw statement lines into ``(object_lines, robot_lines)``.

    Only the object lines describe spatial relations, so only they belong in
    :func:`resolve_spatial_relations`; the robot lines go straight to
    :func:`neighbors_to_pddl`. Keeping the robot out of the solver also stops it from being
    placed in a stack, which would emit ill-typed ``on``/``ontable`` facts for it.
    """
    object_lines, robot_lines = [], []
    for line in lines:
        if _split_robot_line(line) is None:
            object_lines.append(line)
        else:
            robot_lines.append(line)
    return object_lines, robot_lines


def _parse_lines(
    lines: list[str],
) -> tuple[Counter[tuple[str, str]], set[str], Counter[tuple[str, str]]]:
    """Parse raw input lines into weighted relations, subjects, and ``none`` observations.

    Each direction is a separate relation, so ``A: B, C`` counts as one claim that ``B`` is above ``A``
    and one claim that ``C`` is below ``A``. Each claim is weighted by how many times it appears
    in the input.
    """
    weights: Counter[tuple[str, str]] = Counter()
    subjects: set[str] = set()
    none_obs: Counter[tuple[str, str]] = Counter()
    for line in lines:
        parsed = _split_line(line)
        if parsed is None:
            continue
        subject, above, below = parsed

        subjects.add(subject)
        for direction, neighbor in ((_ABOVE, above), (_BELOW, below)):
            if neighbor.lower() in _NONE_VALUES:
                none_obs[(subject, direction)] += 1
                continue
            if direction == _ABOVE:
                weights[(neighbor, subject)] += 1
            else:
                weights[(subject, neighbor)] += 1
    return weights, subjects, none_obs


class _Placement:
    """Z3 encoding that puts every object in one cell of a grid of vertical stacks.

    Each object gets a stack index and a height within that stack, so ``B`` rests directly
    on ``A`` exactly when the two share a stack and ``B`` sits one height higher. The
    methods build the constraints over those variables; they do not solve anything.
    """

    def __init__(self, objects: list[str]) -> None:
        self.ctx = Context()
        self.objects = objects
        self._stack = {o: Int(f"stack_{o}", ctx=self.ctx) for o in objects}
        self._height = {o: Int(f"height_{o}", ctx=self.ctx) for o in objects}

    def stacked(self, upper: str, lower: str):
        """Constraint: ``upper`` rests directly on ``lower``."""
        return And(
            self._stack[upper] == self._stack[lower],
            self._height[upper] == self._height[lower] + 1,
            self.ctx,
        )

    def slot_empty(self, obj: str, direction: str):
        """Constraint: no object occupies the cell directly ``direction`` of ``obj``.

        Returns ``None`` when ``obj`` is the only object, since nothing can fill the slot.
        """
        offset = 1 if direction == _ABOVE else -1
        others = [
            Or(
                self._stack[other] != self._stack[obj],
                self._height[other] != self._height[obj] + offset,
                self.ctx,
            )
            for other in self.objects
            if other != obj
        ]
        return And(others, self.ctx) if others else None

    def distinct_cells(self) -> list:
        """Constraints: no two objects share a cell."""
        return [
            Or(
                self._stack[a] != self._stack[b],
                self._height[a] != self._height[b],
                self.ctx,
            )
            for a, b in combinations(self.objects, 2)
        ]


def _reliable_objects(weights: Counter[tuple[str, str]]) -> set[str]:
    """Objects that are never party to a conflicting claim.

    An object is unreliable when the input names more than one candidate for the cell
    directly above it, or more than one for the cell directly below it (e.g. it is claimed
    to be below two different objects). Each key of ``weights`` is a distinct
    ``(upper, lower)`` pair, so counting the keys an object appears in counts its distinct
    candidates. Only objects appearing in ``weights`` are considered.
    """
    candidates_above = Counter(lower for _, lower in weights)
    candidates_below = Counter(upper for upper, _ in weights)
    return {
        o
        for o in set(candidates_above) | set(candidates_below)
        if candidates_above[o] <= 1 and candidates_below[o] <= 1
    }


def _best_supported_model(
    placement: _Placement,
    weights: Counter[tuple[str, str]],
    none_obs: Counter[tuple[str, str]],
):
    """Solve for the placement satisfying the best-supported set of claims.

    Returns the solved model, or ``None`` if the solver fails.
    """
    opt = Optimize(ctx=placement.ctx)
    if _SOLVER_TIMEOUT_MS > 0:
        opt.set("timeout", _SOLVER_TIMEOUT_MS)
    for constraint in placement.distinct_cells():
        opt.add(constraint)

    reliable = _reliable_objects(weights)
    # A bonus worth more than every claim in the input put together, so that a relation
    # anchored by a self-consistent object wins a contested slot no matter how many
    # conflicting claims oppose it.
    bonus = sum(weights.values()) + 1

    # One soft constraint per relation: its claim support, plus the bonus per reliable
    # endpoint.
    for (upper, lower), weight in weights.items():
        endorsements = (upper in reliable) + (lower in reliable)
        opt.add_soft(placement.stacked(upper, lower), weight + endorsements * bonus)

    # Negative evidence: each ``none`` observation of a slot votes (with no reliability
    # bonus) for that slot staying empty, opposing any relation that would fill it. This is
    # deliberately weak -- a single genuine claim still dominates -- so it only tips slots
    # that are otherwise a symmetric tie, toward the object seen isolated.
    for (obj, direction), count in none_obs.items():
        slot = placement.slot_empty(obj, direction)
        if slot is not None:
            opt.add_soft(slot, count)

    result = opt.check()
    if result == unsat:
        return None
    if result == unknown:
        print(
            f"  [spatial_solver] solve timed out after {_SOLVER_TIMEOUT_MS}ms "
            f"({len(placement.objects)} objects, {len(weights)} relations); "
            "using best placement found"
        )

    try:
        return opt.model()
    except Z3Exception:
        return None


def resolve_spatial_relations(lines: list[str]) -> list[str]:
    """Resolve possibly-conflicting spatial statements into consistent per-object neighbors.

    Each input line has the form
    ``<object>: <above>, <below>`` where either field may be ``none``.
    Lines may repeat or conflict; the solver finds the object placement satisfying
    the most statements (weighting each relation by how many input claims support it) and
    returns the neighbors consistent with that placement.

    Args:
        lines: Raw statement lines.

    Returns:
        One line per object, in the same format as the input,
        ``<object>: <above>, <below>``, where each field is the
        neighbor object in that direction or ``none`` if there is none.
    """
    weights, subjects, none_obs = _parse_lines(lines)
    if not weights:
        # No relations to resolve, but isolated objects still round-trip.
        return [f"{o}: none, none" for o in sorted(subjects)]

    # Every object that appears as a subject (even all-``none``) or a neighbor gets a cell.
    objects = sorted(subjects | {o for pair in weights for o in pair})

    placement = _Placement(objects)
    model = _best_supported_model(placement, weights, none_obs)
    if model is None:
        # Distinct-cell constraints are always satisfiable (spread objects out), so the only
        # realistic cause is a timeout that expired before the first model.
        print(
            f"  [spatial_solver] no model for {len(objects)} objects "
            f"(timeout={_SOLVER_TIMEOUT_MS}ms); no relations resolved"
        )
        return []

    # Reconstruct per-object neighbors from the relations the placement satisfies.
    above_of: dict[str, str] = {}
    below_of: dict[str, str] = {}
    for upper, lower in weights:
        if model.eval(placement.stacked(upper, lower), model_completion=True):
            above_of[lower] = upper
            below_of[upper] = lower

    return [
        f"{o}: {above_of.get(o, 'none')}, {below_of.get(o, 'none')}" for o in objects
    ]


def _resolve_held(robot_lines: list[str]) -> str | None:
    """Resolve possibly-conflicting robot statements into the single object being held.

    Each image contributes its own robot line, so the views can disagree. The most-observed
    answer wins; a tie falls back to an empty hand, as does an empty input.

    Returns:
        The held object, or ``None`` if the robot holds nothing.
    """
    observations: Counter[str | None] = Counter()
    for line in robot_lines:
        held = _split_robot_line(line)
        if held is None:
            continue
        observations[None if held.lower() in _NONE_VALUES else held] += 1

    if not observations:
        return None

    (winner, votes), *rest = observations.most_common()
    if rest and rest[0][1] == votes:
        return None  # tied views; assume the hand is empty
    return winner


def neighbors_to_pddl(
    lines: list[str], robot_lines: list[str] | None = None
) -> set[str]:
    """Convert resolved neighbor lines into Blocksworld facts.

    Each line in ``lines`` has the same ``<object>: <above>, <below>`` shape produced by
    :func:`resolve_spatial_relations` (either field may be ``none``). The mapping is:

      - ``below`` is a real object  -> ``(on <object> <below>)``
      - ``below`` is ``none``       -> ``(ontable <object>)``
      - ``above`` is ``none``       -> ``(clear <object>)``

    Each line in ``robot_lines`` has the ``<robot>: <object held, or 'none'>`` shape, as
    separated out by :func:`partition_robot_lines`. An empty hand becomes
    ``(handempty <robot>)``; a held object becomes ``(handfull <robot>)`` plus
    ``(holding <object>)``. Omitting the robot lines entirely leaves the hand empty.

    A held object cannot also be resting in a stack, so it is detached from the stack graph:
    it gets no facts of its own, and any block the input placed directly on it is emitted as
    ``ontable`` instead. Note that this matches the held object by exact name, so an input
    that calls it ``red`` on the robot line but ``red_1`` on its own line is not detached.

    Malformed lines are skipped.
    """
    held = _resolve_held(robot_lines or [])

    facts: set[str] = set()
    for line in lines:
        parsed = _split_line(line)
        if parsed is None:
            continue
        obj, above, below = parsed
        if obj == held:
            continue

        if below.lower() in _NONE_VALUES or below == held:
            facts.add(f"(ontable {obj})")
        else:
            facts.add(f"(on {obj} {below})")
        if above.lower() in _NONE_VALUES or above == held:
            facts.add(f"(clear {obj})")

    if held is None:
        facts.add(f"(handempty {_ROBOT_OBJECT})")
    else:
        facts.add(f"(handfull {_ROBOT_OBJECT})")
        facts.add(f"(holding {held})")
    return facts
