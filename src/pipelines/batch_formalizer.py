from models.formalizer import (
    assemble_pddl_problem,
    build_formalizer_prompts,
)
from pipelines.synchronous import solve_by_formalization
from utils.batch import build_batch_request, run_batch
from utils.helpers import setup_problem


def main(args, model_id, output_dir, dataset_dir, downward_dir):
    # Build prompts for all problems and collect metadata
    print("Building prompts...")
    batch_requests = []
    problem_meta: dict[str, dict] = {}

    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if not dataset_problem_dir.is_dir():
            continue
        name = dataset_problem_dir.name

        (
            name,
            output_problem_dir,
            gt_domain,
            gt_problem,
            gt_domain_path,
            gt_problem_path,
        ) = setup_problem(dataset_problem_dir, output_dir)

        init_prompt, goal_prompt, objects = build_formalizer_prompts(
            dataset_problem_dir, gt_domain
        )

        batch_requests.append(
            build_batch_request(
                custom_id=f"{name}__init",
                model_id=model_id,
                user_content=init_prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                seed=args.seed,
            )
        )
        batch_requests.append(
            build_batch_request(
                custom_id=f"{name}__goal",
                model_id=model_id,
                user_content=goal_prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                seed=args.seed,
            )
        )

        problem_meta[name] = {
            "dataset_problem_dir": dataset_problem_dir,
            "output_problem_dir": output_problem_dir,
            "gt_domain": gt_domain,
            "gt_problem": gt_problem,
            "gt_domain_path": gt_domain_path,
            "gt_problem_path": gt_problem_path,
            "objects": objects,
        }

    if not batch_requests:
        print("No problems found in dataset directory.")
        return

    # Submit batch requests to VLM and collect responses
    print(f"Submitting batch ({len(batch_requests)} requests)...")
    batch_file = output_dir / "batch_input_formalizer.jsonl"
    results = run_batch(
        model_id, batch_requests, batch_file, description=f"formalizer_{args.dataset}"
    )

    # Process results, run Fast Downward, reprompt failures
    print("Processing results...")
    statistics_summary = {}

    for dataset_problem_dir in sorted(dataset_dir.iterdir()):
        if not dataset_problem_dir.is_dir():
            continue
        name = dataset_problem_dir.name
        meta = problem_meta[name]
        output_problem_dir = meta["output_problem_dir"]
        gt_domain = meta["gt_domain"]
        gt_problem = meta["gt_problem"]
        gt_domain_path = meta["gt_domain_path"]
        gt_problem_path = meta["gt_problem_path"]
        objects = meta["objects"]
        statistics_summary[name] = {}

        init_response = results.get(f"{name}__init", "")
        goal_response = results.get(f"{name}__goal", "")
        if not init_response or not goal_response:
            print(f"  WARNING: missing response for {name}, skipping.")
            statistics_summary[name]["plan_success"] = False
            continue

        # Assemble the PDDL problem from batch responses
        (
            problem,
            _,
            _,
            init_cleanup_response,
            goal_cleanup_response,
        ) = assemble_pddl_problem(
            init_response, goal_response, objects, gt_domain, gt_problem
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
