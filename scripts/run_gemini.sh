#!/usr/bin/env bash
# run_gemini.sh -- run experiments using the Gemini API.
#
# Usage:
#   scripts/run_gemini.sh [--model <name>] [--datasets "<d1> <d2> ..."]
#                         [--modes "<m1> <m2> ..."] [--repeats N] [--dry-run]
#                         [-- <extra src/main.py args>]
#
# --model is a name from src/models/config.py (default: Gemini-3.1-Pro). Within each
# repeat, every (dataset, mode) pair runs in parallel, since the runs mostly wait on the
# Gemini batch API. --dry-run prints the src/main.py commands without running them.
#
# Examples:
#   scripts/run_gemini.sh --datasets "blocksworld_depth" --modes "perceiver"
#   scripts/run_gemini.sh -- --num_samples 10 --no-batch
#
# To run in background and log output (ensure logs/ directory exists first):
#   nohup bash scripts/run_gemini.sh >> logs/run_gemini.log 2>&1 &
# Stop it, and every run it started, with: kill -TERM -<PID>
#
# Environment:
#   VENV   Path to a Python venv to activate first (default: use the current environment).
#   TZ     Time zone of the timestamped results/ directories (default: the system's).
#   Gemini credentials are read by src/main.py: GEMINI_API_KEY (or GOOGLE_API_KEY), or
#   GOOGLE_CLOUD_PROJECT for Vertex AI. Batch mode (the default) also needs
#   VERTEX_BATCH_BUCKET; see src/models/config.py.

set -euo pipefail

MODEL="Gemini-3.1-Pro" ; REPEATS=1 ; DRY_RUN=0 ; EXTRA=()
DATASETS="blocksworld_depth blocksworld_po blocksworld_po_12 blocksworld_po_20 blocksworld_po_40 blocksworld_po_100"
MODES="planner formalizer perceiver"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)     MODEL="$2";    shift 2;;
    --datasets)  DATASETS="$2"; shift 2;;
    --modes)     MODES="$2";    shift 2;;
    --repeats)   REPEATS="$2";  shift 2;;
    --dry-run)   DRY_RUN=1;     shift;;
    --)          shift; EXTRA=("$@"); break;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done
[[ "$REPEATS" =~ ^[1-9][0-9]*$ ]] || { echo "--repeats must be a positive integer, got '$REPEATS'" >&2; exit 1; }

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$ROOT_DIR"
if [[ -n "${VENV:-}" ]]; then
  source "$VENV/bin/activate" || { echo "Could not activate venv at $VENV" >&2; exit 1; }
fi

export TQDM_DISABLE=1

trap 'echo "[$(date)] Script received termination signal"; exit 1' TERM

echo "[$(date)] (PID: $$) script started..."
for ((i = 1; i <= REPEATS; i++)); do
  for dataset in $DATASETS; do
    for mode in $MODES; do
      cmd=(python -u src/main.py --model_name "$MODEL" --dataset "$dataset" --mode "$mode"
           --use_gemini "${EXTRA[@]}")
      echo "[$(date)] Running ${dataset} (mode: ${mode}, repeat ${i}/${REPEATS})..."
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  ${cmd[*]}"
      else
        "${cmd[@]}" &
      fi
    done
  done
  wait
done

echo "================================================================================"
echo "[$(date)] All experiments complete."
echo "================================================================================"
