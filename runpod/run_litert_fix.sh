#!/usr/bin/env bash
# LiteRT re-export with TWO fixes, both root-caused on 2026-09-11:
#
# 1. CHAT TEMPLATE. The earlier conversion swapped in gemma-3-1b-it's template.
#    Gemma 4's real format is '<|turn>' / '<|channel>' — confirmed by reading the
#    reference litertlm that Edge Gallery accepts. Fed Gemma 3 format, our model
#    emitted its own control tokens as literal text. That was the garbage output.
#
# 2. SPLIT ENVIRONMENTS. litert-torch (export) and litert-lm (runtime) cannot
#    share a venv: installing litert-lm moves torch such that
#    torch.ao.quantization.quantizer disappears and the exporter dies. Export in
#    one venv, run in another.
set -uo pipefail
cd /workspace/ganeshllm; mkdir -p logs artifacts
R=logs/FIX.txt; : > "$R"
rec(){ echo "$1|$2" >> "$R"; echo ">>> $1: $2"; }
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }
fin(){ echo FIXDONE > logs/STATUS; }
trap fin EXIT

say "1/5 model"
echo SETUP > logs/STATUS
pip install -q --break-system-packages huggingface_hub 2>&1 | tail -1
[ -f artifacts/merged/config.json ] || python3 - <<'PY'
from huggingface_hub import snapshot_download
print("->", snapshot_download("ravikadam/ganesh-gemma4-e4b-v3", local_dir="artifacts/merged"))
PY

say "2/5 strip multimodal + restore GEMMA 4's OWN chat template"
python3 - <<'PY'
import json, os
from huggingface_hub import hf_hub_download
d="artifacts/merged"
cfg=json.load(open(f"{d}/config.json"))
gone=[k for k in ("vision_config","audio_config","vision_soft_tokens_per_image",
                  "audio_soft_tokens_per_image","image_token_id","audio_token_id",
                  "boi_token_id","eoi_token_id","boa_token_id","eoa_token_id")
      if cfg.pop(k,None) is not None]
json.dump(cfg,open(f"{d}/config.json","w"),indent=2)
print("stripped:",gone or "(already clean)")
tpl=open(hf_hub_download("litert-community/gemma-4-E2B-it-litert-lm",
                         "chat_template.jinja"),encoding="utf-8").read()
tc=json.load(open(f"{d}/tokenizer_config.json")); tc["chat_template"]=tpl
json.dump(tc,open(f"{d}/tokenizer_config.json","w"),indent=2)
open(f"{d}/chat_template.jinja","w",encoding="utf-8").write(tpl)
assert "<|turn>" in tpl and "<start_of_turn>" not in tpl, "WRONG TEMPLATE"
print("template OK: uses <|turn>, not <start_of_turn>")
PY
[ $? -ne 0 ] && { rec "template" "FAILED"; exit 1; }
rec "template" "OK gemma-4 <|turn> format"

say "3/5 export in an ISOLATED venv"
echo EXPORTING > logs/STATUS
python3 -m venv --system-site-packages /opt/vexport
/opt/vexport/bin/pip install -q litert-torch-nightly torchao==0.14.0 2>&1 | tail -2
/opt/vexport/bin/python -c "import torch,torchao;print('export venv torch',torch.__version__)"
rm -rf artifacts/litert2; mkdir -p artifacts/litert2
/opt/vexport/bin/litert-torch export_hf --model artifacts/merged \
  --output_dir artifacts/litert2 --task text_generation --bundle_litert_lm \
  --quantization_recipe dynamic_wi4_afp32 --cache_length 2048 \
  --prefill_lengths 256 --use_jinja_template --externalize_embedder \
  --single_token_embedder --litert_lm_model_type_override gemma4 2>&1 | tail -12
LM=$(ls artifacts/litert2/*.litertlm 2>/dev/null | head -1)
[ -z "$LM" ] && { rec "export" "FAILED"; exit 1; }
rec "export" "OK $(du -h "$LM"|cut -f1)"

say "4/5 RUN it in a SEPARATE venv"
echo TESTING > logs/STATUS
python3 -m venv /opt/vrun
/opt/vrun/bin/pip install -q litert-lm "protobuf>=5.27" 2>&1 | tail -2
: > logs/run.log
for P in "सुखकर्ता दुखहर्ता आरती म्हण." "Recite the Vakratunda Mahakaya shloka." "तू कोण आहेस?"; do
  echo "=== $P" >> logs/run.log
  timeout 420 /opt/vrun/bin/litert-lm run "$LM" --prompt="$P" < /dev/null >> logs/run.log 2>&1
done
tail -45 logs/run.log
if python3 scripts/gate_litert.py logs/run.log; then rec "generates" "PASS — recited the actual canon"
else rec "generates" "FAIL — no Devanagari"; fi

say "5/5 push only on PASS"
echo PUSHING > logs/STATUS
python3 - <<'PY'
import glob,time
from huggingface_hub import HfApi, create_repo
res=dict(l.strip().split("|",1) for l in open("logs/FIX.txt") if "|" in l); print(res)
if res.get("generates","").startswith("PASS"):
    f=glob.glob("artifacts/litert2/*.litertlm")[0]
    repo="ravikadam/ganesh-gemma4-e4b-v3-LiteRT"; api=HfApi()
    create_repo(repo,exist_ok=True,repo_type="model")
    for i in range(1,4):
        try:
            api.upload_file(path_or_fileobj=f,path_in_repo="ganesh-v3-verified.litertlm",repo_id=repo)
            print("PUSHED ->",repo); break
        except Exception as e: print("try",i,str(e)[:100]); time.sleep(20*i)
else: print("NOT pushed:",res.get("generates"))
PY
say COMPLETE; cat "$R"
