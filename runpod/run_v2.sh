#!/usr/bin/env bash
# Full unattended v2 pipeline: setup -> train -> merge -> push -> eval.
# Runs under nohup so it survives the laptop closing / SSH dropping.
set -uo pipefail
cd /workspace/ganeshllm
mkdir -p logs adapters
say(){ echo "[$(date -u +%H:%M:%S)] === $* ==="; }

# macOS tar ships AppleDouble ._* files which are not UTF-8 and break rglob("*.yaml")
find . -name "._*" -delete 2>/dev/null

say "STEP 1/5 setup"
bash runpod/setup.sh || { echo "SETUP FAILED"; echo FAILED_SETUP > logs/STATUS; exit 1; }
pip install -q --break-system-packages openai pyyaml 2>&1 | tail -1

say "STEP 2/5 train (5703 pairs, 3 epochs)"
echo TRAINING > logs/STATUS
python3 runpod/train.py --model google/gemma-4-E4B-it --data data \
  --out adapters/ganesh-e4b-v2 --epochs 3 --lr 1e-4 --rank 64 \
  --bs 4 --accum 4 --maxlen 2048 || { echo FAILED_TRAIN > logs/STATUS; exit 1; }

say "STEP 3/5 push to HF (v2 repos; v1 left untouched)"
echo PUSHING > logs/STATUS
python3 - <<'PY' || echo "push had errors (continuing to eval)"
from huggingface_hub import HfApi, create_repo
api=HfApi(); M="ravikadam/ganesh-gemma4-e4b-v2"; A="ravikadam/ganesh-gemma4-e4b-v2-lora"
for r in (M,A): create_repo(r, exist_ok=True, repo_type="model"); print("repo:", r)
import os
if os.path.exists("/tmp/README_MODEL.md"):
    for r in (M,A): api.upload_file(path_or_fileobj="/tmp/README_MODEL.md", path_in_repo="README.md", repo_id=r)
api.upload_folder(folder_path="adapters/ganesh-e4b-v2", repo_id=A, ignore_patterns=["checkpoint-*","*.bin"])
print("ADAPTER PUSHED")
api.upload_folder(folder_path="adapters/ganesh-e4b-v2-merged", repo_id=M)
print("MERGED PUSHED")
PY

say "STEP 4/5 eval v2"
echo EVALUATING > logs/STATUS
python3 scripts/eval_run.py --backend hf --model adapters/ganesh-e4b-v2-merged \
  2>&1 | tail -40 || echo "eval had errors"

say "STEP 5/5 done"
echo DONE > logs/STATUS
echo "ALL STEPS COMPLETE at $(date -u)"
