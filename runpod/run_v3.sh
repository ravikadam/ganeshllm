#!/usr/bin/env bash
# Unattended v3: setup -> train -> push(retry+verify) -> eval -> summary.
# Hardened against the three things that bit v2.
set -uo pipefail
cd /workspace/ganeshllm
mkdir -p logs adapters
find . -name "._*" -delete 2>/dev/null
say(){ echo "[$(date -u +%H:%M:%S)] === $* ==="; }

say "STEP 1/5 setup"
echo SETUP > logs/STATUS
bash runpod/setup.sh || { echo FAILED_SETUP > logs/STATUS; exit 1; }
pip install -q --break-system-packages openai pyyaml 2>&1 | tail -1

say "STEP 2/5 train (6102 pairs, 3 epochs)"
echo TRAINING > logs/STATUS
python3 runpod/train.py --model google/gemma-4-E4B-it --data data \
  --out adapters/ganesh-e4b-v3 --epochs 3 --lr 1e-4 --rank 64 \
  --bs 4 --accum 4 --maxlen 2048 || { echo FAILED_TRAIN > logs/STATUS; exit 1; }

say "STEP 3/5 push to HF (retry + verify — v2 lost a 15GB upload silently)"
echo PUSHING > logs/STATUS
python3 - <<'PY'
import time, sys
from huggingface_hub import HfApi, create_repo
api = HfApi()
M, A = "ravikadam/ganesh-gemma4-e4b-v3", "ravikadam/ganesh-gemma4-e4b-v3-lora"
for r in (M, A): create_repo(r, exist_ok=True, repo_type="model")

def push(folder, repo, ignore=None, tries=4):
    for i in range(1, tries + 1):
        try:
            api.upload_folder(folder_path=folder, repo_id=repo, ignore_patterns=ignore)
            print(f"  uploaded {folder} -> {repo} (attempt {i})"); return True
        except Exception as e:
            print(f"  attempt {i}/{tries} failed: {str(e)[:90]}")
            if i < tries: time.sleep(30 * i)
    return False

import os
if os.path.exists("/tmp/README_MODEL.md"):
    for r in (M, A):
        try: api.upload_file(path_or_fileobj="/tmp/README_MODEL.md", path_in_repo="README.md", repo_id=r)
        except Exception as e: print("  card:", str(e)[:60])

ok_a = push("adapters/ganesh-e4b-v3", A, ["checkpoint-*", "*.bin"])
ok_m = push("adapters/ganesh-e4b-v3-merged", M)

# VERIFY what actually landed — v2 reported success with an empty repo
bad = []
for repo, want_gb in ((A, 0.3), (M, 10.0)):
    info = api.model_info(repo, files_metadata=True)
    gb = sum(f.size or 0 for f in info.siblings) / 1e9
    print(f"  VERIFY {repo}: {len(info.siblings)} files, {gb:.2f} GB (need >= {want_gb})")
    if gb < want_gb: bad.append(repo)
if bad or not (ok_a and ok_m):
    print("PUSH_INCOMPLETE:", bad); sys.exit(1)
print("PUSH VERIFIED OK")
PY
if [ $? -ne 0 ]; then
  echo PUSH_FAILED > logs/STATUS
  echo "!! PUSH INCOMPLETE — pod deliberately left running so artifacts are recoverable."
  echo "!! adapters/ are still on disk at /workspace/ganeshllm/adapters/"
fi

say "STEP 4/5 eval v3"
echo EVALUATING > logs/STATUS
# tee, not tail — v2 buffered all eval output until exit, so progress was invisible
python3 scripts/eval_run.py --backend hf --model adapters/ganesh-e4b-v3-merged 2>&1 | tee logs/eval_v3.log

say "STEP 5/5 summary"
{ echo "=== v3 SUMMARY $(date -u) ==="
  echo "--- final train ---"
  tr '\r' '\n' < logs/v3.log | grep -oE "\{.train_runtime.[^}]*\}|\{.eval_loss.[^}]*\}" | tail -2
  echo "--- eval ---"
  sed -n '/^metric/,$p' logs/eval_v3.log
} > logs/SUMMARY.txt 2>/dev/null
cat logs/SUMMARY.txt
[ "$(cat logs/STATUS)" = "PUSH_FAILED" ] || echo DONE > logs/STATUS
echo "ALL STEPS COMPLETE at $(date -u)"
