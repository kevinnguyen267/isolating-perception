from pathlib import Path

from utils.parse import extract_normalized_problem


def parse_problem(filepath: Path) -> dict[str, set[str]]:
    with open(filepath) as f:
        text = f.read()
    _, _, objects, init, goal = extract_normalized_problem(text)
    return {
        "objects": objects,
        "init": init,
        "goal": goal,
    }


def compute_statistics(
    gt_problem_path: Path, pred_problem_path: Path
) -> dict[str, dict[str, float]]:
    """Compute precision, recall, and F1 for objects, init state, and goal state."""

    ground_truth = parse_problem(gt_problem_path)
    predicted = parse_problem(pred_problem_path)

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
