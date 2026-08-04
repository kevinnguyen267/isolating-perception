from collections import Counter
from itertools import combinations

from z3 import And, Context, Int, Optimize, Or, Z3Exception, unknown, unsat

_ABOVE = "above"
_BELOW = "below"
_NONE_VALUES = {"", "none", "null", "nothing"}

# Wall-clock cap on a single solve; 0 disables the cap.
_SOLVER_TIMEOUT_MS = 5 * 60 * 1000

# Subjects that name the robot rather than a block. Matched case-insensitively against the
# left-hand side of a line, so that a robot line is recognized however many fields follow.
_ROBOT_NAMES = {"robot", "robot_1", "robot_arm", "robot arm", "gripper", "arm", "hand"}
# Every dataset declares exactly one ``robot - robot`` object, so the robot facts always use
# this name regardless of what the input called it. ``ALIAS_MAP`` maps it to ``robot_1``.
_ROBOT_OBJECT = "robot"


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

    Only the object lines describe where a block sits, so only they are translated into
    placement claims; the robot lines are read separately for what the gripper holds.
    Keeping the robot out of the solver also stops it from being placed in a stack, which
    would emit ill-typed ``on``/``ontable`` facts for it.
    """
    object_lines, robot_lines = [], []
    for line in lines:
        if _split_robot_line(line) is None:
            object_lines.append(line)
        else:
            robot_lines.append(line)
    return object_lines, robot_lines


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

        Returns ``None`` when ``obj`` is the only object, since nothing can fill the cell.
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
    empty_obs: Counter[tuple[str, str]],
):
    """Solve for the placement satisfying the best-supported set of claims.

    Args:
        placement: The cell variables every constraint below is stated over.
        weights: Claim support per ``(upper, lower)`` relation, as positive evidence that
            the two are stacked.
        empty_obs: Evidence per ``(object, direction)`` cell that the cell is empty, as
            negative evidence against any relation that would fill it.

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

    # Negative evidence: each observation that a cell is empty votes (with no reliability
    # bonus) for it staying empty, opposing any relation that would fill it. This is
    # deliberately weak -- a single genuine claim still dominates -- so it only tips cells
    # that are otherwise a symmetric tie, toward the object seen isolated.
    for (obj, direction), count in empty_obs.items():
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
