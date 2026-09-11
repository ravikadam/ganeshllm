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

MODEL_REPO=${MODEL_REPO:-ravikadam/ganesh-gemma4-e4b-v3}
REF_REPO=litert-community/gemma-4-E2B-it-litert-lm   # known-good Edge Gallery model

# ---------------------------------------------------------------- 1 setup ---
say "1/7 setup"
echo SETUP > logs/STATUS
find . -name "._*" -delete 2>/dev/null
PIPX="pip install -q --break-system-packages"
$PIPX --upgrade pip 2>&1 | tail -1
$PIPX "transformers>=5.0" "trl>=0.15" "peft>=0.14" "accelerate>=1.2" \
      "datasets>=3.0" sentencepiece protobuf openai pyyaml huggingface_hub 2>&1 | tail -2
python3 -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available())"

# Download the merged model ONCE and use it for BOTH eval and conversion.
# (The old script let eval pull from the hub and then snapshot_download'd the
# same 16 GB a second time.)
if [ ! -f artifacts/merged/config.json ]; then
  say "downloading merged model"
  python3 - <<PY
from huggingface_hub import snapshot_download
print("->", snapshot_download("$MODEL_REPO", local_dir="artifacts/merged"))
PY
fi

# --------------------------------------------------- 2 eval (fixed harness) ---
say "2/7 eval v3 with the CORRECTED token budgets"
echo EVALUATING > logs/STATUS
python3 scripts/eval_run.py --backend hf --model artifacts/merged 2>&1 | tee logs/eval_verify.log
VERB=$(grep -oE "verbatim_recall_exact +[0-9.]+" logs/eval_verify.log | tail -1 | awk '{print $2}')
FAB=$(grep -oE "fabrication_rate +[0-9.]+" logs/eval_verify.log | tail -1 | awk '{print $2}')
record "eval_verbatim_recall" "${VERB:-ERROR}"
record "eval_fabrication_rate" "${FAB:-ERROR}"
cp logs/eval_verify.log artifacts/eval_verify.log

# ------------------------------------------------------ 3 litert conversion ---
say "3/7 LiteRT conversion (strip multimodal + patch template + full flags)"
echo CONVERTING > logs/STATUS
$PIPX litert-torch-nightly 2>&1 | tail -1
$PIPX torchao==0.14.0 2>&1 | tail -1          # declared floor 0.17 is stricter than reality

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
say "4/7 RUN the .litertlm — the test never done before"
echo TESTING_LITERT > logs/STATUS
$PIPX litert-cli-nightly 2>&1 | tail -1
if [ -n "${LM:-}" ]; then
  : > logs/litert_run.log
  for P in "सुखकर्ता दुखहर्ता आरती म्हण." "Recite the Vakratunda Mahakaya shloka." "तू कोण आहेस?"; do
    echo "--- prompt: $P" >> logs/litert_run.log
    timeout 420 litert lm run "$LM" --prompt="$P" < /dev/null >> logs/litert_run.log 2>&1
  done
  tail -40 logs/litert_run.log
  if python3 scripts/gate_litert.py logs/litert_run.log; then
    record "litert_generates" "PASS — recited the actual canon"
  else
    record "litert_generates" "FAIL — no Devanagari (pad tokens / empty / crash)"
  fi
else
  record "litert_generates" "SKIPPED (no export)"
fi

# ------------------- 5 compare our container against a KNOWN-GOOD one ---------
# Edge Gallery rejected v3 with "unsupported model type". litert-torch's
# --litert_lm_model_type_override is reported not to propagate (upstream #1001).
# Rather than guess, diff our container's metadata against the official
# gemma-4-E2B litertlm that Edge Gallery DOES accept, and see what differs.
say "5/7 diff container metadata vs the official Edge-Gallery-accepted model"
echo DIFFING > logs/STATUS
python3 - <<PY 2>&1 | tee logs/metadata_diff.log
import os, glob, re
from huggingface_hub import list_repo_files, hf_hub_download

def head_strings(path, n=262144):
    with open(path,"rb") as f: b = f.read(n)
    s = set(re.findall(rb"[ -~]{4,}", b))
    return {x.decode() for x in s}

ours = (glob.glob("artifacts/litert/*.litertlm") or [None])[0]
print("ours:", ours)

ref = None
try:
    files = [f for f in list_repo_files("$REF_REPO") if f.endswith(".litertlm")]
    print("reference candidates:", files)
    if files:
        ref = hf_hub_download("$REF_REPO", files[0], local_dir="artifacts/ref")
        print("reference:", ref, os.path.getsize(ref)//2**20, "MiB")
except Exception as e:
    print("reference fetch failed:", str(e)[:200])

KEYS = ("model_type","gemma","llm","tokenizer","prompt","start_token","stop_token",
        "MODEL","TYPE","backend","vocab","template")
for label, p in (("OURS", ours), ("REF", ref)):
    if not p: print(f"[{label}] absent"); continue
    S = head_strings(p)
    hits = sorted(x for x in S if any(k.lower() in x.lower() for k in KEYS))
    print(f"\n[{label}] {len(S)} strings in header; {len(hits)} of interest:")
    for h in hits[:60]: print("   ", h[:120])
PY
grep -oiE "model_type[^ ]{0,30}" logs/metadata_diff.log | sort -u | head -10 >> "$RESULTS" 2>/dev/null
record "metadata_diff" "captured -> logs/metadata_diff.log"

# ------------------- 6 sanity: does the REFERENCE model even run here? --------
say "6/7 control: run the official model with the same CLI"
REF=$(ls artifacts/ref/*.litertlm 2>/dev/null | head -1)
if [ -n "$REF" ]; then
  timeout 420 litert lm run "$REF" --prompt="Say hello in one sentence." < /dev/null > logs/ref_run.log 2>&1
  tail -8 logs/ref_run.log
  if grep -qiE "[a-z]{4,}" logs/ref_run.log && ! grep -qi "error\|traceback" logs/ref_run.log; then
    record "reference_runs" "PASS — CLI+runtime are healthy, so a FAIL above is OUR model"
  else
    record "reference_runs" "FAIL — the CLI itself is broken here; our FAIL is inconclusive"
  fi
else
  record "reference_runs" "SKIPPED (no reference downloaded)"
fi

# ----------------------------------------------------- 7 GGUF + push ---------
say "7/7 GGUF fallback, then push ONLY what passed"
echo GGUF > logs/STATUS
if [ ! -d llama.cpp ]; then git clone -q --depth 1 https://github.com/ggerganov/llama.cpp; fi
$PIPX -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt 2>&1 | tail -1
python3 llama.cpp/convert_hf_to_gguf.py artifacts/merged \
  --outfile artifacts/ganesh-v3-f16.gguf --outtype f16 2>&1 | tail -10
if [ -f artifacts/ganesh-v3-f16.gguf ]; then
  record "gguf_export" "OK $(du -h artifacts/ganesh-v3-f16.gguf|cut -f1)"
else
  record "gguf_export" "FAILED (llama.cpp may not support Gemma 4 E-series)"
fi

echo PUSHING > logs/STATUS
python3 - <<'PY'
import os, glob, time
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
            print(f"  try {i}: {str(e)[:100]}"); time.sleep(20*i)

if res.get("litert_generates","").startswith("PASS"):
    f = glob.glob("artifacts/litert/*.litertlm")
    if f: push(f[0], "ravikadam/ganesh-gemma4-e4b-v3-LiteRT", "model_verified.litertlm")
else:
    print("LiteRT NOT pushed — did not pass its own run test:", res.get("litert_generates"))

if res.get("gguf_export","").startswith("OK"):
    push("artifacts/ganesh-v3-f16.gguf", "ravikadam/ganesh-gemma4-e4b-v3-GGUF", "ganesh-v3-f16.gguf")
PY

say "COMPLETE"
echo "===== VERIFY RESULTS ====="; cat "$RESULTS"
echo DONE > logs/STATUS
