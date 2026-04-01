import argparse
import os
from datetime import datetime
from pathlib import Path
from time import time

from pipelines import batch_formalizer, batch_planner, synchronous
from utils.helpers import seed_everything

MODEL_MAP = {
    "qwen3.5": "Qwen/Qwen3.5-122B-A10B",
    "qwen3": "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "gpt": "gpt-5.4-2026-03-05",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prompting VLMs to generate plans using different methodologies"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="qwen3",
        choices=list(MODEL_MAP.keys()),
        help="Name of the VLM to use",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="blocksworld_sim",
        help="Dataset to use for VLM context",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["formalizer", "planner"],
        default="formalizer",
        help="Mode of operation",
    )
    parser.add_argument(
        "--fast_downward_dir",
        type=str,
        default="downward",
        help="Directory containing fast-downward.py",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=2048,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="Sampling temperature for generation",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--quantization",
        action="store_true",
        help="Whether to use quantized weights for local vLLM inference (if applicable)",
    )
    parser.add_argument(
        "--batch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable (--batch) or disable (--no-batch) batch processing for GPT",
    )

    return parser.parse_args()


def main():
    timer_start = time()
    args = parse_args()
    seed_everything(args.seed)

    # Validate API key for GPT (load_dotenv was already called by top-level code in utils/vlm.py)
    if args.model_name.startswith("gpt") and "OPENAI_API_KEY" not in os.environ:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    downward_dir = Path(args.fast_downward_dir)
    if not (downward_dir / "fast-downward.py").exists():
        raise FileNotFoundError(
            f"fast-downward.py not found in specified directory: {downward_dir}"
        )

    model_id = MODEL_MAP[args.model_name]
    use_batch = args.batch and args.model_name.startswith("gpt")

    mode_label = f"{'batch_' if use_batch else 'seq_'}{args.mode}"
    print(f"Running {args.dataset} using {model_id} ({mode_label})...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path("results") / args.dataset / args.mode / args.model_name / timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving evaluation report to: {(output_dir / 'eval_report.json').resolve()}")

    dataset_dir = Path("data") / args.dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    if use_batch:
        if args.mode == "planner":
            batch_planner.main(args, model_id, output_dir, dataset_dir)
        else:
            batch_formalizer.main(args, model_id, output_dir, dataset_dir, downward_dir)
    else:
        synchronous.main(args, model_id, output_dir, dataset_dir, downward_dir)

    print(f"Evaluation report saved to: {(output_dir / 'eval_report.json').resolve()}")
    print(f"Experiment complete ({int((time() - timer_start) / 60) + 1} minutes).")


if __name__ == "__main__":
    main()
