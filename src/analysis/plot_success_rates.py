"""Summarize plan success and token cost per dataset, mode, and model.

Reads the latest eval_report.json under results/<dataset>/<mode>/<model>/ for each
combination, writes a CSV, and plots plan success rate and mean and median completion
tokens. Reports count tokens per generation call, so modes that prompt separately for the
init and goal state are scaled to tokens per problem. Tokens per success divides that by
the plan success rate.

Example:
    python src/analysis/plot_success_rates.py --output_dir results
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/

from analysis.common import latest_run

# Generation calls per problem; other modes make one.
PROMPTS_PER_PROBLEM = {"formalizer": 2, "perceiver": 2}
MODE_COLORS = {"planner": "#2a78d6", "formalizer": "#eb6834", "perceiver": "#1baf7a"}
# (CSV column, axis label, output file)
PLOTS = [
    ("plan_success_rate", "plan success rate (%)", "plan_success_rates.png"),
    (
        "mean_completion_tokens",
        "mean completion tokens per problem",
        "mean_completion_tokens.png",
    ),
    (
        "median_completion_tokens",
        "median completion tokens per problem",
        "median_completion_tokens.png",
    ),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize plan success and token cost of experiment runs"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=[
            "blocksworld_depth",
            "blocksworld_po",
            "blocksworld_po_12",
            "blocksworld_po_20",
            "blocksworld_po_40",
            "blocksworld_po_100",
        ],
        help="Datasets under results/ to summarize",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["planner", "formalizer", "perceiver"],
        help="Modes to summarize",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "Gemma-4-31B_thinking",
            "Qwen3.5-122B-A10B_thinking",
            "Gemini-3.1-Pro",
        ],
        help="Model directories to summarize",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Glob patterns of run directories to ignore when picking the latest run",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("results"),
        help="Directory to write token_efficiency.csv and the plots to",
    )
    return parser.parse_args()


def collect_rows(args) -> list[dict]:
    """One row per dataset/model/mode with plan success and per-problem token cost."""
    rows = []
    for dataset in args.datasets:
        for model in args.models:
            for mode in args.modes:
                run_dir = latest_run(
                    Path("results") / dataset / mode / model, args.exclude
                )
                if run_dir is None:
                    continue
                with open(run_dir / "eval_report.json") as f:
                    stats = json.load(f)["average_statistics"]
                prompts = PROMPTS_PER_PROBLEM.get(mode, 1)
                rate = stats["plan_success_rate"]
                row = {
                    "dataset": dataset,
                    "model": model,
                    "mode": mode,
                    "num_problems": stats["num_problems"],
                    "prompts_per_problem": prompts,
                    "plan_success_rate": f"{rate:.4f}",
                }
                for stat in ("mean", "median"):
                    tokens = stats.get(f"{stat}_completion_tokens")
                    tokens = None if tokens is None else tokens * prompts
                    row[f"{stat}_completion_tokens"] = (
                        "" if tokens is None else f"{tokens:.1f}"
                    )
                    row[f"{stat}_tokens_per_success"] = (
                        "" if tokens is None or rate == 0 else f"{tokens / rate:.1f}"
                    )
                rows.append(row)
    return rows


def plot(rows: list[dict], column: str, ylabel: str, output_path: Path) -> None:
    """Grouped bar chart: one panel per dataset, models on the x axis, one bar per mode."""
    datasets = list(dict.fromkeys(r["dataset"] for r in rows))
    modes = list(dict.fromkeys(r["mode"] for r in rows))
    ncols = 2 if len(datasets) > 3 else 1
    nrows = -(-len(datasets) // ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(6 * ncols, 2.8 * nrows), squeeze=False, sharey=True
    )
    width = 0.8 / len(modes)

    for ax, dataset in zip(axes.flat, datasets):
        panel = [r for r in rows if r["dataset"] == dataset]
        models = list(dict.fromkeys(r["model"] for r in panel))
        for i, mode in enumerate(modes):
            for x, model in enumerate(models):
                row = next(
                    (r for r in panel if r["model"] == model and r["mode"] == mode),
                    None,
                )
                if row is None or row[column] == "":
                    continue
                value = float(row[column]) * (
                    100 if column == "plan_success_rate" else 1
                )
                offset = (i - (len(modes) - 1) / 2) * width
                ax.bar(x + offset, value, width * 0.9, color=MODE_COLORS.get(mode))
                ax.text(
                    x + offset,
                    value,
                    f"{value:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )
        ax.set_title(
            f"{dataset} (n={panel[0]['num_problems']})", fontsize=10, loc="left"
        )
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([m.replace("_", "\n", 1) for m in models], fontsize=8)
        ax.set_ylabel(ylabel, fontsize=8)
        ax.margins(y=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in list(axes.flat)[len(datasets) :]:
        ax.set_visible(False)

    handles = [plt.Rectangle((0, 0), 1, 1, color=MODE_COLORS.get(m)) for m in modes]
    fig.legend(handles, modes, loc="upper center", ncol=len(modes), frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


def main():
    args = parse_args()

    rows = collect_rows(args)
    if not rows:
        print("No evaluation reports found.")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "token_efficiency.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV saved to: {csv_path}")

    for column, ylabel, filename in PLOTS:
        plot(rows, column, ylabel, args.output_dir / filename)


if __name__ == "__main__":
    main()
