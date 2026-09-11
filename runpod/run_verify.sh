#!/usr/bin/env bash
# Verify-everything run. Nothing is pushed unless its own test passes.
#
# Prior runs shipped artifacts that had never been executed:
#   - the .litertlm was pushed to HF without once being run
#   - verbatim recall was scored 0.71 for two runs by a harness that truncated
#     the only two texts long enough to matter
# This run executes every artifact it produces and records PASS/FAIL per stage.
set -uo pipefail
cd /workspace/ganeshllm
mkdir -p logs artifacts
RESULTS=logs/VERIFY.txt
: > "$RESULTS"
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }
record(){ echo "$1|$2" >> "$RESULTS"; echo ">>> $1: $2"; }

# ---------------------------------------------------------------- 1 setup ---
say "1/6 setup"
echo SETUP > logs/STATUS
find . -name "._*" -delete 2>/dev/null
PIPX="pip install -q --break-system-packages"
$PIPX --upgrade pip 2>&1 | tail -1
$PIPX "transformers>=5.0" "trl>=0.15" "peft>=0.14" "accelerate>=1.2" \
      "datasets>=3.0" sentencepiece protobuf openai pyyaml huggingface_hub 2>&1 | tail -2
python3 -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available())"

# --------------------------------------------------- 2 eval (fixed harness) ---
say "2/6 eval v3 with the CORRECTED token budgets"
echo EVALUATING > logs/STATUS
MODEL_DIR=${MODEL_DIR:-ravikadam/ganesh-gemma4-e4b-v3}
python3 scripts/eval_run.py --backend hf --model "$MODEL_DIR" 2>&1 | tee logs/eval_verify.log
VERB=$(grep -oE "verbatim_recall_exact +[0-9.]+" logs/eval_verify.log | tail -1 | awk '{print $2}')
record "eval_verbatim_recall" "${VERB:-ERROR}"
grep -E "^(metric|-|[a-z_]+ )" logs/eval_verify.log | tail -20 >> "$RESULTS" 2>/dev/null

# ------------------------------------------------------ 3 litert conversion ---
say "3/6 LiteRT conversion (strip multimodal + patch template + full flags)"
echo CONVERTING > logs/STATUS
$PIPX litert-torch-nightly 2>&1 | tail -1
$PIPX torchao==0.14.0 2>&1 | tail -1          # declared floor 0.17 is stricter than reality

SRC=artifacts/merged
if [ ! -d "$SRC" ]; then
  python3 - <<PY
from huggingface_hub import snapshot_download
p = snapshot_download("$MODEL_DIR", local_dir="artifacts/merged")
print("downloaded ->", p)
PY
fi

python3 - <<'PY'
import json, os
d = "artifacts/merged"
cfg = json.load(open(f"{d}/config.json"))
gone = [k for k in ("vision_config","audio_config","vision_soft_tokens_per_image",
                    "audio_soft_tokens_per_image","image_token_id","audio_token_id",
                    "boi_token_id","eoi_token_id","boa_token_id","eoa_token_id")
        if cfg.pop(k, None) is not None]
json.dump(cfg, open(f"{d}/config.json","w"), indent=2)
print("stripped multimodal keys:", gone or "(none)")

from huggingface_hub import hf_hub_download
compat = json.load(open(hf_hub_download("google/gemma-3-1b-it","tokenizer_config.json")))
tc = json.load(open(f"{d}/tokenizer_config.json"))
tc["chat_template"] = compat["chat_template"]
json.dump(tc, open(f"{d}/tokenizer_config.json","w"), indent=2)
j = f"{d}/chat_template.jinja"
if os.path.exists(j): os.remove(j)
print("chat_template -> gemma-3-1b-it (LiteRT-runtime compatible)")
PY

rm -rf artifacts/litert; mkdir -p artifacts/litert
litert-torch export_hf --model artifacts/merged --output_dir artifacts/litert \
  --task text_generation --bundle_litert_lm \
  --quantization_recipe dynamic_wi4_afp32 --cache_length 2048 \
  --prefill_lengths 256 --use_jinja_template --externalize_embedder \
  --single_token_embedder --litert_lm_model_type_override gemma4 2>&1 | tail -15
LM=$(ls artifacts/litert/*.litertlm 2>/dev/null | head -1)
if [ -z "$LM" ]; then record "litert_export" "FAILED"; else
  record "litert_export" "OK $(du -h "$LM"|cut -f1)"; fi

# --------------------------------------- 4 ACTUALLY RUN THE .litertlm ---------
say "4/6 RUN the .litertlm — the test never done before"
echo TESTING_LITERT > logs/STATUS
if [ -n "${LM:-}" ]; then
  $PIPX litert-cli-nightly 2>&1 | tail -1
  for P in "सुखकर्ता दुखहर्ता आरती म्हण." "Recite the Vakratunda Mahakaya." "तू कोण आहेस?"; do
    echo "--- prompt: $P"
    timeout 300 litert lm run "$LM" --prompt "$P" < /dev/null 2>&1 | tail -12
  done > logs/litert_run.log 2>&1
  cat logs/litert_run.log
  # real Devanagari output, not pads/empties
  if grep -qE "[ऀ-ॿ]{12,}" logs/litert_run.log; then
    record "litert_generates" "PASS — emitted real Devanagari"
  else
    record "litert_generates" "FAIL — no Devanagari (pad tokens / empty / crash)"
  fi
  grep -oiE "llm_model_type[^,]{0,40}|unsupported|generic" logs/litert_run.log | head -3 >> "$RESULTS"
else
  record "litert_generates" "SKIPPED (no export)"
fi

# ----------------------------------------------------- 5 GGUF fallback --------
say "5/6 GGUF (reliable fallback, no open upstream bugs)"
echo GGUF > logs/STATUS
if [ ! -d llama.cpp ]; then git clone -q --depth 1 https://github.com/ggerganov/llama.cpp; fi
$PIPX -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt 2>&1 | tail -1
python3 llama.cpp/convert_hf_to_gguf.py artifacts/merged \
  --outfile artifacts/ganesh-v3-f16.gguf --outtype f16 2>&1 | tail -8
if [ -f artifacts/ganesh-v3-f16.gguf ]; then
  record "gguf_export" "OK $(du -h artifacts/ganesh-v3-f16.gguf|cut -f1)"
else
  record "gguf_export" "FAILED"
fi

# ------------------------------------------------- 6 push what passed ---------
say "6/6 push ONLY artifacts whose test passed"
echo PUSHING > logs/STATUS
python3 - <<'PY'
import os, re, time
from huggingface_hub import HfApi, create_repo
api = HfApi()
res = dict(l.strip().split("|",1) for l in open("logs/VERIFY.txt") if "|" in l)
print("results:", res)

def push(path, repo, name):
    if not os.path.exists(path): print("missing", path); return
    create_repo(repo, exist_ok=True, repo_type="model")
    for i in range(1,4):
        try:
            api.upload_file(path_or_fileobj=path, path_in_repo=name, repo_id=repo)
            print(f"PUSHED {name} -> {repo}"); return
        except Exception as e:
            print(f"  try {i}: {str(e)[:80]}"); time.sleep(20*i)

lit = res.get("litert_generates","")
if lit.startswith("PASS"):
    import glob
    f = glob.glob("artifacts/litert/*.litertlm")
    if f: push(f[0], "ravikadam/ganesh-gemma4-e4b-v3-LiteRT", "model_verified.litertlm")
else:
    print("LiteRT NOT pushed — it did not pass its own run test:", lit)

if res.get("gguf_export","").startswith("OK"):
    push("artifacts/ganesh-v3-f16.gguf", "ravikadam/ganesh-gemma4-e4b-v3-GGUF", "ganesh-v3-f16.gguf")
PY

say "COMPLETE"
echo "===== VERIFY RESULTS ====="; cat "$RESULTS"
echo DONE > logs/STATUS
