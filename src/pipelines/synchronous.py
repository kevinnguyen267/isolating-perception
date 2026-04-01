import json
from pathlib import Path

from models.formalizer import generate_pddl_problem
from models.formalizer_reprompt import regenerate_pddl_problem
from models.planner import generate_plan
from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.helpers import setup_problem
from utils.parse import (
    normalize_plan,
    normalize_problem,
)
from utils.statistics import (
    compute_plan_success_with_ground_truth,
    compute_precision_recall_f1,
    get_eval_report_formalizer,
    get_eval_report_planner,
)


def solve_by_formalization(
    args,
    model_id: str,
    dataset_problem_dir: Path,
    name: str,
    downward_dir: Path,
    gt_domain: str,
    gt_problem: str,
    gt_domain_path: Path,
    gt_problem_path: Path,
    problem: str,
    init_response: str,
    goal_response: str,
    init_cleanup_response: str,
    goal_cleanup_response: str,
    statistics_summary: dict[str, dict],
    output_dir: Path,
    output_problem_dir: Path,
) -> None:
    """Helper function for synchronous pipeline and re-prompting batch pipeline.
    Given a generated PDDL problem file, attempt to solve and validate it using Fast Downward and Unified Planning.

    Returns None but updates statistics_summary in-place and saves all relevant files to output_problem_dir for error analysis."""
    problem = normalize_problem(problem)
    (output_problem_dir / "problem.pddl").write_text(problem)

    # Save VLM responses
    (output_problem_dir / "init_response.txt").write_text(init_response)
    (output_problem_dir / "goal_response.txt").write_text(goal_response)
    (output_problem_dir / "init_cleanup_response.txt").write_text(init_cleanup_response)
    (output_problem_dir / "goal_cleanup_response.txt").write_text(goal_cleanup_response)

    # Solve the generated problem using Fast Downward
    downward_success, downward_error_msg, plan = find_plan(
        gt_domain, problem, downward_dir
    )
    # If the plan generation attempt fails, re-prompt the VLM to try to fix the problem file
    # Currently, only re-prompts once and only regenerates the init section
    if not downward_success:
        (output_problem_dir / "downward_error.txt").write_text(downward_error_msg)

        # Re-prompt the VLM
        statistics_summary[name]["num_reprompts"] = 1
        (
            problem,
            init_response,
            init_cleanup_response,
        ) = regenerate_pddl_problem(
            model_id,
            dataset_problem_dir,
            gt_domain,
            problem,
            args.max_tokens,
            args.temperature,
            args.seed,
            args.quantization,
        )
        problem = normalize_problem(problem)
        (output_problem_dir / "problem_reprompted.pddl").write_text(problem)

        # Save the re-prompted VLM responses
        (output_problem_dir / "init_response_reprompted.txt").write_text(init_response)
        (output_problem_dir / "init_cleanup_response_reprompted.txt").write_text(
            init_cleanup_response
        )

        # Try Fast Downward again on the re-prompted problem
        downward_success, downward_error_msg, plan = find_plan(
            gt_domain, problem, downward_dir
        )

    if not downward_success:
        # If it fails the re-prompting attempt
        statistics_summary[name]["downward_success"] = False
        (output_problem_dir / "downward_error_reprompted.txt").write_text(
            downward_error_msg
        )
        plan_success = False
    else:
        # If the plan generation is successful, check if the plan was successful using UP
        plan = normalize_plan(plan)
        (output_problem_dir / "plan.txt").write_text(plan)

        plan_success, plan_error_msg = validate_plan(
            gt_domain_path, gt_problem_path, plan
        )
        statistics_summary[name]["plan_success"] = plan_success

    # Determine whether the plan failed due to init or goal state (or both) for error analysis
    if not plan_success:
        statistics_summary[name].update(
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
    statistics_summary[name].update(compute_precision_recall_f1(gt_problem, problem))

    # Save evaluation report
    eval_report = get_eval_report_formalizer(statistics_summary)
    with open(output_dir / "eval_report.json", "w") as f:
        json.dump(eval_report, f, indent=4)


def main(args, model_id, output_dir, dataset_dir, downward_dir):
    statistics_summary = {}
    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if not dataset_problem_dir.is_dir():
            continue

        (
            name,
            output_problem_dir,
            gt_domain,
            gt_problem,
            gt_domain_path,
            gt_problem_path,
        ) = setup_problem(dataset_problem_dir, output_dir)

        print(f"  Processing {name}...")
        statistics_summary[name] = {}

        if args.mode == "planner":
            # Generate plan using VLM
            plan, response = generate_plan(
                model_id,
                dataset_problem_dir,
                args.max_tokens,
                args.temperature,
                args.seed,
                args.quantization,
            )
            plan = normalize_plan(plan)
            (output_problem_dir / "plan.txt").write_text(plan)

            # Save VLM response
            (output_problem_dir / "response.txt").write_text(response)

            # Check if plan was successful using UP
            plan_success, plan_error_msg = validate_plan(
                gt_domain_path, gt_problem_path, plan
            )
            statistics_summary[name]["plan_success"] = plan_success

            # Save evaluation report
            eval_report = get_eval_report_planner(statistics_summary)
            with open(output_dir / "eval_report.json", "w") as f:
                json.dump(eval_report, f, indent=4)

        elif args.mode == "formalizer":
            # Generate PDDL problem file using VLM
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

            # Run helper function to solve the problem, validate the plan, compute statistics, and save all relevant files for error analysis
            solve_by_formalization(
                args,
                model_id,
                dataset_problem_dir,
                name,
                downward_dir,
                gt_domain,
                gt_problem,
                gt_domain_path,
                gt_problem_path,
                problem,
                init_response,
                goal_response,
                init_cleanup_response,
                goal_cleanup_response,
                statistics_summary,
                output_dir,
                output_problem_dir,
            )
