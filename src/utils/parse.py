import re
from pathlib import Path

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


def _parse_objects_file(filepath: Path) -> set[str]:
    """Parse an objects text file and return a set of '(name - type)' strings."""
    objects = set()
    if not filepath.exists():
        return objects
    for line in filepath.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" - ")
        name = ALIAS_MAP.get(parts[0].strip(), parts[0].strip())
        obj_type = parts[1].strip()
        objects.add(f"({name} - {obj_type})")
    objects.add("(robot1 - robot)")
    return objects


def get_present_objects(dataset_problem_dir: Path) -> list[set[str]]:
    """Get the set of objects present in each image by parsing the corresponding objects text files.

    Returns a list of sets, where each set corresponds to the objects present in one image."""
    objects_dir = dataset_problem_dir / "objects"
    observations_dir = dataset_problem_dir / "observations"
    if not objects_dir.exists() or not observations_dir.exists():
        raise FileNotFoundError(
            f"Expected objects and observations directories at {objects_dir} and {observations_dir}"
        )

    objects = []
    for obs_file in sorted(observations_dir.glob("*")):
        objects.append(_parse_objects_file(objects_dir / (obs_file.stem + ".txt")))

    return objects


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


def parse_section(text: str, section: str) -> set[str]:
    """Parse the :section and return a set of '(predicate arg1 arg2 ...)' strings."""
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


def _parse_types(types_body: str) -> set[str]:
    """Parse the :types section and return a set of 'name - parent' strings, where parent is the immediate parent type or 'object' if no parent is specified."""
    if not types_body:
        return set()

    tokens = types_body.split()
    pairs = set()
    pending = []

    i = 0
    while i < len(tokens):
        if tokens[i] == "-":
            if i + 1 >= len(tokens):
                break
            parent = tokens[i + 1]
            for child in pending:
                pairs.add(f"{child} - {parent}")
            pending = []
            i += 2
        else:
            pending.append(tokens[i])
            i += 1

    for child in pending:
        pairs.add(f"{child} - object")

    return pairs


def extract_domain_sections(domain_text: str) -> dict[str, str | set[str]]:
    """Extract types, predicates, and actions from a PDDL domain string.

    Types are returned as a set of type names.
    Predicates are returned as a set of '(predicate arg1 arg2 ...)' strings.
    Actions are returned as a set of '(:action ...)' strings.

    Returns dict with keys: "name", "types", "predicates", "actions"
    """
    # Name
    name_match = re.search(r"\(\s*define\s+\(domain\s+(\S+)\)", domain_text)
    domain_name = name_match.group(1) if name_match else "unknown"

    # Types
    types_body = _get_body(domain_text, ":types")
    types = _parse_types(types_body)

    # Predicates
    predicates = parse_section(domain_text, ":predicates")
    predicates = set(p.strip() for p in predicates)

    # Actions
    actions = set()
    idx = 0
    while True:
        idx = domain_text.find("(:action", idx)
        if idx == -1:
            break
        actions.add(_find_balanced(domain_text, idx))
        idx += 1

    return {
        "name": domain_name,
        "types": types,
        "predicates": predicates,
        "actions": actions,
    }


def extract_normalized_problem(
    text: str,
) -> tuple[str, str, set[str], set[str], set[str]]:
    """Parse the problem_name, domain_name, and :objects, :init, :goal sections of a problem file.

    Returns: (problem_name, domain_name, objects, init, goal)
    """
    text = re.sub(r";.*", "", text)

    prob_match = re.search(r"\(\s*define\s+\(problem\s+(\S+)\)", text)
    domain_match = re.search(r"\(:domain\s+(\S+)\)", text)
    prob_name = prob_match.group(1) if prob_match else "unknown"
    domain_name = domain_match.group(1) if domain_match else "unknown"

    objects = _parse_objects(text)
    init = parse_section(text, ":init")
    goal = parse_section(text, ":goal")
    return prob_name, domain_name, objects, init, goal


def create_problem_from_sections(
    prob_name: str,
    domain_name: str,
    objects: set[str],
    init: set[str] | list[str],
    goal: set[str] | list[str],
) -> str:
    """Create a problem string from the given sections."""
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


def normalize_problem(problem_text: str) -> str:
    """Normalize a problem file by parsing and reformatting the :objects, :init, and :goal sections with consistent formatting and alias normalization."""
    prob_name, domain_name, objects, init, goal = extract_normalized_problem(
        problem_text
    )
    return create_problem_from_sections(prob_name, domain_name, objects, init, goal)


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


def extract_output_from_response(response: str) -> tuple[list[str], str]:
    """Extract the lines within the last code block of the response.
    Each line is formatted as '(<token0> <token1> <token2> ...)'.
    For output_str, the lines are joined with newlines.

    Returns: (output_lst, output_str)"""
    output = []

    match = re.findall(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
    if match:
        lines = match[-1].strip().splitlines()
        for line in lines:
            tokens = line.replace("(", " ").replace(")", " ").replace(",", " ").split()
            if tokens:
                output.append(f"({' '.join(tokens)})")

    output_str = "\n".join(output)

    return output, output_str
