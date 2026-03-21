import re

# Alias to canonical name mapping
ALIAS_MAP = {
    "robot": "robot1",
    "red": "red_block",
    "orange": "orange_block",
    "yellow": "yellow_block",
    "green": "green_block",
    "blue": "blue_block",
    "purple": "purple_block",
    "pink": "pink_block",
}


def _find_balanced(text: str, start_idx: int) -> str:
    """Return the balanced parenthesized block starting at text[start_idx]='('."""
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return text[start_idx:]


def _get_body(text: str, keyword: str) -> str:
    """Get the inner content of a section, stripping the outer parentheses and keyword."""
    idx = text.find(keyword)
    if idx == -1:
        return ""
    start_idx = text.rfind("(", 0, idx)
    if start_idx == -1:
        return ""

    body = _find_balanced(text, start_idx)
    inner = body[1:-1]  # Remove outer parentheses
    inner = inner[len(keyword) :].strip()  # Remove :objects/init/goal keyword
    return inner


def _parse_objects(text: str) -> set[str]:
    """Parse the :objects section and return a set of 'name - type' strings."""
    inner = _get_body(text, ":objects")
    # Split by whitespace and handle both formats. For example:
    # "<name> - <type>" -> objects.add("(<name> - <type>)")
    # <name> <name> - <type>" -> objects.add("(<name> - <type>)"), objects.add("(<name> - <type>)"), etc.
    objects = set()
    tokens = inner.split()
    names = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "-":
            # Next token is the type
            if i + 1 >= len(tokens):
                raise ValueError(
                    f"Malformed :objects section, '-' without type: {' '.join(tokens)}"
                )
            obj_type = tokens[i + 1]
            for name in names:
                objects.add(f"({name} - {obj_type})")
            names = []
            i += 2
        else:
            # This token is a name (or part of a group of names)
            names.append(ALIAS_MAP.get(tokens[i], tokens[i]))
            i += 1

    # Leftover names with no type
    if names:
        raise ValueError(
            f"Malformed :objects section, names without type: {' '.join(names)}"
        )

    return objects


def _parse_init_goal(text: str, section: str) -> set[str]:
    """Parse the :init or :goal section and return a set of 'predicate args' strings."""
    if section not in (":init", ":goal"):
        raise ValueError(f"Section must be ':init' or ':goal', got: {section}")

    inner = _get_body(text, section)
    if not inner:
        return set()

    # Strip a wrapping (and ...) if present in :goal section
    stripped = inner.strip()
    if section == ":goal" and re.match(r"^\(\s*and\b", stripped):
        inner = _find_balanced(stripped, 0)
        inner = re.sub(r"^\(\s*and\s*", "", inner)[:-1]

    # Find every individual predicate like (<predicate> <arg>) or (<predicate> <arg1> <arg2>)
    predicates = re.findall(r"\([^()]+\)", inner)

    # Normalize
    normalized = set()
    for p in predicates:
        tokens = p.strip("()").split()
        args = [ALIAS_MAP.get(t, t) for t in tokens[1:]]
        normalized.add(f"({tokens[0]} {' '.join(args)})")  # type: ignore

    return normalized


def extract_normalized_problem(
    text: str,
) -> tuple[str, str, set[str], set[str], set[str]]:
    """Parse the problem_name, domain_name, and :objects, :init, :goal sections of a problem file."""
    text = re.sub(r";.*", "", text)

    prob_match = re.search(r"\(\s*define\s+\(problem\s+(\S+)\)", text)
    domain_match = re.search(r"\(:domain\s+(\S+)\)", text)
    prob_name = prob_match.group(1) if prob_match else "unknown"
    domain_name = domain_match.group(1) if domain_match else "unknown"

    objects = _parse_objects(text)
    init = _parse_init_goal(text, ":init")
    goal = _parse_init_goal(text, ":goal")
    return prob_name, domain_name, objects, init, goal


def normalize_problem(problem_text: str) -> str:
    """Normalize a problem file by parsing and reformatting the :objects, :init, and :goal sections with consistent formatting and alias normalization."""
    prob_name, domain_name, objects, init, goal = extract_normalized_problem(
        problem_text
    )

    # Group objects by type: "(name - type)" -> {type: [name, ...]}
    obj_by_type: dict[str, list[str]] = {}
    for o in sorted(objects):
        inner = o.strip("()")
        name, obj_type = inner.split(" - ")
        obj_by_type.setdefault(obj_type.strip(), []).append(name.strip())

    objects_str = "\n    ".join(
        f"{' '.join(sorted(names))} - {t}" for t, names in sorted(obj_by_type.items())
    )

    init_str = "\n    ".join(sorted(init))
    goal_str = "\n    ".join(sorted(goal))

    return (
        f"(define (problem {prob_name})\n"
        f"  (:domain {domain_name})\n"
        f"  (:objects\n    {objects_str}\n  )\n"
        f"  (:init\n    {init_str}\n  )\n"
        f"  (:goal (and\n    {goal_str}\n  ))\n"
        f")"
    )


def normalize_plan(plan_text: str) -> str:
    """Normalize a plan file by normalizing aliases in the action lines."""
    normalized_lines = []
    for line in plan_text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            normalized_lines.append(line)
            continue

        inner = line.strip("()")
        parts = inner.split()
        action_name = parts[0]
        args = parts[1:]
        args = [ALIAS_MAP.get(arg, arg) for arg in args]
        normalized_line = f"({action_name} {' '.join(args)})"
        normalized_lines.append(normalized_line)

    return "\n".join(normalized_lines)
