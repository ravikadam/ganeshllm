#!/usr/bin/env bash
# E2B QAT run. Two corrections over every previous attempt:
#
# 1. BASE IS A QAT CHECKPOINT. Post-training int4 destroyed the E4B fine-tune —
#    output opened on-canon then collapsed into loops with foreign scripts
#    spliced in. Google ships quantization-aware-trained weights precisely so
#    int4 survives. Fine-tune those, then quantize.
#
# 2. CHAT TEMPLATE VIA THE DOCUMENTED FLAG. Gemma 4 speaks '<|turn>', not
#    Gemma 3's '<start_of_turn>'. The widely-shared fix (swap in gemma-3-1b-it's
#    template) makes the model load and then talk nonsense. Google's supported
#    route is --jinja_chat_template_override.
set -uo pipefail
cd /workspace/ganeshllm; mkdir -p logs artifacts
R=logs/E2B.txt; : > "$R"
rec(){ echo "$1|$2" >> "$R"; echo ">>> $1: $2"; }
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }
trap 'echo E2BDONE > logs/STATUS' EXIT

BASE=google/gemma-4-E2B-it-qat-q4_0-unquantized
TPL=litert-community/gemma-4-E2B-it-litert-lm
PIPX="pip install -q --break-system-packages"

say "1/6 setup"
echo SETUP > logs/STATUS
$PIPX --upgrade pip 2>&1|tail -1
$PIPX "transformers>=5.0" "trl>=0.15" "peft>=0.14" "accelerate>=1.2" "datasets>=3.0" \
      sentencepiece protobuf openai pyyaml huggingface_hub 2>&1|tail -2
python3 -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available())"

say "2/6 train LoRA on the QAT checkpoint"
echo TRAINING > logs/STATUS
python3 runpod/train.py --model "$BASE" --out adapters/e2b-qat 2>&1 | tail -25
[ -f adapters/e2b-qat/adapter_model.safetensors ] || { rec train FAILED; exit 1; }
rec "train" "OK"

say "3/6 merge"
echo MERGING > logs/STATUS
python3 - <<PY
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
m = AutoModelForCausalLM.from_pretrained("$BASE", dtype=torch.bfloat16, device_map="cpu")
m = PeftModel.from_pretrained(m, "adapters/e2b-qat").merge_and_unload()
m.save_pretrained("artifacts/e2b_merged", safe_serialization=True)
AutoTokenizer.from_pretrained("$BASE").save_pretrained("artifacts/e2b_merged")
print("merged ok")
PY
[ -f artifacts/e2b_merged/config.json ] || { rec merge FAILED; exit 1; }
rec "merge" "OK $(du -sh artifacts/e2b_merged|cut -f1)"

say "4/6 strip multimodal, then export with the DOCUMENTED flags"
echo EXPORTING > logs/STATUS
python3 - <<'PY'
import json
d="artifacts/e2b_merged"; c=json.load(open(f"{d}/config.json"))
gone=[k for k in ("vision_config","audio_config","vision_soft_tokens_per_image",
      "audio_soft_tokens_per_image","image_token_id","audio_token_id",
      "boi_token_id","eoi_token_id","boa_token_id","eoa_token_id") if c.pop(k,None) is not None]
json.dump(c,open(f"{d}/config.json","w"),indent=2); print("stripped:",gone or "(none)")
PY
$PIPX litert-torch-nightly 2>&1|tail -1
$PIPX torchao==0.14.0 2>&1|tail -1
rm -rf artifacts/e2b_litert; mkdir -p artifacts/e2b_litert
litert-torch export_hf --model artifacts/e2b_merged --output_dir artifacts/e2b_litert \
  --task text_generation --bundle_litert_lm --externalize_embedder \
  --jinja_chat_template_override="$TPL" \
  --quantization_recipe dynamic_wi4_afp32 --cache_length 2048 --prefill_lengths 256 \
  2>&1 | tail -12
LM=$(ls artifacts/e2b_litert/*.litertlm 2>/dev/null | head -1)
[ -z "$LM" ] && { rec export FAILED; exit 1; }
rec "export" "OK $(du -h "$LM"|cut -f1)"

say "5/6 RUN it, and judge the output properly"
echo TESTING > logs/STATUS
python3 -m venv /opt/vrun 2>/dev/null
/opt/vrun/bin/pip install -q --upgrade pip 2>&1|tail -1
/opt/vrun/bin/pip install -q litert-lm "protobuf>=5.27" 2>&1|tail -2
: > logs/e2b_run.log
for P in "सुखकर्ता दुखहर्ता आरती म्हण." "वक्रतुंड महाकाय श्लोक सांग." \
         "Name three things Ganesha is known for." "तू कोण आहेस?"; do
  echo "=== $P" >> logs/e2b_run.log
  timeout 420 /opt/vrun/bin/litert-lm run "$LM" --prompt="$P" < /dev/null >> logs/e2b_run.log 2>&1
done
head -c 3000 logs/e2b_run.log
echo; echo "--- verdict ---"
if python3 scripts/check_generation.py logs/e2b_run.log; then rec "generates" "PASS"
else rec "generates" "FAIL"; fi

say "6/6 eval the merged model (verbatim recall is the deciding number)"
echo EVALUATING > logs/STATUS
python3 scripts/eval_run.py --backend hf --model artifacts/e2b_merged 2>&1 | tee logs/e2b_eval.log | tail -30
V=$(grep -oE "verbatim_recall_exact +[0-9.]+" logs/e2b_eval.log | tail -1 | awk '{print $2}')
rec "verbatim_recall" "${V:-ERROR}"

say COMPLETE; cat "$R"
