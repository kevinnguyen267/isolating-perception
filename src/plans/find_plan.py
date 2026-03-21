import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def create_temp_files(
    domain_path: Path, problem_path: Path, temp_dir: Path
) -> Tuple[Path, Path, Path]:
    """Copy domain and problem files into a temp directory and return working paths."""
    tmp_domain = temp_dir / "domain.pddl"
    tmp_problem = temp_dir / "problem.pddl"

    tmp_domain.write_text(domain_path.read_text())
    tmp_problem.write_text(problem_path.read_text())

    plan_path = temp_dir / "output_plan"
    return tmp_domain, tmp_problem, plan_path


def build_command(
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


def run_downward(command: str, plan_path: Path) -> Tuple[bool, Optional[str], str]:
    """
    Execute Fast Downward and return the best plan found.

    Returns:
        (success, error_message, plan_text)
    """
    try:
        subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        # If Fast Downward fails, return error message
        raw = getattr(exc, "output", b"")
        output = raw.decode(errors="replace").strip() if raw else str(exc)

        if "Search stopped without finding a solution" in output:
            return False, "Search stopped without finding a solution.", ""
        if "Driver aborting after search" in output:
            return False, "Search stopped early due to time limit.", ""
        return False, f"...{output[-500:]}", ""

    # Select plan with lowest cost from generated plan files
    plan_files = list(plan_path.parent.glob(f"{plan_path.name}.*"))
    if not plan_files:
        return False, "Fast Downward exited successfully but produced no plan file.", ""

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

    # Clean up generated plan files
    for fname in plan_files:
        fname.unlink()

    if best_plan is None:
        return False, "No valid plan found in output files.", ""

    return True, None, best_plan


def find_plan(
    domain_path: Path, problem_path: Path, downward_dir: Path, time_limit: int = 20
) -> Tuple[bool, Optional[str], str]:
    """
    Finds a plan using Fast Downward.

    Returns:
        (success, error_message, plan_text)
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_domain, tmp_problem, plan_path = create_temp_files(
            domain_path, problem_path, tmp_dir
        )
        command = build_command(
            tmp_domain, tmp_problem, plan_path, downward_dir, time_limit
        )
        return run_downward(command, plan_path)
