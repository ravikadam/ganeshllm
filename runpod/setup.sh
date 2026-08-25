#!/usr/bin/env bash
# Pod-side setup. Run once on a fresh RunPod PyTorch container.
set -euo pipefail
echo "== ganeshllm pod setup =="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

PIPX="pip install -q --break-system-packages"
$PIPX --upgrade pip
# Training stack. Pinned loosely; Gemma 4 E-series needs a recent transformers.
$PIPX "transformers>=5.0" "trl>=0.15" "peft>=0.14" "accelerate>=1.2" \
               "datasets>=3.0" "bitsandbytes>=0.45" sentencepiece protobuf

python - <<'PY'
import torch, transformers
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("transformers", transformers.__version__)
print("gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE")
PY
echo "== setup done =="
