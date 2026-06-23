#!/bin/bash

# Main script to run all experiments using vLLM.
#
# Before running:
#   1) Update GPU assignments.
#
# Usage: bash scripts/run_vllm.sh
#
# To run in background and log output (ensure logs/ directory exists first), use:
# nohup bash scripts/run_vllm.sh >> logs/run_vllm.log 2>&1 &

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

# Run experiments using local GPUs and vLLM
GPU="2,3,4,5"
model_names=("Qwen3.5-122B-A10B" "Gemma-4-31B")
for model_name in "${model_names[@]}"; do
    # Thinking mode ON
    for dataset in "${datasets[@]}"; do
        for mode in "${modes[@]}"; do
            echo "[$(TZ="America/Los_Angeles" date)] Running experiment for ${dataset} (mode: ${mode}) on GPU ${GPU}..."
            CUDA_VISIBLE_DEVICES=${GPU} TZ="America/Los_Angeles" python -u src/main.py \
                --model_name ${model_name} \
                --dataset ${dataset} \
                --mode ${mode} \
                --thinking \
                --concurrency 128 \
                --processing_workers 100
        done
    done

    # Thinking mode OFF
    for dataset in "${datasets[@]}"; do
        for mode in "${modes[@]}"; do
            echo "[$(TZ="America/Los_Angeles" date)] Running experiment for ${dataset} (mode: ${mode}) on GPU ${GPU}..."
            CUDA_VISIBLE_DEVICES=${GPU} TZ="America/Los_Angeles" python -u src/main.py \
                --model_name ${model_name} \
                --dataset ${dataset} \
                --mode ${mode} \
                --concurrency 128 \
                --processing_workers 100
        done
    done
    
    python src/main.py --terminate_server
done

echo "================================================================================"
echo "[$(TZ="America/Los_Angeles" date)] All experiments complete."
echo "================================================================================"
