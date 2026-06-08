import os
import random
import re
from pathlib import Path
from typing import List

import numpy as np
import torch

from utils.parse import (
    create_problem_from_sections,
    extract_output_from_response,
    normalize_problem,
)


def seed_everything(seed: int):
    """Set random seeds for reproducibility across random, numpy, and torch."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _get_gt_domain_and_problem(
    dataset_problem_dir: Path, output_problem_dir: Path
) -> tuple[str, str, Path, Path]:
    """Get ground truth domain and problem from the dataset problem directory.
    Rewrites the problem file to the output directory with normalized formatting.

    Returns: (domain_text, normalized_problem_text, domain_path, problem_path)
    """
    # Read (unmodified) domain
    domain_path = dataset_problem_dir.parent / "domain.pddl"
    if not domain_path.exists():
        raise FileNotFoundError(f"Ground truth domain file not found: {domain_path}")
    domain = domain_path.read_text()

    # Read (normalized) problem
    problem_path = dataset_problem_dir / "problem.pddl"
    if not problem_path.exists():
        raise FileNotFoundError(f"Ground truth problem file not found: {problem_path}")
    problem = problem_path.read_text()
    normalized_problem = normalize_problem(problem)

    # Write the normalized problem to the output directory for reference
    output_problem_path = output_problem_dir / "gt_problem.pddl"
    output_problem_path.write_text(normalized_problem)

    return domain, normalized_problem, domain_path, output_problem_path


def _valid_problem_cost(prob_dir: Path, threshold: int = 5) -> bool:
    """Filter out problems if the plan cost is below a certain threshold."""
    plan_path = prob_dir / "plan.txt"
    if plan_path.exists():
        with plan_path.open() as f:
            match = re.search(r"; cost = (\d+)", f.read())
            if match and int(match.group(1)) >= threshold:
                return True
    return False


def get_problem_dirs(dataset_dir: Path, num_samples: int | None = None) -> List[Path]:
    """Return the dataset's problem subdirectories, sorted by name."""
    problem_dirs = [
        p
        for p in sorted(dataset_dir.iterdir())
        if p.is_dir() and _valid_problem_cost(p)
    ]
    if num_samples is not None:
        problem_dirs = problem_dirs[:num_samples]
    return problem_dirs


def setup_problem(
    dataset_problem_dir: Path,
    output_dir: Path,
):
    name = dataset_problem_dir.name

    # Set up output directory for the problem
    output_problem_dir = output_dir / "problems" / name
    output_problem_dir.mkdir(parents=True, exist_ok=True)

    # Add a symlink to the problem's data directory for reference
    symlink_path = output_problem_dir / "source_data"
    if not symlink_path.exists():
        symlink_path.symlink_to(dataset_problem_dir.resolve())

    # Get ground truth domain (unmodified) and problem (normalized) texts
    gt_domain, gt_problem, gt_domain_path, gt_problem_path = _get_gt_domain_and_problem(
        dataset_problem_dir, output_problem_dir
    )

    return (
        name,
        output_problem_dir,
        gt_domain,
        gt_problem,
        gt_domain_path,
        gt_problem_path,
    )


def extract_dataset_info(
    dataset_problem_dir: Path,
) -> tuple[List[Path], List[Path]]:
    """Extract init and goal image paths from the dataset directory."""
    init_paths = sorted((dataset_problem_dir / "observations").glob("init_*"))
    if not init_paths:
        raise FileNotFoundError(
            f"No init images found in {dataset_problem_dir / 'observations'}"
        )
    goal_paths = sorted((dataset_problem_dir / "observations").glob("goal_*"))
    if not goal_paths:
        raise FileNotFoundError(
            f"No goal images found in {dataset_problem_dir / 'observations'}"
        )

    return init_paths, goal_paths


def assemble_pddl_problem(
    init_response: str,
    goal_response: str,
    objects: set[str],
    gt_domain: str,
    gt_problem: str,
) -> tuple[str, str, str]:
    """Assemble a PDDL problem from pre-obtained VLM responses.

    Returns: (problem, init_response_extracted, goal_response_extracted)
    """
    init_preds, init_response_extracted = extract_output_from_response(init_response)
    goal_preds, goal_response_extracted = extract_output_from_response(goal_response)

    # Extract domain name from the ground truth domain file
    match = re.search(r"\(domain\s+(\w+)\)", gt_domain)
    if not match:
        raise ValueError(
            "Could not extract domain name from the ground truth domain file."
        )
    domain_name = match.group(1)

    # Extract problem name from the ground truth problem file
    match = re.search(r"\(problem\s+(\w+)\)", gt_problem)
    if not match:
        raise ValueError(
            "Could not extract problem name from the ground truth problem file."
        )
    problem_name = match.group(1)

    problem = create_problem_from_sections(
        problem_name,
        domain_name,
        objects,
        init_preds,
        goal_preds,
    )
    return (
        problem,
        init_response_extracted,
        goal_response_extracted,
    )
