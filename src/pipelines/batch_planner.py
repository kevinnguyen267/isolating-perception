import json

from plans.validate_plan import validate_plan
from utils.batch import build_batch_request, run_batch
from utils.helpers import extract_dataset_info, setup_problem
from utils.parse import (
    extract_output_from_response,
    get_present_objects,
    normalize_plan,
)
from utils.statistics import get_eval_report_planner


def main(args, mode_module, model_id, output_dir, dataset_dir):
    # Build prompts for all problems and collect metadata
    print("Building prompts...")
    batch_requests = []
    problem_metadata: dict[str, dict] = {}

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
        
        objects = get_present_objects(dataset_problem_dir)
        image_paths, instruction = extract_dataset_info(dataset_problem_dir)
        
        prompt = mode_module.build_prompt(objects, gt_domain, image_paths, instruction)
        custom_id = f"{name}__plan"

        batch_requests.append(
            build_batch_request(
                custom_id=custom_id,
                model_id=model_id,
                user_content=prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                seed=args.seed,
            )
        )
        problem_metadata[name] = {
            "output_problem_dir": output_problem_dir,
            "gt_domain_path": gt_domain_path,
            "gt_problem_path": gt_problem_path,
        }

    if not batch_requests:
        print("No problems found in dataset directory.")
        return

    # Submit batch requests to VLM and collect responses
    print(f"Submitting batch ({len(batch_requests)} requests)...")
    batch_file = output_dir / "batch_input_planner.jsonl"
    results = run_batch(
        model_id, batch_requests, batch_file, description=f"planner_{args.dataset}"
    )

    # Process results, validate plans, and compile statistics
    print("Processing results...")
    statistics_summary = {}

    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if not dataset_problem_dir.is_dir():
            continue
        name = dataset_problem_dir.name
        meta = problem_metadata[name]
        output_problem_dir = meta["output_problem_dir"]
        statistics_summary[name] = {}

        response = results.get(f"{name}__plan", "")
        if not response:
            print(f"  WARNING: no response for {name}, skipping.")
            statistics_summary[name]["plan_success"] = False
            continue

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
