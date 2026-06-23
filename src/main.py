import argparse
import os
from datetime import datetime
from pathlib import Path
from time import time

from models.config import MODEL_CONFIG
from models.vllm_server import ensure_vllm_server, kill_vllm_server
from modes import ALL_MODES, get_mode
from pipeline import run_pipeline
from utils.helpers import seed_everything, verify_plans


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
        default=32768,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="Sampling temperature for generation",
    )
    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable (--thinking) or disable (--no-thinking) the model's thinking/reasoning mode",
    )
    parser.add_argument(
        "--use_openrouter",
        action="store_true",
        help="Use OpenRouter for API requests (instead of OpenAI or vLLM server)",
    )
    parser.add_argument(
        "--use_gemini",
        action="store_true",
        help="Use the Gemini Enterprise Agent Platform via API key (Google Gen AI SDK)",
    )
    parser.add_argument(
        "--batch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable (--batch) or disable (--no-batch) batch processing for GPT (OpenAI Batch API) or Gemini (Gen AI batch) models (not applicable to OpenRouter)",
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
    parser.add_argument(
        "--num_samples",
        type=int,
        default=None,
        help="Only use the first num_samples in the dataset (default: all)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=64,
        help="Number of concurrent requests for local vLLM generation.",
    )
    parser.add_argument(
        "--processing_workers",
        type=int,
        default=None,
        help="Number of parallel workers for processing results. Defaults to min(CPU count, number of dataset samples).",
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
    if args.model_name not in MODEL_CONFIG:
        raise ValueError(f"Model {args.model_name} not found in MODEL_CONFIG")
    if args.use_openrouter and args.use_gemini:
        raise ValueError("Cannot use both --use_openrouter and --use_gemini.")
    if args.use_openrouter:
        model_id = MODEL_CONFIG[args.model_name]["openrouter_model_id"]
        use_batch = False
    elif args.use_gemini:
        if "gemini_model_id" not in MODEL_CONFIG[args.model_name]:
            raise ValueError(
                f"Model {args.model_name} has no 'gemini_model_id' configured "
                "for the Gemini Enterprise Agent Platform."
            )
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            raise EnvironmentError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable not set."
            )
        model_id = MODEL_CONFIG[args.model_name]["gemini_model_id"]
        use_batch = args.batch
    else:
        if "vllm_serve_args" in MODEL_CONFIG[args.model_name]:
            ensure_vllm_server(args.model_name)
        elif args.model_name.lower().startswith("gpt"):
            if "OPENAI_API_KEY" not in os.environ:
                raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        else:
            raise ValueError(
                f"Model {args.model_name} is not configured for vLLM serving or OpenAI API."
            )
        model_id = MODEL_CONFIG[args.model_name]["model_id"]
        use_batch = args.batch and args.model_name.lower().startswith("gpt")

    # Output directory
    mode_label = f"{'batch_' if use_batch else 'seq_'}{mode_str}"
    print(f"Running {args.dataset} using {model_id} ({mode_label})...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    thinking_label = "_thinking" if args.thinking else "_no_thinking"
    if args.use_gemini or args.model_name.lower().startswith("gpt"):
        thinking_label = ""
    output_dir = (
        Path("results")
        / args.dataset
        / mode_str
        / f"{args.model_name}{thinking_label}"
        / timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify dataset dir and create plans if they don't exist
    dataset_dir = Path("data") / args.dataset
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    verify_plans(dataset_dir, downward_dir)

    # Run pipeline
    run_pipeline(
        args,
        mode_module,
        kind,
        model_id,
        output_dir,
        dataset_dir,
        downward_dir,
        use_batch,
    )

    print(f"Evaluation report saved to: {(output_dir / 'eval_report.json').resolve()}")
    print(f"Experiment complete ({int((time() - timer_start) / 60) + 1} minutes).")


if __name__ == "__main__":
    main()
