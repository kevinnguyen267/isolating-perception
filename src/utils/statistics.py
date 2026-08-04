from pathlib import Path

from plans.find_plan import find_plan
from plans.validate_plan import validate_plan
from utils.parse import (
    create_problem_from_sections,
    extract_normalized_problem,
    has_object_facts,
    normalize_problem,
)


def _extract_problem(problem: str) -> dict[str, set[str]]:
    _, _, objects, init, goal = extract_normalized_problem(problem)
    return {
        "objects": objects,
        "init": init,
        "goal": goal,
    }


def compute_precision_recall_f1(
    gt_problem: str, problem: str
) -> dict[str, dict[str, float]]:
    """Compute precision, recall, and F1 for objects, init state, and goal state."""
    ground_truth = _extract_problem(gt_problem)
    predicted = _extract_problem(problem)

    statistics = {}
    for key in ["objects", "init", "goal"]:
        tp = len(ground_truth[key] & predicted[key])
        fp = len(predicted[key] - ground_truth[key])
        fn = len(ground_truth[key] - predicted[key])

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )

        statistics[key] = {
            "tp": tp,
            "fp": fp,
            "fp_values": list(predicted[key] - ground_truth[key]),
            "fn": fn,
            "fn_values": list(ground_truth[key] - predicted[key]),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return statistics


def compute_plan_success_with_ground_truth(
    gt_problem: str,
    problem: str,
    gt_domain: str,
    gt_domain_path: Path,
    gt_problem_path: Path,
    downward_dir: Path,
) -> dict[str, bool]:
    """For failed plans, determine whether the failure was due to init state, goal state, or both by
    replacing the init and goal sections of the generated problem with the ground truth and re-evaluating plan success."""
    result = {
        "plan_failed_due_to_init": False,
        "plan_failed_due_to_goal": False,
        "plan_failed_due_to_both": False,
    }

    _, _, _, gt_init, gt_goal = extract_normalized_problem(gt_problem)
    prob_name, domain_name, objects, init, goal = extract_normalized_problem(problem)

    tests = [
        ("plan_failed_due_to_init", gt_init, goal),
        ("plan_failed_due_to_goal", init, gt_goal),
        ("plan_failed_due_to_both", gt_init, gt_goal),
    ]

    for test_name, test_init, test_goal in tests:
        if not (has_object_facts(test_init) and has_object_facts(test_goal)):
            continue

        test_problem = normalize_problem(
            create_problem_from_sections(
                prob_name, domain_name, objects, test_init, test_goal
            )
        )
        downward_success, _, plan = find_plan(gt_domain, test_problem, downward_dir)
        if downward_success:
            plan_success, _ = validate_plan(gt_domain_path, gt_problem_path, plan)
            if plan_success:
                result[test_name] = plan_success
                break

    return result


def compute_completion_token_stats(completion_tokens: list[int] | None) -> dict:
    """Mean and median completion tokens over all generation calls in the run."""
    values = sorted(completion_tokens or [])
    if not values:
        return {"mean_completion_tokens": 0.0, "median_completion_tokens": 0.0}

    n = len(values)
    mid = n // 2
    return {
        "mean_completion_tokens": sum(values) / n,
        "median_completion_tokens": (
            values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2
        ),
    }


def get_eval_report_planner(
    statistics_summary: dict,
    completion_tokens: list[int] | None = None,
) -> dict:
    """Generate an evaluation report summarizing the statistics for all problems."""
    if not statistics_summary:
        return {}

    passed_problems = [
        p for p in statistics_summary.values() if p.get("plan_success", False)
    ]
    failed_problems = [
        p for p in statistics_summary.values() if not p.get("plan_success", False)
    ]

    num_problems = len(statistics_summary)
    num_passed = len(passed_problems)
    num_failed = len(failed_problems)

    statistics_summary_avg = {
        "plan_success_rate": num_passed / num_problems if num_problems > 0 else 0.0,
        **compute_completion_token_stats(completion_tokens),
        "num_problems": num_problems,
        "num_plans_passed": num_passed,
        "num_plans_failed": num_failed,
        "problems_passed": [
            name
            for name, p in statistics_summary.items()
            if p.get("plan_success", False)
        ],
        "problems_failed": [
            name
            for name, p in statistics_summary.items()
            if not p.get("plan_success", False)
        ],
    }

    return {
        "average_statistics": statistics_summary_avg,
    }


def get_eval_report_formalizer(
    statistics_summary: dict,
    completion_tokens: list[int] | None = None,
) -> dict:
    """Generate an evaluation report summarizing the statistics for all problems."""
    if not statistics_summary:
        return {}

    passed_problems = [
        p for p in statistics_summary.values() if p.get("plan_success", False)
    ]
    failed_problems = [
        p for p in statistics_summary.values() if not p.get("plan_success", False)
    ]

    num_problems = len(statistics_summary)
    num_passed = len(passed_problems)
    num_failed = len(failed_problems)

    def _compute_avg_metrics(probs):
        avg_metrics = {}

        for key in ("objects", "init", "goal"):
            valid_probs = [p[key] for p in probs if key in p]
            n = len(valid_probs) if len(valid_probs) > 0 else 1
            avg_metrics[key] = {
                "precision": sum(vp.get("precision", 0.0) for vp in valid_probs) / n,
                "recall": sum(vp.get("recall", 0.0) for vp in valid_probs) / n,
                "f1": sum(vp.get("f1", 0.0) for vp in valid_probs) / n,
            }

        return avg_metrics

    statistics_summary_avg = {
        "plan_success_rate": num_passed / num_problems if num_problems > 0 else 0.0,
        **compute_completion_token_stats(completion_tokens),
        "num_problems": num_problems,
        "num_plans_reprompted": sum(
            p.get("num_reprompts", 0) > 0 for p in statistics_summary.values()
        ),
        "num_plans_successfully_reprompted": sum(
            p.get("num_reprompts", 0) > 0
            and p.get("plan_success", False)
            for p in statistics_summary.values()
        ),
        "num_plans_passed": num_passed,
        "problems_passed": [
            name
            for name, p in statistics_summary.items()
            if p.get("plan_success", False)
        ],
        "num_plans_failed": num_failed,
        "problems_failed": [
            name
            for name, p in statistics_summary.items()
            if not p.get("plan_success", False)
        ],
        "num_plans_failed_due_to_init": sum(
            p.get("plan_failed_due_to_init", False) for p in failed_problems
        ),
        "num_plans_failed_due_to_goal": sum(
            p.get("plan_failed_due_to_goal", False) for p in failed_problems
        ),
        "num_plans_failed_due_to_both": sum(
            p.get("plan_failed_due_to_both", False) for p in failed_problems
        ),
        **_compute_avg_metrics(statistics_summary.values()),
    }

    statistics_summary_avg_passed = {
        **_compute_avg_metrics(passed_problems),
    }
    statistics_summary_avg_failed = {
        **_compute_avg_metrics(failed_problems),
    }

    return {
        "average_statistics": statistics_summary_avg,
        "average_statistics_passed_cases": statistics_summary_avg_passed,
        "average_statistics_failed_cases": statistics_summary_avg_failed,
        "individual_statistics": statistics_summary,
    }
