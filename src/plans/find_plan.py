import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


def _create_temp_files(
    domain: str, problem: str, temp_dir: Path
) -> Tuple[Path, Path, Path]:
    """Write domain and problem files into a temp directory and return working paths."""
    tmp_domain_path = temp_dir / "domain.pddl"
    tmp_problem_path = temp_dir / "problem.pddl"

    tmp_domain_path.write_text(domain)
    tmp_problem_path.write_text(problem)

    plan_path = temp_dir / "output_plan"
    return tmp_domain_path, tmp_problem_path, plan_path


def _build_command(
    domain_path: Path,
    problem_path: Path,
    plan_path: Path,
    downward_dir: Path,
    time_limit: int,
) -> str:
    """Build the Fast Downward CLI command string."""
    sas_path = plan_path.with_suffix(".sas")
    return (
        f"python {downward_dir}/fast-downward.py "
        f"--alias lama "
        f"--search-time-limit {time_limit} "
        f"--plan-file {plan_path} "
        f"--sas-file {sas_path} "
        f"{domain_path} "
        f"{problem_path}"
    )


def _parse_cost(last_line: str) -> float:
    """Extract plan cost from the trailing comment line ('; cost = N ...')."""
    if last_line.startswith("; cost = "):
        try:
            return float(last_line.split()[3])
        except (IndexError, ValueError):
            pass
    return float("inf")


def _select_best_plan(plan_path: Path) -> str | None:
    """Return the lowest-cost plan among generated plan files, or None if there are none."""
    plan_files = list(plan_path.parent.glob(f"{plan_path.name}.*"))
    if not plan_files:
        return None

    best_cost = float("inf")
    best_plan = None

    for fname in plan_files:
        lines = fname.read_text().splitlines()
        cost = _parse_cost(lines[-1]) if lines else float("inf")
        if cost < best_cost:
            best_cost = cost
            best_plan = "\n".join(
                line.strip() for line in lines[:-1]
            )  # Strip the trailing cost comment

    return best_plan


def _run_downward(command: str, plan_path: Path) -> Tuple[bool, str, str]:
    """
    Execute Fast Downward and return the best plan found.

    Returns:
        (success, error_message, plan_text)
    """
    try:
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        output = ""
    except subprocess.CalledProcessError as exc:
        raw = getattr(exc, "output", b"")
        output = raw.decode(errors="replace").strip() if raw else str(exc)

    # Select plan with lowest cost from generated plan files, regardless of exit code
    # since Fast Downward may exit with a non-zero code even if a plan was found.
    best_plan = _select_best_plan(plan_path)
    if best_plan is not None:
        return True, "", best_plan

    if "Search stopped without finding a solution" in output:
        return False, "Search stopped without finding a solution.", ""
    if "Driver aborting after search" in output:
        return False, "Search stopped early due to time limit.", ""
    if output:
        return False, f"...{output[-500:]}", ""
    return False, "Fast Downward exited successfully but produced no plan file.", ""


def find_plan(
    domain: str, problem: str, downward_dir: Path, time_limit: int = 300
) -> Tuple[bool, str, str]:
    """
    Finds a plan using Fast Downward.

    Returns:
        (success, error_message, plan)
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_domain_path, tmp_problem_path, plan_path = _create_temp_files(
            domain, problem, tmp_dir
        )
        command = _build_command(
            tmp_domain_path, tmp_problem_path, plan_path, downward_dir, time_limit
        )
        return _run_downward(command, plan_path)
