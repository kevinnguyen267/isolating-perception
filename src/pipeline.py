import json
from pathlib import Path

from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.batch import build_batch_request, run_batch
from utils.helpers import (
    assemble_pddl_problem,
    extract_dataset_info,
    get_problem_dirs,
    setup_problem,
)
from utils.parse import (
    extract_output_from_response,
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

# TODO: object set is currently hardcoded for blocksworld
_BLOCKSWORLD_OBJECTS = {
    "red - block",
    "orange - block",
    "yellow - block",
    "green - block",
    "blue - block",
    "purple - block",
    "robot1 - robot",
}


def _generate_responses(
    args,
    model_id: str,
    requests: list[tuple[str, list[dict]]],
    *,
    use_batch: bool,
    batch_file: Path,
    description: str,
) -> dict[str, str]:
    """Generate a response for every (custom_id, prompt) pair.
    Supports both synchronous generation and batch generation.

    Return a dictionary mapping custom_id to response text.
    """
    if use_batch:
        batch_requests = [
            build_batch_request(
                custom_id=custom_id,
                model_id=model_id,
                user_content=prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                seed=args.seed,
                use_gemini=args.use_gemini,
            )
            for custom_id, prompt in requests
        ]
        print(f"Submitting batch ({len(batch_requests)} requests)...")
        return run_batch(
            model_id,
            batch_requests,
            batch_file,
            description=description,
            use_gemini=args.use_gemini,
        )

    results: dict[str, str] = {}
    for custom_id, prompt in requests:
        print(f"  Generating {custom_id}...")
        results[custom_id] = generate_response(
            model_id,
            args.use_openrouter,
            args.use_gemini,
            prompt,
            args.max_tokens,
            args.temperature,
            args.seed,
            args.thinking,
        )
    return results


def _run_planner(args, mode_module, model_id, output_dir, dataset_dir, use_batch):
    print("Building prompts...")
    requests: list[tuple[str, list[dict]]] = []
    problem_meta: dict[str, dict] = {}

    for dataset_problem_dir in get_problem_dirs(dataset_dir, args.num_samples):
        (
            name,
            output_problem_dir,
            gt_domain,
            gt_problem,
            gt_domain_path,
            gt_problem_path,
        ) = setup_problem(dataset_problem_dir, output_dir)

        init_paths, goal_paths = extract_dataset_info(dataset_problem_dir)

        prompt = mode_module.build_prompt(gt_domain, init_paths, goal_paths)
        (output_problem_dir / "prompt.txt").write_text(json.dumps(prompt, indent=4))

        requests.append((f"{name}__plan", prompt))
        problem_meta[name] = {
            "output_problem_dir": output_problem_dir,
            "gt_domain_path": gt_domain_path,
            "gt_problem_path": gt_problem_path,
        }

    if not requests:
        print("No problems found in dataset directory.")
        return

    results = _generate_responses(
        args,
        model_id,
        requests,
        use_batch=use_batch,
        batch_file=output_dir / "batch_input_planner.jsonl",
        description=f"planner_{args.dataset}",
    )

    print("Processing results...")
    statistics_summary: dict[str, dict] = {}
    for name, meta in problem_meta.items():
        statistics_summary[name] = {}

        response = results.get(f"{name}__plan", "")
        if not response:
            print(f"  WARNING: no response for {name}, skipping.")
            statistics_summary[name]["plan_success"] = False
            continue

        output_problem_dir = meta["output_problem_dir"]
        _, plan_str = extract_output_from_response(response)
        plan = normalize_plan(plan_str)
        (output_problem_dir / "plan.txt").write_text(plan)
        (output_problem_dir / "response.txt").write_text(response)

        plan_success, _ = validate_plan(
            meta["gt_domain_path"], meta["gt_problem_path"], plan
        )
        statistics_summary[name]["plan_success"] = plan_success

        eval_report = get_eval_report_planner(statistics_summary)
        with open(output_dir / "eval_report.json", "w") as f:
            json.dump(eval_report, f, indent=4)


def _run_formalizer(
    args, mode_module, model_id, output_dir, dataset_dir, downward_dir, use_batch
):
    print("Building prompts...")
    requests: list[tuple[str, list[dict]]] = []
    problem_meta: dict[str, dict] = {}

    for dataset_problem_dir in get_problem_dirs(dataset_dir, args.num_samples):
        (
            name,
            output_problem_dir,
            gt_domain,
            gt_problem,
            gt_domain_path,
            gt_problem_path,
        ) = setup_problem(dataset_problem_dir, output_dir)

        init_paths, goal_paths = extract_dataset_info(dataset_problem_dir)
        
        init_prompt = mode_module.build_grounded_prompt(gt_domain, init_paths)
        (output_problem_dir / "init_prompt.txt").write_text(
            json.dumps(init_prompt, indent=4)
        )
        requests.append((f"{name}__init", init_prompt))
        
        goal_prompt = mode_module.build_grounded_prompt(gt_domain, goal_paths)
        (output_problem_dir / "goal_prompt.txt").write_text(
            json.dumps(goal_prompt, indent=4)
        )
        requests.append((f"{name}__goal", goal_prompt))
        
        problem_meta[name] = {
            "output_problem_dir": output_problem_dir,
            "gt_domain": gt_domain,
            "gt_problem": gt_problem,
            "gt_domain_path": gt_domain_path,
            "gt_problem_path": gt_problem_path,
        }

    if not requests:
        print("No problems found in dataset directory.")
        return

    results = _generate_responses(
        args,
        model_id,
        requests,
        use_batch=use_batch,
        batch_file=output_dir / "batch_input_formalizer.jsonl",
        description=f"formalizer_{args.dataset}",
    )

    print("Processing results...")
    statistics_summary: dict[str, dict] = {}
    for name, meta in problem_meta.items():
        statistics_summary[name] = {}

        init_response = results.get(f"{name}__init", "")
        goal_response = results.get(f"{name}__goal", "")
        if not init_response or not goal_response:
            print(f"  WARNING: missing response for {name}, skipping.")
            statistics_summary[name]["plan_success"] = False
            continue

        gt_domain = meta["gt_domain"]
        gt_problem = meta["gt_problem"]
        gt_domain_path = meta["gt_domain_path"]
        gt_problem_path = meta["gt_problem_path"]
        output_problem_dir = meta["output_problem_dir"]

        # Assemble PDDL problem
        (
            problem,
            init_response_extracted,
            goal_response_extracted,
        ) = assemble_pddl_problem(
            init_response,
            goal_response,
            set(_BLOCKSWORLD_OBJECTS),
            gt_domain,
            gt_problem,
        )
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
        statistics_summary[name].update(
            compute_precision_recall_f1(gt_problem, problem)
        )

        # Save evaluation report
        eval_report = get_eval_report_formalizer(statistics_summary)
        with open(output_dir / "eval_report.json", "w") as f:
            json.dump(eval_report, f, indent=4)


def run_pipeline(
    args, mode_module, kind, model_id, output_dir, dataset_dir, downward_dir, use_batch
):
    if kind == "planner":
        _run_planner(args, mode_module, model_id, output_dir, dataset_dir, use_batch)
    else:
        _run_formalizer(
            args,
            mode_module,
            model_id,
            output_dir,
            dataset_dir,
            downward_dir,
            use_batch,
        )
