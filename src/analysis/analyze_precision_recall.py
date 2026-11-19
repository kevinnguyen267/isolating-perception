"""Compute state precision and recall for every mode, planner included.

Formalizer and perceiver states are read from problem.pddl. Planner writes only a plan, so
its states are recovered from the plan as in Appendix D. Each value is the mean of the init
and goal state scores, averaged over the problems with a predicted state.

Example:
    python src/analysis/analyze_precision_recall.py --output results/precision_recall.csv
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/

from analysis.common import latest_run, parse_gt, plan_implied_facts
from utils.parse import (
    create_problem_from_sections,
    extract_normalized_problem,
)
from utils.statistics import compute_precision_recall_f1


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute state precision and recall for every mode"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=[
            "blocksworld_po",
            "blocksworld_po_12",
            "blocksworld_po_20",
            "blocksworld_po_40",
            "blocksworld_po_100",
        ],
        help="Datasets under results/ to analyze",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["planner", "formalizer", "perceiver"],
        help="Modes to analyze",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "Gemma-4-31B_thinking",
            "Qwen3.5-122B-A10B_thinking",
            "Gemini-3.1-Pro",
        ],
        help="Model directories to analyze",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Glob patterns of run directories to ignore when picking the latest run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional CSV file to write the table to",
    )
    return parser.parse_args()


def precision_recall(run_dir: Path, mode: str) -> tuple[float, float, int]:
    """Mean init/goal precision and recall over a run's problems, and the problem count."""
    scores = []
    for problem_dir in sorted((run_dir / "problems").glob("problem_*")):
        gt_path = problem_dir / "gt_problem.pddl"
        if not gt_path.exists():
            continue
        gt_text = gt_path.read_text()
        if mode.startswith("planner"):
            blocks, robot, _, _ = parse_gt(gt_text)
            plan = problem_dir / "plan.txt"
            init, goal = plan_implied_facts(
                plan.read_text() if plan.exists() else "", blocks, robot
            )
            name, domain, objects, _, _ = extract_normalized_problem(gt_text)
            problem = create_problem_from_sections(name, domain, objects, init, goal)
        elif (problem_dir / "problem.pddl").exists():
            problem = (problem_dir / "problem.pddl").read_text()
        else:
            continue
        scores.append(compute_precision_recall_f1(gt_text, problem))

    n = len(scores)
    if n == 0:
        return 0.0, 0.0, 0
    precision, recall = (
        sum(s[state][metric] for s in scores for state in ("init", "goal")) / (2 * n)
        for metric in ("precision", "recall")
    )
    return precision, recall, n


def main():
    args = parse_args()

    rows = []
    print(
        f"{'dataset':<20}{'mode':<12}{'model':<30}{'precision':>10}{'recall':>8}{'n':>5}"
    )
    for dataset in args.datasets:
        for mode in args.modes:
            for model in args.models:
                run_dir = latest_run(
                    Path("results") / dataset / mode / model, args.exclude
                )
                if run_dir is None:
                    print(f"{dataset:<20}{mode:<12}{model:<30}  no run found")
                    continue
                precision, recall, n = precision_recall(run_dir, mode)
                print(
                    f"{dataset:<20}{mode:<12}{model:<30}"
                    f"{precision:>10.1%}{recall:>8.1%}{n:>5}"
                )
                rows.append(
                    {
                        "dataset": dataset,
                        "mode": mode,
                        "model": model,
                        "run": str(run_dir),
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                        "num_problems": n,
                    }
                )

    if args.output and rows:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV saved to: {args.output}")


if __name__ == "__main__":
    main()
