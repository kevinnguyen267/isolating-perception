import json
from pathlib import Path

from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.helpers import assemble_pddl_problem, extract_dataset_info, setup_problem
from utils.parse import (
    extract_output_from_response,
    get_present_objects,
    normalize_plan,
    normalize_problem,
)
from utils.statistics import (
    compute_plan_success_with_ground_truth,
    compute_precision_recall_f1,
    get_eval_report_formalizer,
    get_eval_report_planner,
)
from utils.vlm import generate_response


def _run_planner(args, mode_module, model_id, output_dir, dataset_dir):
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

        objects = get_present_objects(dataset_problem_dir)
        image_paths, text_paths, instruction = extract_dataset_info(dataset_problem_dir)

        prompt = mode_module.build_prompt(objects, gt_domain, image_paths, text_paths, instruction)
        (output_problem_dir / "prompt.txt").write_text(json.dumps(prompt, indent=4))
        response = generate_response(
            model_id, args.use_openrouter, prompt, args.max_tokens, args.temperature, args.seed
        )

        _, plan_str = extract_output_from_response(response)
        plan = normalize_plan(plan_str)
        (output_problem_dir / "plan.txt").write_text(plan)
        (output_problem_dir / "response.txt").write_text(response)

        plan_success, _ = validate_plan(gt_domain_path, gt_problem_path, plan)
        statistics_summary[name]["plan_success"] = plan_success

        eval_report = get_eval_report_planner(statistics_summary)
        with open(output_dir / "eval_report.json", "w") as f:
            json.dump(eval_report, f, indent=4)


def _run_formalizer(args, mode_module, model_id, output_dir, dataset_dir, downward_dir):
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

        objects = get_present_objects(dataset_problem_dir)
        image_paths, text_paths, instruction = extract_dataset_info(dataset_problem_dir)

        # Goal state
        goal_prompt = mode_module.build_goal_prompt(objects, gt_domain, instruction)
        (output_problem_dir / "goal_prompt.txt").write_text(json.dumps(goal_prompt, indent=4))
        goal_response = generate_response(
            model_id, args.use_openrouter, goal_prompt, args.max_tokens, args.temperature, args.seed
        )

        # Init state - mode_module decides whether to generate single prompt or multiple per-image prompts with merge step
        init_prompts = mode_module.build_init_prompts(objects, gt_domain, image_paths, text_paths)
        if len(init_prompts) == 1:
            (output_problem_dir / "init_prompt.txt").write_text(json.dumps(init_prompts, indent=4))
            init_response = generate_response(
                model_id, args.use_openrouter, init_prompts[0], args.max_tokens, args.temperature, args.seed
            )
            per_image_responses = None
        else:
            (output_problem_dir / "init_prompts.txt").write_text(json.dumps(init_prompts, indent=4))
            per_image_responses = [
                generate_response(
                    model_id, args.use_openrouter, p, args.max_tokens, args.temperature, args.seed
                )
                for p in init_prompts
            ]
            merge_prompt = mode_module.build_merge_prompt(
                objects, gt_domain, image_paths, per_image_responses
            )
            init_response = generate_response(
                model_id, args.use_openrouter, merge_prompt, args.max_tokens, args.temperature, args.seed
            )

        # Assemble PDDL problem
        all_objects = set().union(*objects)
        (
            problem,
            init_response_extracted,
            goal_response_extracted,
        ) = assemble_pddl_problem(
            init_response, goal_response, all_objects, gt_domain, gt_problem
        )

        # Solve, validate, and save
        solve_by_formalization(
            name,
            downward_dir,
            gt_domain,
            gt_problem,
            gt_domain_path,
            gt_problem_path,
            problem,
            init_response,
            goal_response,
            init_response_extracted,
            goal_response_extracted,
            per_image_responses,
            statistics_summary,
            output_dir,
            output_problem_dir,
        )


def solve_by_formalization(
    name: str,
    downward_dir: Path,
    gt_domain: str,
    gt_problem: str,
    gt_domain_path: Path,
    gt_problem_path: Path,
    problem: str,
    init_response: str,
    goal_response: str,
    init_response_extracted: str,
    goal_response_extracted: str,
    per_image_responses: list[str] | None,
    statistics_summary: dict[str, dict],
    output_dir: Path,
    output_problem_dir: Path,
) -> None:
    """Given a generated PDDL problem file, attempt to solve and validate it.

    Updates statistics_summary in-place and saves all relevant files."""
    problem = normalize_problem(problem)
    (output_problem_dir / "problem.pddl").write_text(problem)

    # Save VLM responses
    (output_problem_dir / "init_response.txt").write_text(init_response)
    (output_problem_dir / "goal_response.txt").write_text(goal_response)
    (output_problem_dir / "init_response_extracted.txt").write_text(
        init_response_extracted
    )
    (output_problem_dir / "goal_response_extracted.txt").write_text(
        goal_response_extracted
    )
    if per_image_responses:
        for i, resp in enumerate(per_image_responses):
            (output_problem_dir / f"init_response_img_{i}.txt").write_text(resp)

    # Solve the generated problem using Fast Downward and validate if successful
    downward_success, _, plan = find_plan(gt_domain, problem, downward_dir)
    if not downward_success:
        statistics_summary[name]["downward_success"] = False
        plan_success = False
    else:
        plan = normalize_plan(plan)
        (output_problem_dir / "plan.txt").write_text(plan)

        plan_success, _ = validate_plan(gt_domain_path, gt_problem_path, plan)
        statistics_summary[name]["plan_success"] = plan_success

    # Determine whether the plan failed due to init or goal state
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


def main(args, mode_module, kind, model_id, output_dir, dataset_dir, downward_dir):
    if kind == "planner":
        _run_planner(args, mode_module, model_id, output_dir, dataset_dir)
    else:
        _run_formalizer(
            args, mode_module, model_id, output_dir, dataset_dir, downward_dir
        )
