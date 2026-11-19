"""Ablate the perceiver's view reconciler by replaying saved responses.

No model is queried: every condition re-solves the same stored perceiver responses with
different solver settings, then plans and validates against the ground truth.

Example:
    python src/analysis/ablate_reconciler.py --model_name Gemma-4-31B_thinking
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/

from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.helpers import assemble_pddl_problem
from utils.parse import (
    extract_normalized_problem,
    has_object_facts,
    normalize_plan,
    normalize_problem,
)
from utils.statistics import (
    compute_precision_recall_f1,
    get_eval_report_formalizer,
)

# Solver settings per condition; "baseline" matches the defaults used by the pipeline.
CONDITIONS = {
    "baseline": {"on_weight": 2, "empty_weight": 1, "reliability_bonus": True},
    "no_reliability_bonus": {
        "on_weight": 2,
        "empty_weight": 1,
        "reliability_bonus": False,
    },
    "equal_weights": {"on_weight": 1, "empty_weight": 1, "reliability_bonus": True},
    "equal_weights_no_reliability_bonus": {
        "on_weight": 1,
        "empty_weight": 1,
        "reliability_bonus": False,
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replay saved perceiver responses under different reconciler settings"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Model directory under results/<dataset>/perceiver/, e.g. Gemma-4-31B_thinking",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="blocksworld_depth",
        help="Dataset whose perceiver run to replay",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        help="Timestamp of the run to replay (default: the most recent)",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=list(CONDITIONS),
        default=list(CONDITIONS),
        help="Conditions to run (default: all)",
    )
    parser.add_argument(
        "--fast_downward_dir",
        type=str,
        default="downward",
        help="Directory containing fast-downward.py",
    )
    parser.add_argument(
        "--processing_workers",
        type=int,
        default=8,
        help="Number of parallel workers for processing problems",
    )
    return parser.parse_args()


def replay_problem(
    source_dir: Path,
    output_dir: Path,
    domain_path: Path,
    downward_dir: Path,
    solver_options: dict,
) -> dict:
    """Re-solve one problem's saved responses and evaluate the resulting plan."""
    responses = {}
    for section in ("init", "goal"):
        path = source_dir / f"{section}_response.txt"
        responses[section] = path.read_text() if path.exists() else ""
    if not all(responses.values()):
        return {"plan_success": False}

    gt_problem_path = source_dir / "gt_problem.pddl"
    gt_problem = gt_problem_path.read_text()
    domain = domain_path.read_text()

    problem, _, _ = assemble_pddl_problem(
        responses["init"],
        responses["goal"],
        extract_normalized_problem(gt_problem)[2],
        domain,
        gt_problem,
        "perceiver",
        solver_options,
    )
    problem = normalize_problem(problem)
    output_dir.mkdir(parents=True)
    (output_dir / "problem.pddl").write_text(problem)

    stats = {"plan_success": False, **compute_precision_recall_f1(gt_problem, problem)}
    _, _, _, init_facts, goal_facts = extract_normalized_problem(problem)
    if not (has_object_facts(init_facts) and has_object_facts(goal_facts)):
        return stats

    found, _, plan = find_plan(domain, problem, downward_dir)
    if found:
        plan = normalize_plan(plan)
        (output_dir / "plan.txt").write_text(plan)
        stats["plan_success"], _ = validate_plan(domain_path, gt_problem_path, plan)
    return stats


def main():
    args = parse_args()

    downward_dir = Path(args.fast_downward_dir)
    if not (downward_dir / "fast-downward.py").exists():
        raise FileNotFoundError(
            f"fast-downward.py not found in specified directory: {downward_dir}"
        )

    # Source run: results/<dataset>/perceiver/<model>/<timestamp>
    model_dir = Path("results") / args.dataset / "perceiver" / args.model_name
    runs = sorted(p.name for p in model_dir.glob("*") if (p / "problems").is_dir())
    if not runs:
        raise FileNotFoundError(f"No perceiver runs found in {model_dir}")
    source_dir = model_dir / (args.run or runs[-1])
    domain_path = Path("data") / args.dataset / "domain.pddl"
    names = sorted(p.name for p in (source_dir / "problems").iterdir() if p.is_dir())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path("ablations") / "reconciler" / args.dataset / args.model_name / timestamp
    )
    output_dir.mkdir(parents=True)
    print(f"Replaying {source_dir} ({len(names)} problems) into {output_dir}")

    summaries = {condition: {} for condition in args.conditions}
    with ThreadPoolExecutor(max_workers=args.processing_workers) as executor:
        futures = {
            executor.submit(
                replay_problem,
                source_dir / "problems" / name,
                output_dir / condition / "problems" / name,
                domain_path,
                downward_dir,
                CONDITIONS[condition],
            ): (condition, name)
            for condition in args.conditions
            for name in names
        }
        for future in as_completed(futures):
            condition, name = futures[future]
            try:
                summaries[condition][name] = future.result()
            except Exception as e:
                print(f"  ERROR processing {condition}/{name}: {e!r}")
                summaries[condition][name] = {"plan_success": False}

    for condition, summary in summaries.items():
        report = get_eval_report_formalizer({name: summary[name] for name in names})
        report["solver_options"] = CONDITIONS[condition]
        report["source_run"] = str(source_dir)
        (output_dir / condition).mkdir(exist_ok=True)
        with open(output_dir / condition / "eval_report.json", "w") as f:
            json.dump(report, f, indent=4)
        stats = report["average_statistics"]
        print(
            f"{condition}: {stats['num_plans_passed']}/{stats['num_problems']} "
            f"({stats['plan_success_rate']:.1%})"
        )


if __name__ == "__main__":
    main()
