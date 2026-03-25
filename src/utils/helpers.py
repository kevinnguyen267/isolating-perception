import os
import random
from pathlib import Path

import numpy as np
import torch
from utils.parse import normalize_problem


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


def get_gt_domain_and_problem(
    dataset_problem_dir: Path, output_problem_dir: Path
) -> tuple[str, str, Path, Path]:
    """Get ground truth domain and problem from the dataset problem directory.
    Rewrites the problem file to the output directory with normalized formatting.

    Returns: (domain_text, normalized_problem_text, domain_path, problem_path)
    """
    # Read (unmodified) domain
    domain_path = dataset_problem_dir / "domain.pddl"
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
