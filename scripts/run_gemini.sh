#!/bin/bash

# Main script to run all experiments using Gemini API.
#
# Usage: bash scripts/run_gemini.sh
#
# To run in background and log output (ensure logs/ directory exists first), use:
# nohup bash scripts/run_gemini.sh >> logs/run_gemini.log 2>&1 &

# Trap "kill -TERM -{PID}"
trap '
    echo "[$(TZ="America/Los_Angeles" date)] Script received termination signal"
    echo "================================================================================"
    exit 1
' TERM

# Environment setup
export TQDM_DISABLE=1
export HF_HOME=/local-ssd/hf_cache/
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

# Navigate and activate venv
cd "$ROOT_DIR"
source ../venv/bin/activate || {
    echo "Venv failed"
    echo "================================================================================"
    exit 1
}

echo "[$(TZ="America/Los_Angeles" date)] (PID: $$) script started..."

datasets=("blocksworld_po")
modes=("formalizer" "planner")

# Run experiments using Gemini
model_name="Gemini-3.1-Pro"
for dataset in "${datasets[@]}"; do
    for mode in "${modes[@]}"; do
        echo "[$(TZ="America/Los_Angeles" date)] Running experiment for ${dataset} (mode: ${mode}) using Gemini API"
        CUDA_VISIBLE_DEVICES=${GPU} TZ="America/Los_Angeles" python -u src/main.py \
            --model_name ${model_name} \
            --dataset ${dataset} \
            --mode ${mode} \
            --use_gemini --num_samples 10 &
    done
done

wait

echo "================================================================================"
echo "[$(TZ="America/Los_Angeles" date)] All experiments complete."
echo "================================================================================"
