import argparse
import json
import os
from pathlib import Path
from time import time

from models.vlm import generate_pddl_problem
from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.helpers import get_gt_domain_and_problem, seed_everything
from utils.parse import (
    normalize_plan,
    normalize_problem,
)
from utils.statistics import (
    compute_plan_success_with_ground_truth,
    compute_precision_recall_f1,
    get_eval_report,
)

MODEL_MAP = {
    "qwen": "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "gpt": "gpt-5.4",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prompting VLMs to generate plans using different methodologies"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="qwen",
        choices=list(MODEL_MAP.keys()),
        help="Name of the VLM to use",
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
        default="downward",
        help="Directory containing fast-downward.py",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=2048,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="Sampling temperature for generation",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--quantization",
        action="store_true",
        help="Whether to use quantized weights for local vLLM inference (if applicable)",
    )

    return parser.parse_args()


def main():
    timer_start = time()
    args = parse_args()
    seed_everything(args.seed)

    # Validate API key for GPT (load_dotenv was already called by top-level code in models/vlm.py)
    if args.model_name == "gpt" and "OPENAI_API_KEY" not in os.environ:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    downward_dir = Path(args.fast_downward_dir)
    if not (downward_dir / "fast-downward.py").exists():
        raise FileNotFoundError(
            f"fast-downward.py not found in specified directory: {downward_dir}"
        )

    model_id = MODEL_MAP[args.model_name]
    print(f"Running {args.dataset} using {model_id}...")

    output_dir = Path("results") / args.dataset / args.model_name
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_dir = Path("data") / args.dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    # Iterate over all problem instances in the dataset directory (assumes subdirs for each problem)
    statistics_summary = {}
    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if dataset_problem_dir.is_dir():
            print(f"  Processing {dataset_problem_dir.name}...")
            statistics_summary[dataset_problem_dir.name] = {}

            output_problem_dir = output_dir / "problems" / dataset_problem_dir.name
            output_problem_dir.mkdir(parents=True, exist_ok=True)

            # Add a symlink to the problem's data directory for reference
            symlink_path = output_problem_dir / "source_data"
            if not symlink_path.exists():
                symlink_path.symlink_to(dataset_problem_dir.resolve())

            # Get ground truth domain (unmodified) and problem (normalized) texts
            gt_domain, gt_problem, gt_domain_path, gt_problem_path = (
                get_gt_domain_and_problem(dataset_problem_dir, output_problem_dir)
            )

            # Generate PDDL problem file using the VLM
            (
                problem,
                init_response,
                goal_response,
                init_cleanup_response,
                goal_cleanup_response,
            ) = generate_pddl_problem(
                model_id,
                dataset_problem_dir,
                gt_domain,
                gt_problem,
                args.max_tokens,
                args.temperature,
                args.seed,
                args.quantization,
            )
            problem = normalize_problem(problem)
            (output_problem_dir / "problem.pddl").write_text(problem)

            # Save VLM responses for init and goal sections
            (output_problem_dir / "init_response.txt").write_text(init_response)
            (output_problem_dir / "goal_response.txt").write_text(goal_response)
            (output_problem_dir / "init_cleanup_response.txt").write_text(
                init_cleanup_response
            )
            (output_problem_dir / "goal_cleanup_response.txt").write_text(
                goal_cleanup_response
            )

            # Solve the generated problem using Fast Downward
            downward_success, downward_error_msg, plan = find_plan(
                gt_domain, problem, downward_dir
            )
            if not downward_success:
                statistics_summary[dataset_problem_dir.name]["downward_success"] = False

            plan = normalize_plan(plan)
            (output_problem_dir / "plan.txt").write_text(plan)

            # Check if plan was successful using unified planning
            plan_success, plan_error_msg = validate_plan(
                gt_domain_path, gt_problem_path, plan
            )
            statistics_summary[dataset_problem_dir.name]["plan_success"] = plan_success

            # Determine whether the plan failed due to init or goal state (or both)
            if not plan_success:
                statistics_summary[dataset_problem_dir.name].update(
                    compute_plan_success_with_ground_truth(
                        gt_problem,
                        problem,
                        gt_domain,
                        gt_domain_path,
                        gt_problem_path,
                        downward_dir,
                    )
                )

            # Record precision, recall, and F1 statistics
            statistics_summary[dataset_problem_dir.name].update(
                compute_precision_recall_f1(gt_problem, problem)
            )

            # Update evaluation report
            eval_report = get_eval_report(statistics_summary)
            with open(output_dir / "eval_report.json", "w") as f:
                json.dump(eval_report, f, indent=4)

    print(f"Evaluation report saved to: {(output_dir / 'eval_report.json').resolve()}")
    print(f"Experiment complete ({int((time() - timer_start) / 60) + 1} minutes).")


if __name__ == "__main__":
    main()
