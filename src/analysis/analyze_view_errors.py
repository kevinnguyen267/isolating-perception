"""Analyze how each mode reconciles conflicting views on BW-PO-DEPTH.

Every block placement (problem x state x block) is labelled by what the two views of a
reference perceiver run claim, each on its own, that the block rests on:

    agree      both views place it identically
    one_view   exactly one view places it
    ambiguous  both views place it and disagree
    unseen     no view places it

On ambiguous placements, a mode either selects the correct view, selects the wrong view,
predicts a third support neither view claims, or leaves the block unplaced. Accuracy is the
share selecting the correct view, excluding unplaced blocks. Planner states are recovered
from its plan, so only blocks the plan touches are placed (see `placed`).

Example:
    python src/analysis/analyze_view_errors.py --compare_label_model Gemma-4-31B_no_thinking
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/

from analysis.common import (
    MISSING,
    latest_run,
    parse_gt,
    predicted_states,
    support_map,
)
from utils.parse import extract_image_views
from utils.stack_solver import _view_to_predicates

LABELS = ("agree", "one_view", "ambiguous", "unseen")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze cross-view reconciliation on ambiguous block placements"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="blocksworld_depth",
        help="Dataset under results/ to analyze",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["planner", "formalizer", "perceiver"],
        help="Modes to analyze",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "Gemma-4-31B_thinking",
            "Qwen3.5-122B-A10B_thinking",
            "Gemini-3.1-Pro",
        ],
        help="Model directories to analyze",
    )
    parser.add_argument(
        "--label_model",
        type=str,
        default="Gemini-3.1-Pro",
        help="Model whose perceiver run's per-view responses define the labels",
    )
    parser.add_argument(
        "--compare_label_model",
        type=str,
        default=None,
        help="Second perceiver model to measure label agreement against",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Glob patterns of run directories to ignore when picking the latest run",
    )
    return parser.parse_args()


def problems(run_dir: Path):
    """Yield (problem_dir, blocks, robot, gt_init, gt_goal) for each problem of a run."""
    for problem_dir in sorted((run_dir / "problems").glob("problem_*")):
        gt_path = problem_dir / "gt_problem.pddl"
        if gt_path.exists():
            yield problem_dir, *parse_gt(gt_path.read_text())


def view_labels(run_dir: Path) -> dict:
    """Return {(problem, state): (labels, claims)} from a perceiver run's per-view responses.

    `labels` maps each block to one of LABELS; `claims` maps it to the set of supports the
    views claim for it.
    """
    out = {}
    for problem_dir, blocks, _, _, _ in problems(run_dir):
        for state in ("init", "goal"):
            response = problem_dir / f"{state}_response.txt"
            if not response.exists():
                continue
            views = [
                support_map(_view_to_predicates(view), blocks)
                for view in extract_image_views(response.read_text())
            ]
            if not views:
                continue
            labels, claims = {}, {}
            for b in blocks:
                placed = [v[b] for v in views if v[b] != MISSING]
                claims[b] = set(placed)
                if not placed:
                    labels[b] = "unseen"
                elif len(set(placed)) > 1:
                    labels[b] = "ambiguous"
                elif len(placed) == len(views):
                    labels[b] = "agree"
                else:
                    labels[b] = "one_view"
            out[(problem_dir.name, state)] = (labels, claims)
    return out


def report_labels(label_run: Path, labels: dict) -> None:
    counts = Counter()
    truth_claimed = 0
    for problem_dir, blocks, _, gt_init, gt_goal in problems(label_run):
        for state, facts in (("init", gt_init), ("goal", gt_goal)):
            if (problem_dir.name, state) not in labels:
                continue
            block_labels, claims = labels[(problem_dir.name, state)]
            truth = support_map(facts, blocks)
            for b in blocks:
                counts[block_labels[b]] += 1
                if block_labels[b] == "ambiguous":
                    truth_claimed += truth[b] in claims[b]

    total = sum(counts.values())
    print(f"Labels from {label_run} ({total} placements)")
    for label in LABELS:
        print(f"  {label:<10} {counts[label]:>5}  ({counts[label] / total:.1%})")
    if counts["ambiguous"]:
        print(
            f"  True support is one of the views' claims on "
            f"{truth_claimed / counts['ambiguous']:.1%} of ambiguous placements"
        )


def report_agreement(labels: dict, other: dict, other_run: Path) -> None:
    """Report how often a second run agrees on which placements are ambiguous."""
    same = total = 0
    for key, (block_labels, _) in labels.items():
        if key not in other:
            continue
        for b, label in block_labels.items():
            total += 1
            same += (other[key][0][b] == "ambiguous") == (label == "ambiguous")
    print(
        f"Ambiguous/unambiguous label agreement with {other_run}: "
        f"{same / total:.1%} of {total} placements"
    )


def analyze_run(run_dir: Path, mode: str, labels: dict) -> dict:
    """Count placed blocks and the outcome on each ambiguous placement of one run."""
    counts = Counter()
    for problem_dir, blocks, robot, gt_init, gt_goal in problems(run_dir):
        predicted = predicted_states(problem_dir, mode, blocks, robot)
        if predicted is None:
            continue
        for state, gt_facts, facts in zip(
            ("init", "goal"), (gt_init, gt_goal), predicted
        ):
            truth, pred = support_map(gt_facts, blocks), support_map(facts, blocks)
            block_labels, claims = labels.get((problem_dir.name, state), ({}, {}))
            for b in blocks:
                counts["placements"] += 1
                counts["placed"] += pred[b] != MISSING
                if block_labels.get(b) != "ambiguous":
                    continue
                if pred[b] == MISSING:
                    counts["unplaced"] += 1
                elif pred[b] == truth[b]:
                    counts["correct"] += 1
                elif pred[b] in claims[b]:
                    counts["wrong_view"] += 1
                else:
                    counts["neither"] += 1
    return counts


def main():
    args = parse_args()
    results_dir = Path("results") / args.dataset

    label_run = latest_run(results_dir / "perceiver" / args.label_model, args.exclude)
    if label_run is None:
        raise FileNotFoundError(f"No perceiver run found for {args.label_model}")
    labels = view_labels(label_run)
    report_labels(label_run, labels)
    if args.compare_label_model:
        other_run = latest_run(
            results_dir / "perceiver" / args.compare_label_model, args.exclude
        )
        if other_run is None:
            raise FileNotFoundError(
                f"No perceiver run found for {args.compare_label_model}"
            )
        report_agreement(labels, view_labels(other_run), other_run)

    print("\nSelection on ambiguous placements (accuracy excludes unplaced blocks)")
    header = ["placed", "n", "correct", "wrong_view", "neither", "unplaced", "accuracy"]
    print(f"{'mode':<12}{'model':<30}" + "".join(f"{h:>11}" for h in header))
    for mode in args.modes:
        for model in args.models:
            run_dir = latest_run(results_dir / mode / model, args.exclude)
            if run_dir is None:
                print(f"{mode:<12}{model:<30}  no run found")
                continue
            c = analyze_run(run_dir, mode, labels)
            n = c["correct"] + c["wrong_view"] + c["neither"] + c["unplaced"]
            committed = n - c["unplaced"]
            cells = [f"{c['placed'] / c['placements']:.1%}", str(n)]
            cells += [f"{c[k] / n:.1%}" if n else "-" for k in header[2:6]]
            cells.append(f"{c['correct'] / committed:.1%}" if committed else "-")
            print(f"{mode:<12}{model:<30}" + "".join(f"{cell:>11}" for cell in cells))


if __name__ == "__main__":
    main()
