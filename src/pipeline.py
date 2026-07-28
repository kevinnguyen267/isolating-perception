import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    extract_normalized_problem,
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
from utils.usage import get_completion_tokens
from utils.vlm import generate_response


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

    def _one(
        custom_id: str,
        prompt: list[dict],
        max_retries: int = 5,
        initial_delay: float = 2.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> str:
        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                return generate_response(
                    model_id,
                    args.use_openrouter,
                    args.use_gemini,
                    prompt,
                    args.max_tokens,
                    args.temperature,
                    args.seed,
                    args.thinking,
                )
            except Exception as e:
                if attempt == max_retries:
                    raise
                print(
                    f"  {custom_id} failed (attempt {attempt}/{max_retries}): {e!r}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
        raise RuntimeError("Unreachable")

    # Use concurrency for local vLLM
    is_vllm = not (
        args.use_openrouter or args.use_gemini or model_id.lower().startswith("gpt")
    )
    concurrency = max(1, getattr(args, "concurrency", 1)) if is_vllm else 1
    concurrency = min(concurrency, len(requests))

    results: dict[str, str] = {}
    if concurrency == 1:
        for custom_id, prompt in requests:
            print(f"  Generating {custom_id}...")
            results[custom_id] = _one(custom_id, prompt)
        return results

    print(f"  Generating {len(requests)} requests (concurrency={concurrency})...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_id = {
            executor.submit(_one, custom_id, prompt): custom_id
            for custom_id, prompt in requests
        }
        for future in as_completed(future_to_id):
            custom_id = future_to_id[future]
            try:
                results[custom_id] = future.result()
            except Exception as e:
                print(f"  ERROR: {custom_id} failed after all retries: {e!r}")
                results[custom_id] = ""
            print(f"  Done {custom_id} ({len(results)}/{len(requests)})")
    n_failed = sum(1 for v in results.values() if not v)
    if n_failed:
        print(
            f"  WARNING: {n_failed}/{len(requests)} requests failed (empty response)."
        )
    return results


def _process_in_parallel(
    items: list[tuple[str, dict]],
    process_one,
    report_fn,
    output_dir: Path,
    max_workers: int | None,
) -> dict[str, dict]:
    """Run process_one(name, meta) for every problem in parallel."""
    n = len(items)
    cap = max_workers if max_workers and max_workers > 0 else (os.cpu_count() or 1)
    workers = min(n, cap)
    print(f"Processing results ({n} problems, workers={workers})...")

    statistics_summary: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_name = {
            executor.submit(process_one, name, meta): name for name, meta in items
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                statistics_summary[name] = future.result()
            except Exception as e:
                print(f"  ERROR processing {name}: {e!r}")
                statistics_summary[name] = {"plan_success": False}
            print(f"  Done {name} ({len(statistics_summary)}/{n})")
            with open(output_dir / "eval_report.json", "w") as f:
                json.dump(report_fn(statistics_summary), f, indent=4)

    ordered = {name: statistics_summary[name] for name, _ in items}
    with open(output_dir / "eval_report.json", "w") as f:
        json.dump(report_fn(ordered), f, indent=4)
    return ordered


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

        prompt = mode_module.build_prompt(gt_domain, gt_problem, init_paths, goal_paths, args.dataset)
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

    def _process_one(name: str, meta: dict) -> dict:
        stats: dict = {}

        response = results.get(f"{name}__plan", "")
        if not response:
            print(f"  WARNING: no response for {name}, skipping.")
            stats["plan_success"] = False
            return stats

        output_problem_dir = meta["output_problem_dir"]
        _, plan_str = extract_output_from_response(response, args.mode)
        plan = normalize_plan(plan_str)
        (output_problem_dir / "plan.txt").write_text(plan)
        (output_problem_dir / "response.txt").write_text(response)

        plan_success, _ = validate_plan(
            meta["gt_domain_path"], meta["gt_problem_path"], plan
        )
        stats["plan_success"] = plan_success
        return stats

    completion_tokens = get_completion_tokens()
    _process_in_parallel(
        list(problem_meta.items()),
        _process_one,
        lambda summary: get_eval_report_planner(summary, completion_tokens),
        output_dir,
        max_workers=getattr(args, "processing_workers", None),
    )


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

        init_prompt = mode_module.build_grounded_prompt(
            gt_domain, gt_problem, init_paths, args.dataset
        )
        (output_problem_dir / "init_prompt.txt").write_text(
            json.dumps(init_prompt, indent=4)
        )
        requests.append((f"{name}__init", init_prompt))

        goal_prompt = mode_module.build_grounded_prompt(
            gt_domain, gt_problem, goal_paths, args.dataset
        )
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
            "objects": extract_normalized_problem(gt_problem)[2],
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

    def _process_one(name: str, meta: dict) -> dict:
        stats: dict = {}

        init_response = results.get(f"{name}__init", "")
        goal_response = results.get(f"{name}__goal", "")
        if not init_response or not goal_response:
            print(f"  WARNING: missing response for {name}, skipping.")
            stats["plan_success"] = False
            return stats

        gt_domain = meta["gt_domain"]
        gt_problem = meta["gt_problem"]
        gt_domain_path = meta["gt_domain_path"]
        gt_problem_path = meta["gt_problem_path"]
        output_problem_dir = meta["output_problem_dir"]

        (output_problem_dir / "init_response.txt").write_text(init_response)
        (output_problem_dir / "goal_response.txt").write_text(goal_response)

        # Assemble PDDL problem
        (
            problem,
            init_response_extracted,
            goal_response_extracted,
        ) = assemble_pddl_problem(
            init_response,
            goal_response,
            meta["objects"],
            gt_domain,
            gt_problem,
            args.mode,
        )
        problem = normalize_problem(problem)
        (output_problem_dir / "problem.pddl").write_text(problem)

        (output_problem_dir / "init_response_extracted.txt").write_text(
            init_response_extracted
        )
        (output_problem_dir / "goal_response_extracted.txt").write_text(
            goal_response_extracted
        )

        # Solve the generated problem using Fast Downward and validate if successful
        downward_success, _, plan = find_plan(gt_domain, problem, downward_dir)
        if not downward_success:
            stats["downward_success"] = False
            plan_success = False
        else:
            plan = normalize_plan(plan)
            (output_problem_dir / "plan.txt").write_text(plan)

            plan_success, _ = validate_plan(gt_domain_path, gt_problem_path, plan)
            stats["plan_success"] = plan_success

        # Determine whether the plan failed due to init or goal state
        if not plan_success:
            stats.update(
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
        stats.update(compute_precision_recall_f1(gt_problem, problem))
        return stats

    completion_tokens = get_completion_tokens()
    _process_in_parallel(
        list(problem_meta.items()),
        _process_one,
        lambda summary: get_eval_report_formalizer(summary, completion_tokens),
        output_dir,
        max_workers=getattr(args, "processing_workers", None),
    )


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
