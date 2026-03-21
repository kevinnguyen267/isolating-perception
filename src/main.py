import argparse
import json
from pathlib import Path

from models.vlm import generate_pddl_problem
from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.parse import normalize_problem, normalize_plan
from utils.statistics import compute_statistics

MODEL_MAP = {
    "qwen": "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "gpt": "gpt-5.4",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a PDDL problem file from images via a VLM, then solve with Fast Downward"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="qwen",
        choices=list(MODEL_MAP.keys()),
        help="Name of the VLM to use for problem file generation",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="blocksworld_sim",
        help="Dataset to use for VLM context",
    )
    parser.add_argument(
        "--fast_downward_dir",
        type=str,
        default="/home/mh3897/pddl/villain/downward",
        help="Directory containing fast-downward.py",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=1024,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature for generation",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="API key for OpenAI-compatible API",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Validate Fast Downward directory exists
    downward_dir = Path(args.fast_downward_dir)
    if not (downward_dir / "fast-downward.py").exists():
        raise FileNotFoundError(
            f"fast-downward.py not found in specified directory: {downward_dir}"
        )

    model_id = MODEL_MAP[args.model_name]
    print(
        f"Generating PDDL problem files with {args.model_name} ({model_id}) for {args.dataset}..."
    )

    output_dir = output_dir = Path("results") / args.dataset / args.model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    statistics_summary = {}

    # Iterate over all problem instances in the dataset directory (assumes subdirs for each problem)
    dataset_dir = Path("data") / args.dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if dataset_problem_dir.is_dir():
            output_problem_dir = output_dir / dataset_problem_dir.name
            output_problem_dir.mkdir(parents=True, exist_ok=True)

            print(f"Processing: {dataset_problem_dir.name}")

            gt_domain_path = dataset_problem_dir / "domain.pddl"

            # Copy and normalize ground truth problem file
            gt_problem_path = output_problem_dir / "gt_problem.pddl"
            gt_problem_path.write_text(
                normalize_problem(
                    (dataset_problem_dir / "problem.pddl").read_text(),
                )
            )

            # Generate PDDL problem file using the VLM
            problem_text = generate_pddl_problem(
                model_name=args.model_name,
                model_id=model_id,
                dataset_dir=dataset_problem_dir,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                api_key=args.api_key,
            )
            problem_text = normalize_problem(problem_text)
            problem_path = output_problem_dir / "problem.pddl"
            problem_path.write_text(problem_text)
            
            # Compute statistics against the ground truth problem file
            statistics_summary[dataset_problem_dir.name] = compute_statistics(
                gt_problem_path, problem_path
            )

            # Solve the generated problem with Fast Downward
            success, error_msg, plan_text = find_plan(
                gt_domain_path, problem_path, downward_dir
            )
            plan_text = normalize_plan(plan_text)
            plan_path = output_problem_dir / "plan.txt"
            if success:
                plan_path.write_text(plan_text)
            else:
                plan_path.write_text(f"FAST DOWNWARD ERROR:\n{error_msg}")

            # Record whether the plan was successful with unified planning
            success, error_msg = validate_plan(
                gt_domain_path, gt_problem_path, plan_path
            )
            statistics_summary[dataset_problem_dir.name]["plan_success"] = success
            statistics_summary[dataset_problem_dir.name]["plan_success_error_msg"] = (
                f"UNIFIED PLANNING ERROR:\n{error_msg}" if not success else ""
            )

    # After processing all problems, save an evaluation report to JSON
    statistics_summary_avg = {}
    statistics_summary_avg["plan_success_rate"] = sum(
        statistics_summary[p]["plan_success"] for p in statistics_summary
    ) / len(statistics_summary)
    for key in ("objects", "init", "goal"):
        statistics_summary_avg[key] = {
            "precision": sum(
                statistics_summary[p][key]["precision"] for p in statistics_summary
            )
            / len(statistics_summary),
            "recall": sum(
                statistics_summary[p][key]["recall"] for p in statistics_summary
            )
            / len(statistics_summary),
            "f1": sum(statistics_summary[p][key]["f1"] for p in statistics_summary)
            / len(statistics_summary),
        }
    eval_report = {
        "average_statistics": statistics_summary_avg,
        "individual_statistics": statistics_summary,
    }
    with open(output_dir / "eval_report.json", "w") as f:
        json.dump(eval_report, f, indent=4)
    print(f"Evaluation report saved to: {(output_dir / 'eval_report.json').resolve()}")


if __name__ == "__main__":
    main()
