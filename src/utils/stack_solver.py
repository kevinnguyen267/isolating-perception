import re

from utils.predicate_solver import predicates_to_pddl
from utils.spatial_solver import (
    _NONE_VALUES,
    _ROBOT_OBJECT,
    _split_robot_line,
    partition_robot_lines,
)

# An object name starts with a letter and carries no punctuation, so a field failing this is
# a leftover of the response's own formatting (a list number, a bare "1.") rather than a
# block. Dropping those keeps invented objects out of the assembled problem.
_OBJECT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")

# A bullet or list number in front of a stack line, which would otherwise be read as the
# bottom object's name and cost the stack its bottom block.
_ENUMERATION_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _is_object(name: str) -> bool:
    return bool(name) and name[0].isalpha() and set(name) <= _OBJECT_CHARS


def _stack_objects(line: str) -> list[str]:
    """Parse one `<bottom>, <above>, ..., <top>` line into its objects, bottom first.

    Two kinds of decoration are dropped, because a response asked for a list tends to write
    one anyway and losing a block to it would quietly shorten the stack:

    - An enumeration marker in front of the line (`- red_1, blue_2`, `2. red_1, blue_2`).
    - A label in front of a field (`Stack 2: red_1`, `bottom: red_1`). A colon can only be
      part of a label, since no object name contains one and the robot lines that
      legitimately use a colon have already been partitioned out.

    Only the first token of each field is then read, which drops trailing annotations like
    `red_1 (bottom)`.
    """
    objects = []
    for field in _ENUMERATION_RE.sub("", line).split(","):
        tokens = field.rpartition(":")[2].strip().strip("()[]*-•").split()
        if not tokens:
            continue
        name = tokens[0]
        if name.lower() in _NONE_VALUES or not _is_object(name):
            continue
        objects.append(name)
    return objects


def _view_to_predicates(lines: list[str]) -> list[str]:
    """Translate one view's stack and robot lines into grounded predicates.

    Aliases are deliberately left alone: `predicate_solver.parse_predicates` resolves them
    before the views vote, which is early enough for `red_1` and `red_block_1` to already be
    the same block by the time their claims are counted.
    """
    object_lines, robot_lines = partition_robot_lines(lines)

    predicates = []
    for line in object_lines:
        stack = _stack_objects(line)
        if not stack:
            continue
        predicates.append(f"(ontable {stack[0]})")
        predicates.append(f"(clear {stack[-1]})")
        predicates.extend(
            f"(on {upper} {lower})" for lower, upper in zip(stack, stack[1:])
        )

    for line in robot_lines:
        held = _split_robot_line(line)
        if held is None:
            continue
        if held.lower() in _NONE_VALUES or not _is_object(held):
            predicates.append(f"(handempty {_ROBOT_OBJECT})")
        else:
            predicates.append(f"(holding {held})")

    return predicates


def stacks_to_pddl(views: list[list[str]]) -> set[str]:
    """Ground several views' stack lines into one physically possible set of facts.

    Args:
        views: One list of raw response lines per view of the same scene, each list holding
            that view's stack lines and its robot line in any order.

    Returns:
        The Blocksworld facts of the best-supported placement, in the same form
        :func:`utils.predicate_solver.predicates_to_pddl` returns them: `(on X Y)` /
        `(ontable X)` for what each block rests on, `(clear X)` for a block with nothing
        above it, and `(handempty <robot>)` or `(handfull <robot>)` plus `(holding X)` for
        the robot. A block no view placed in any stack stays absent.
    """
    return predicates_to_pddl([_view_to_predicates(view) for view in views])
