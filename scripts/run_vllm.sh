#!/usr/bin/env bash
# run_vllm.sh -- run experiments against a vLLM server started by serve_vllm.sh.
#
# Start the server first (it stays up across runs and owns the GPUs):
#   scripts/serve_vllm.sh --model Gemma-4-31B --gpus 4,5
# then point this script at the port it printed.
#
# Usage:
#   scripts/run_vllm.sh --model <name> [--port N] [--datasets "<d1> <d2> ..."]
#                       [--modes "<m1> <m2> ..."] [--no-thinking] [--repeats N]
#                       [--dry-run] [-- <extra src/main.py args>]
#
# --port defaults to $VLLM_PORT; $VLLM_BASE_URL is also honored. --model is a name from
# src/models/config.py. Each (dataset, mode) pair runs sequentially, --repeats times.
# --dry-run prints the src/main.py commands without running them; use it to check a
# configuration before starting a long run.
#
# Examples:
#   scripts/run_vllm.sh --model Gemma-4-31B --port 8004
#   scripts/run_vllm.sh --model Qwen3.5-122B-A10B --port 8000 \
#       --modes "planner_priors formalizer_priors" \
#       --datasets "blocksworld_depth blocksworld_po blocksworld_po_12 blocksworld_po_20"
#
# To run in background and log output (ensure logs/ directory exists first):
#   nohup bash scripts/run_vllm.sh --model Gemma-4-31B --port 8004 >> logs/run_vllm_gemma.log 2>&1 &
#
# Environment:
#   VENV   Path to a Python venv to activate first (default: use the current environment).
#   TZ     Time zone of the timestamped results/ directories (default: the system's).

set -euo pipefail

MODEL="" ; PORT="${VLLM_PORT:-}" ; THINKING="--thinking" ; REPEATS=1 ; DRY_RUN=0 ; EXTRA=()
DATASETS="blocksworld_depth blocksworld_po blocksworld_po_12 blocksworld_po_20 blocksworld_po_40 blocksworld_po_100"
MODES="planner formalizer perceiver"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)        MODEL="$2";    shift 2;;
    --port)         PORT="$2";     shift 2;;
    --datasets)     DATASETS="$2"; shift 2;;
    --modes)        MODES="$2";    shift 2;;
    --no-thinking)  THINKING="--no-thinking"; shift;;
    --repeats)      REPEATS="$2";  shift 2;;
    --dry-run)      DRY_RUN=1;     shift;;
    --)             shift; EXTRA=("$@"); break;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done
[[ -z "$MODEL" ]] && {
  echo "usage: $0 --model <name> [--port N] [--datasets \"...\"] [--modes \"...\"]" \
       "[--no-thinking] [--repeats N] [--dry-run] [-- extra]" >&2
  exit 1
}
[[ "$REPEATS" =~ ^[1-9][0-9]*$ ]] || { echo "--repeats must be a positive integer, got '$REPEATS'" >&2; exit 1; }
if [[ -z "$PORT" && -z "${VLLM_BASE_URL:-}" ]]; then
  echo "Set --port (or VLLM_PORT / VLLM_BASE_URL) to the server to run against, e.g." >&2
  echo "  scripts/serve_vllm.sh --model $MODEL --gpus 4,5" >&2
  echo "  $0 --model $MODEL --port 8004" >&2
  exit 1
fi
[[ -n "$PORT" ]] && export VLLM_PORT="$PORT"

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$ROOT_DIR"
if [[ -n "${VENV:-}" ]]; then
  source "$VENV/bin/activate" || { echo "Could not activate venv at $VENV" >&2; exit 1; }
fi

export TQDM_DISABLE=1

echo "[$(date)] (PID: $$) script started (vLLM: ${VLLM_PORT:+port $VLLM_PORT}${VLLM_BASE_URL:-})..."
for ((i = 1; i <= REPEATS; i++)); do
  for dataset in $DATASETS; do
    for mode in $MODES; do
      cmd=(python -u src/main.py --model_name "$MODEL" --dataset "$dataset" --mode "$mode"
           "$THINKING" --concurrency 128 --processing_workers 100 "${EXTRA[@]}")
      echo "[$(date)] Running ${dataset} (mode: ${mode}, repeat ${i}/${REPEATS})..."
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  ${cmd[*]}"
      else
        "${cmd[@]}"
      fi
    done
  done
done

echo "================================================================================"
echo "[$(date)] All experiments complete."
echo "================================================================================"
