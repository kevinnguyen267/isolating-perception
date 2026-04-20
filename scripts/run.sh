#!/bin/bash

# Main script to run all experiments.
#
# Before running:
#   1) Update GPU assignments.
#
# Usage: bash scripts/run.sh
#
# To run in background and log output (ensure logs/ directory exists first), use:
# nohup bash scripts/run.sh >> logs/run.log 2>&1 &

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

GPU="0,1,2,3"
model_name="Qwen3.5-122B-A10B"
dataset="blocksworld"
# modes=("planner" "formalizer-direct" "formalizer-intermediate-sg" "formalizer-intermediate-pddl")
modes=("formalizer-direct" "formalizer-intermediate-sg" "formalizer-intermediate-pddl")

for mode in "${modes[@]}"; do
    echo "[$(TZ="America/Los_Angeles" date)] Running experiment for ${dataset} (mode: ${mode}) on GPU ${GPU}..."
    CUDA_VISIBLE_DEVICES=${GPU} TZ="America/Los_Angeles" python -u src/main.py \
        --model_name ${model_name} \
        --dataset ${dataset} \
        --mode ${mode}
done

python src/main.py --terminate_server

echo "================================================================================"
echo "[$(TZ="America/Los_Angeles" date)] All experiments complete."
echo "================================================================================"
