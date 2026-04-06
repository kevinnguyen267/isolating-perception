from models.formalizer import (
    assemble_pddl_problem,
    build_grounding_prompt_from_instruction,
    build_grounding_prompt_img,
    build_grounding_prompt_imgs,
    build_merge_grounded_prompt,
    build_merge_scene_graph_prompt,
    build_scene_graph_prompt_img,
    extract_dataset_info,
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
        objects, predicates, image_paths, instruction = extract_dataset_info(
            dataset_problem_dir, gt_domain
        )

        # Intermediate representation only affects the init prompt
        goal_prompt = build_grounding_prompt_from_instruction(
            objects, predicates, instruction
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

        # Build different prompts depending on intermediate representation choice
        if args.intermediate == "none":
            if len(image_paths) == 1:
                init_prompt = build_grounding_prompt_img(
                    objects, predicates, image_paths[0]
                )
            else:
                init_prompt = build_grounding_prompt_imgs(
                    objects, predicates, image_paths
                )

            num_images = 0  # Used for intermediate representation bookkeeping
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
        else:
            if args.intermediate == "scene_graph":
                per_image_prompts = [
                    build_scene_graph_prompt_img(objects, predicates, img_path)
                    for img_path in image_paths
                ]
            elif args.intermediate == "pddl":
                per_image_prompts = [
                    build_grounding_prompt_img(objects, predicates, img_path)
                    for img_path in image_paths
                ]
            else:
                raise ValueError(
                    f"Invalid intermediate representation: {args.intermediate}"
                )

            num_images = len(per_image_prompts)
            for img_idx, img_prompt in enumerate(per_image_prompts):
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
            "predicates": predicates,
            "num_images": num_images,
        }

    if not batch_requests:
        print("No problems found in dataset directory.")
        return

    # Submit batch 1: (one or multiple) init + goal prompts
    print(f"Submitting batch 1 ({len(batch_requests)} requests)...")
    batch_file = output_dir / "batch_input_formalizer.jsonl"
    results = run_batch(
        model_id, batch_requests, batch_file, description=f"formalizer_{args.dataset}"
    )

    # If using an intermediate representation, submit batch 2: merge prompts
    merge_results = {}
    if args.intermediate != "none":
        merge_requests = []
        for name, meta in problem_meta.items():
            per_image_responses = []
            for img_idx in range(meta["num_images"]):
                resp = results.get(f"{name}__init_img{img_idx}", "")
                per_image_responses.append(resp)
            meta["per_image_responses"] = per_image_responses

            if all(per_image_responses):
                if args.intermediate == "scene_graph":
                    merge_prompt = build_merge_scene_graph_prompt(
                        meta["objects"], meta["predicates"], per_image_responses
                    )
                elif args.intermediate == "pddl":
                    merge_prompt = build_merge_grounded_prompt(
                        meta["objects"], meta["predicates"], per_image_responses
                    )
                else:
                    raise ValueError(
                        f"Invalid intermediate representation: {args.intermediate}"
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

        if merge_requests:
            print(f"Submitting batch 2 - merge ({len(merge_requests)} requests)...")
            merge_batch_file = output_dir / "batch_input_formalizer_merge.jsonl"
            merge_results = run_batch(
                model_id,
                merge_requests,
                merge_batch_file,
                description=f"formalizer_merge_{args.dataset}",
            )

    # Process results
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

        if args.intermediate == "none":
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
            per_image_responses,
            statistics_summary,
            output_dir,
            output_problem_dir,
        )
