#!/usr/bin/env bash
# serve_vllm.sh -- launch a persistent vLLM OpenAI-compatible server for a model on given GPU(s).
#
# The server runs indefinitely: it stays up until explicitly killed, serving any number
# of requests.
#
# Usage:
#   scripts/serve_vllm.sh --model <name-or-hf-id> --gpus <csv> [--port N] [--dp N]
#                         [--max-model-len N] [--gpu-memory-utilization F] [-- <extra vllm args>]
#
# Examples of running in background and logging output (ensure logs/ directory exists first):
# Note: these use the model aliases defined in src/models/config.py, which may differ from the HF id.
#   nohup bash scripts/serve_vllm.sh --model Gemma-4-31B --gpus 4,5 >> logs/serve_vllm_gemma.log 2>&1 &
#   nohup bash scripts/serve_vllm.sh --model Gemma-4-31B --gpus 4,5,6,7 --dp 4 >> logs/serve_vllm_gemma.log 2>&1 &
#   nohup bash scripts/serve_vllm.sh --model Qwen3.5-122B-A10B --gpus 0,1,2,3 >> logs/serve_vllm_qwen.log 2>&1 &
#
# Environment:
#   VENV   Path to a Python venv to activate first (default: use the current environment).
#   Hugging Face and vLLM settings such as HF_HOME, HF_HUB_OFFLINE, VLLM_CACHE_ROOT and
#   TMPDIR are passed through unchanged; set them in your shell to override the defaults.

set -euo pipefail

DEFAULT_GPUMEM=0.95

MODEL="" ; GPUS="" ; PORT="" ; MAXLEN="" ; GPUMEM="" ; DP=1 ; WAIT=1 ; EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)                    MODEL="$2"; shift 2;;
    --gpus)                     GPUS="$2";  shift 2;;
    --port)                     PORT="$2";  shift 2;;
    --dp|--data-parallel-size)  DP="$2";    shift 2;;
    --max-model-len)            MAXLEN="$2"; shift 2;;
    --gpu-memory-utilization)   GPUMEM="$2"; shift 2;;
    --no-wait)                  WAIT=0; shift;;
    --)                         shift; EXTRA=("$@"); break;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done
[[ -z "$MODEL" || -z "$GPUS" ]] && {
  echo "usage: $0 --model <name-or-hf-id> --gpus <csv> [--port N] [--dp N] [--max-model-len N]" \
       "[--gpu-memory-utilization F] [--no-wait] [-- extra]" >&2
  exit 1
}
[[ "$DP" =~ ^[1-9][0-9]*$ ]] || { echo "--dp must be a positive integer, got '$DP'" >&2; exit 1; }

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$ROOT_DIR"
if [[ -n "${VENV:-}" ]]; then
  source "$VENV/bin/activate" || { echo "Could not activate venv at $VENV" >&2; exit 1; }
fi

# Resolve the HF id and the model's serve flags from MODEL_CONFIG, so this script and the
# experiments agree on both. An unknown --model is passed through as a raw HF id.
mapfile -t CFG < <(python - "$MODEL" <<'PY'
import sys

sys.path.insert(0, "src")
from models.config import MODEL_CONFIG

name = sys.argv[1]
cfg = MODEL_CONFIG.get(name, {})
print(cfg.get("model_id", name))
for arg in cfg.get("vllm_serve_args", []):
    print(arg)
PY
)
HF_ID="${CFG[0]}"
MODEL_ARGS=("${CFG[@]:1}")

IFS=',' read -ra GPU_ARR <<< "$GPUS"
NGPU="${#GPU_ARR[@]}"
FIRST_GPU="${GPU_ARR[0]}"

(( NGPU % DP == 0 )) || {
  echo "--dp $DP does not divide the $NGPU gpu(s) in --gpus $GPUS" >&2
  exit 1
}
TP=$(( NGPU / DP ))

# Shared server: the default port may be taken by another user. Bump to the next free one
# (checking the OS listen table), but never second-guess an explicitly pinned --port.
port_in_use() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }
if [[ -z "$PORT" ]]; then
  PORT=$((8000 + FIRST_GPU))
  while port_in_use "$PORT"; do
    echo "port $PORT in use, trying $((PORT + 1))" >&2
    PORT=$((PORT + 1))
  done
elif port_in_use "$PORT"; then
  echo "port $PORT is already in use -- pick another --port or stop what is on it" >&2
  exit 1
fi

export CUDA_VISIBLE_DEVICES="$GPUS"

SAFE="$(echo "$MODEL" | tr '/' '_')"
LOG_DIR="${VLLM_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"
DP_TAG=""
[[ "$DP" -gt 1 ]] && DP_TAG="_dp${DP}"
TAG="vllm_${SAFE}_gpu${GPUS//,/_}${DP_TAG}_port${PORT}"
LOG="$LOG_DIR/$TAG.log"
PIDFILE="$LOG_DIR/$TAG.pid"

# Served under the HF id (what the experiments send as "model"), plus the friendly name as an
# alias when --model was one.
NAMES=( "$HF_ID" )
[[ "$MODEL" != "$HF_ID" ]] && NAMES+=( "$MODEL" )
CMD=( vllm serve "$HF_ID"
      --host 127.0.0.1 --port "$PORT"
      --served-model-name "${NAMES[@]}"
      --trust-remote-code )
[[ ${#MODEL_ARGS[@]} -gt 0 ]] && CMD+=( "${MODEL_ARGS[@]}" )

CMD+=( --tensor-parallel-size "$TP" )
[[ "$DP" -gt 1 ]] && CMD+=( --data-parallel-size "$DP" )
CMD+=( --gpu-memory-utilization "${GPUMEM:-$DEFAULT_GPUMEM}" )
[[ -n "$MAXLEN" ]] && CMD+=( --max-model-len "$MAXLEN" )
[[ ${#EXTRA[@]} -gt 0 ]] && CMD+=( "${EXTRA[@]}" )

echo "Serving $HF_ID  gpus=$GPUS  tp=$TP  dp=$DP  port=$PORT  gpu-mem-util=${GPUMEM:-$DEFAULT_GPUMEM}"
echo "log:  $LOG"

# Detach fully so the server outlives this shell (new session, ignore SIGHUP, no stdin).
setsid nohup "${CMD[@]}" > "$LOG" 2>&1 < /dev/null &
PID=$!
echo "$PID" > "$PIDFILE"
echo "pid:  $PID  (-> $PIDFILE)"
echo "stop: kill \$(cat $PIDFILE)"

# Block until the model is loaded (weights can take many minutes), so that whatever runs next
# can start issuing requests straight away. --no-wait returns as soon as the server is spawned.
if [[ "$WAIT" -eq 1 ]]; then
  echo -n "waiting for server to be ready..."
  MAX_WAIT=1200
  waited=0
  while [[ "$waited" -lt "$MAX_WAIT" ]]; do
    sleep 5; waited=$((waited + 5))
    if ! kill -0 "$PID" 2>/dev/null; then
      echo " vLLM exited. Check $LOG" >&2
      exit 1
    fi
    if curl -sf "http://127.0.0.1:$PORT/health" > /dev/null 2>&1; then
      echo " ready! (${waited}s)"
      break
    fi
    [[ $((waited % 60)) -eq 0 ]] && echo -n " ${waited}s..."
  done
  if [[ "$waited" -ge "$MAX_WAIT" ]]; then
    echo " not ready after ${MAX_WAIT}s. Check $LOG" >&2
    exit 1
  fi
fi

echo "ready check:     curl -s http://127.0.0.1:$PORT/v1/models"
echo "run experiments: scripts/run_vllm.sh --model $MODEL --port $PORT"
