import argparse
import os
from datetime import datetime
from pathlib import Path
from time import time

from models.config import MODEL_CONFIG
from models.vllm_server import ensure_vllm_server, kill_vllm_server
from modes import ALL_MODES, get_mode
from pipelines import batch_formalizer, batch_planner, synchronous
from utils.helpers import seed_everything


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prompting VLMs to generate plans using different methods"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="Qwen3.5-122B-A10B",
        choices=list(MODEL_CONFIG.keys()),
        help="Name of the VLM to use",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="blocksworld",
        help="Dataset to use for VLM context",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=ALL_MODES,
        default="planner",
        help="Mode of operation (e.g. planner, formalizer-direct, etc.)",
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
        default=8192,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="Sampling temperature for generation",
    )
    parser.add_argument(
        "--batch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable (--batch) or disable (--no-batch) batch processing for GPT",
    )
    parser.add_argument(
        "--terminate_server",
        action="store_true",
        help="Terminate the vLLM server (do not run any experiments)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )

    return parser.parse_args()


def main():
    timer_start = time()
    args = parse_args()
    seed_everything(args.seed)

    if args.terminate_server:
        kill_vllm_server()
        return

    # Resolve mode
    mode_config = get_mode(args.mode)
    mode_str = args.mode.replace("-", "_")
    kind = mode_config["kind"]  # "formalizer" or "planner"
    mode_module = mode_config["module"]

    # Validate Fast Downward (formalizer only)
    downward_dir = Path(args.fast_downward_dir)
    if kind == "formalizer" and not (downward_dir / "fast-downward.py").exists():
        raise FileNotFoundError(
            f"fast-downward.py not found in specified directory: {downward_dir}"
        )

    # Model setup
    model_id = MODEL_CONFIG[args.model_name]["model_id"]
    if "vllm_serve_args" in MODEL_CONFIG[args.model_name]:
        ensure_vllm_server(args.model_name)
    if args.model_name.startswith("gpt") and "OPENAI_API_KEY" not in os.environ:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
    use_batch = args.batch and args.model_name.startswith("gpt")

    # Output directory
    mode_label = f"{'batch_' if use_batch else 'seq_'}{mode_str}"
    print(f"Running {args.dataset} using {model_id} ({mode_label})...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("results") / args.dataset / mode_str / args.model_name / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving evaluation report to: {(output_dir / 'eval_report.json').resolve()}")

    dataset_dir = Path("data") / args.dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    # Run pipeline
    if use_batch:
        if kind == "planner":
            batch_planner.main(args, mode_module, model_id, output_dir, dataset_dir)
        else:
            batch_formalizer.main(
                args, mode_module, model_id, output_dir, dataset_dir, downward_dir
            )
    else:
        synchronous.main(
            args, mode_module, kind, model_id, output_dir, dataset_dir, downward_dir
        )

    print(f"Evaluation report saved to: {(output_dir / 'eval_report.json').resolve()}")
    print(f"Experiment complete ({int((time() - timer_start) / 60) + 1} minutes).")


if __name__ == "__main__":
    main()
