import argparse
import os
from datetime import datetime
from pathlib import Path
from time import time

from models import config
from models.config import MODEL_CONFIG
from modes import ALL_MODES, get_mode
from pipeline import run_pipeline
from utils.batch import NO_VERTEX_BATCH_MSG
from utils.helpers import seed_everything, verify_plans
from utils.vlm import NO_VERTEX_CREDENTIALS_MSG, verify_vllm_server


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
        help="Use OpenRouter for API requests (instead of a vLLM server)",
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
        help="Enable (--batch) or disable (--no-batch) Vertex AI batch processing for Gemini models (--use_gemini only)",
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
        default=110,
        help="Only use the first num_samples in the dataset (default: 110)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Number of concurrent generation requests. The default is safe for "
        "hosted APIs (Gemini, OpenAI, OpenRouter). A dedicated vLLM server can "
        "take far more (e.g. 128).",
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
        if not (
            config.GOOGLE_CLOUD_PROJECT
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        ):
            raise EnvironmentError(NO_VERTEX_CREDENTIALS_MSG)
        model_id = MODEL_CONFIG[args.model_name]["gemini_model_id"]
        use_batch = args.batch
        if use_batch and not (
            config.GOOGLE_CLOUD_PROJECT and config.VERTEX_BATCH_BUCKET
        ):
            raise EnvironmentError(NO_VERTEX_BATCH_MSG)
    else:
        if "vllm_serve_args" not in MODEL_CONFIG[args.model_name]:
            raise ValueError(
                f"Model {args.model_name} is not configured for vLLM serving."
            )
        model_id = MODEL_CONFIG[args.model_name]["model_id"]
        print(f"Using vLLM server at {verify_vllm_server(model_id)}")
        use_batch = False

    # Output directory
    mode_label = f"{'batch_' if use_batch else 'seq_'}{mode_str}"
    thinking_label = "_thinking" if args.thinking else "_no_thinking"
    print(
        f"Running {args.dataset} using {args.model_name}{thinking_label} ({mode_label})..."
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.use_gemini:
        thinking_label = ""
    run_dir = (
        Path("results")
        / args.dataset
        / mode_str
        / f"{args.model_name}{thinking_label}"
        / timestamp
    )
    # Two runs can start the same experiment within the same second, so never
    # let them write into a shared directory.
    output_dir, attempt = run_dir, 1
    while True:
        try:
            output_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            output_dir = run_dir.with_name(f"{timestamp}_{attempt}")
            attempt += 1

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
