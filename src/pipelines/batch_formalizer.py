from pipelines.synchronous import solve_by_formalization
from utils.batch import build_batch_request, run_batch
from utils.helpers import assemble_pddl_problem, extract_dataset_info, setup_problem
from utils.parse import get_present_objects


def main(args, mode_module, model_id, output_dir, dataset_dir, downward_dir):
    # Build prompts for all problems and collect metadata
    print("Building prompts...")
    batch_requests = []
    problem_meta: dict[str, dict] = {}

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
        image_paths, text_paths, instruction = extract_dataset_info(dataset_problem_dir)

        # Goal state
        goal_prompt = mode_module.build_goal_prompt(objects, gt_domain, instruction)
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

        # Init state - mode_module decides whether to generate single prompt or multiple per-image prompts with merge step
        init_prompts = mode_module.build_init_prompts(objects, gt_domain, image_paths, text_paths)
        num_images = len(init_prompts)
        if num_images == 1:
            batch_requests.append(
                build_batch_request(
                    custom_id=f"{name}__init",
                    model_id=model_id,
                    user_content=init_prompts[0],
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    seed=args.seed,
                )
            )
        else:
            for img_idx, img_prompt in enumerate(init_prompts):
                batch_requests.append(
                    build_batch_request(
                        custom_id=f"{name}__init_img{img_idx}",
                        model_id=model_id,
                        user_content=img_prompt,
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
            "domain_text": gt_domain,
            "image_paths": image_paths,
            "num_images": num_images,
        }

    if not batch_requests:
        print("No problems found in dataset directory.")
        return

    # Submit batch 1: init + goal state prompts
    print(f"Submitting batch 1 ({len(batch_requests)} requests)...")
    batch_file = output_dir / "batch_input_formalizer.jsonl"
    results = run_batch(
        model_id, batch_requests, batch_file, description=f"formalizer_{args.dataset}"
    )

    # If any problems needed merging, submit batch 2
    merge_requests = []
    for name, meta in problem_meta.items():
        if meta["num_images"] == 1:
            continue  # No merge needed

        per_image_responses = []
        for img_idx in range(meta["num_images"]):
            resp = results.get(f"{name}__init_img{img_idx}", "")
            per_image_responses.append(resp)
        meta["per_image_responses"] = per_image_responses

        if all(per_image_responses):
            merge_prompt = mode_module.build_merge_prompt(
                meta["objects"], meta["domain_text"], meta["image_paths"], per_image_responses
            )
            merge_requests.append(
                build_batch_request(
                    custom_id=f"{name}__init_merge",
                    model_id=model_id,
                    user_content=merge_prompt,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    seed=args.seed,
                )
            )

    merge_results = {}
    if merge_requests:
        print(f"Submitting batch 2 - merge ({len(merge_requests)} requests)...")
        merge_batch_file = output_dir / "batch_input_formalizer_merge.jsonl"
        merge_results = run_batch(
            model_id,
            merge_requests,
            merge_batch_file,
            description=f"formalizer_merge_{args.dataset}",
        )

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

        if meta["num_images"] == 1:
            init_response = results.get(f"{name}__init", "")
            per_image_responses = None
        else:
            init_response = merge_results.get(f"{name}__init_merge", "")
            per_image_responses = meta.get("per_image_responses")
        goal_response = results.get(f"{name}__goal", "")

        if not init_response or not goal_response:
            print(f"  WARNING: missing response for {name}, skipping.")
            statistics_summary[name]["plan_success"] = False
            continue

        # Assemble the PDDL problem
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
