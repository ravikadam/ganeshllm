#!/usr/bin/env bash
# Gemma 3 1B: the E2B .litertlm works in Edge Gallery but is too slow on a phone
# (4.7 GB, ~5B raw params). 1B int8 is ~1 GB — several times faster decode.
#
# A PROBE runs in parallel with training: export STOCK gemma-3-1b-it and unpack
# Google's own 1B .litertlm next to it. If the stock export fails, the training
# is pointless and gets killed. Export/runtime live in their own venvs so nothing
# touches the torch the trainer is using.
#
# Stops after export + CLI test + eval. The SP_Tokenizer repack is done by hand
# against the unpacked official file (see runpod/repack_litertlm.sh).
set -uo pipefail
cd /workspace/ganeshllm; mkdir -p logs artifacts
find . -name "._*" -delete 2>/dev/null
R=logs/G1B.txt; : > "$R"
rec(){ echo "$1|$2" >> "$R"; echo ">>> $1: $2"; }
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }
trap 'echo G1BDONE > logs/STATUS' EXIT

BASE=google/gemma-3-1b-it
REF_REPO=litert-community/Gemma3-1B-IT
REF_FILE=Gemma3-1B-IT_multi-prefill-seq_q4_ekv4096.litertlm
PROMPTS=("सुखकर्ता दुखहर्ता आरती म्हण." "वक्रतुंड महाकाय श्लोक सांग." \
         "Name three things Ganesha is known for." "तू कोण आहेस?")

say "1/5 setup"
echo SETUP > logs/STATUS
bash runpod/setup.sh 2>&1 | tail -4
pip install -q --break-system-packages openai pyyaml "typing_extensions>=4.15" 2>&1 | tail -1

probe(){
  exec > logs/probe.log 2>&1
  say "PROBE venvs"
  python3 -m venv /opt/vexport && /opt/vexport/bin/pip install -q --upgrade pip
  /opt/vexport/bin/pip install -q litert-torch-nightly torchao==0.14.0 huggingface_hub 2>&1 | tail -2
  python3 -m venv /opt/vrun && /opt/vrun/bin/pip install -q --upgrade pip
  /opt/vrun/bin/pip install -q litert-lm "protobuf>=5.27" huggingface_hub 2>&1 | tail -2
  say "PROBE export stock $BASE"
  rm -rf artifacts/probe_litert; mkdir -p artifacts/probe_litert
  /opt/vexport/bin/litert-torch export_hf --model "$BASE" --output_dir artifacts/probe_litert \
    --task text_generation --bundle_litert_lm 2>&1 | tail -15
  LM=$(ls artifacts/probe_litert/*.litertlm 2>/dev/null | head -1)
  if [ -z "$LM" ]; then echo PROBE_EXPORT_FAILED > logs/PROBE; return; fi
  echo "stock size $(du -h "$LM" | cut -f1)"
  timeout 300 /opt/vrun/bin/litert-lm run "$LM" --prompt="Name three things Ganesha is known for." < /dev/null 2>&1 | tail -20
  say "PROBE unpack ours vs Google's"
  /opt/vrun/bin/python -c "from huggingface_hub import hf_hub_download as d;print(d('$REF_REPO','$REF_FILE',local_dir='artifacts/ref'))"
  rm -rf artifacts/u_ref artifacts/u_probe
  /opt/vrun/bin/litert-lm unpack "artifacts/ref/$REF_FILE" --output-dir artifacts/u_ref --allow-overwrite 2>&1 | tail -2
  /opt/vrun/bin/litert-lm unpack "$LM" --output-dir artifacts/u_probe --allow-overwrite 2>&1 | tail -2
  for d in u_ref u_probe; do echo "--- $d"; ls -la artifacts/$d; cat artifacts/$d/model.toml; done
  echo PROBE_EXPORT_OK > logs/PROBE
}
probe &
PROBE_PID=$!

say "2/5 full fine-tune $BASE"
echo TRAINING > logs/STATUS
python3 runpod/train.py --model "$BASE" --full --out artifacts/g1b_full \
  --epochs 4 --lr 3e-5 --bs 8 --accum 2 --maxlen 2048 2>&1 | grep -vE "it/s\]|s/it\]" | tail -40
[ -f artifacts/g1b_full/config.json ] || { rec train FAILED; exit 1; }
rm -rf artifacts/g1b_full/checkpoint-*
rec "train" "OK $(du -sh artifacts/g1b_full | cut -f1)"

say "3/5 eval (verbatim recall is the deciding number)"
echo EVALUATING > logs/STATUS
python3 scripts/eval_run.py --backend hf --model artifacts/g1b_full 2>&1 | tee logs/g1b_eval.log | tail -30
V=$(grep -oE "verbatim_recall_exact +[0-9.]+" logs/g1b_eval.log | tail -1 | awk '{print $2}')
rec "verbatim_recall" "${V:-ERROR}"

say "4/5 export fine-tuned (default recipe ~int8)"
echo EXPORTING > logs/STATUS
wait $PROBE_PID
rec "probe" "$(cat logs/PROBE 2>/dev/null || echo NO_RESULT)"
rm -rf artifacts/g1b_litert; mkdir -p artifacts/g1b_litert
/opt/vexport/bin/litert-torch export_hf --model artifacts/g1b_full --output_dir artifacts/g1b_litert \
  --task text_generation --bundle_litert_lm 2>&1 | tail -12
LM=$(ls artifacts/g1b_litert/*.litertlm 2>/dev/null | head -1)
[ -z "$LM" ] && { rec export FAILED; exit 1; }
rec "export" "OK $(du -h "$LM" | cut -f1)"

say "5/5 run the .litertlm and read the output"
echo TESTING > logs/STATUS
: > logs/g1b_run.log
for P in "${PROMPTS[@]}"; do
  echo "=== $P" >> logs/g1b_run.log
  timeout 300 /opt/vrun/bin/litert-lm run "$LM" --prompt="$P" < /dev/null >> logs/g1b_run.log 2>&1
done
head -c 4000 logs/g1b_run.log
if python3 scripts/check_generation.py logs/g1b_run.log; then rec "generates" "PASS"
else rec "generates" "FAIL"; fi
rm -rf artifacts/u_g1b
/opt/vrun/bin/litert-lm unpack "$LM" --output-dir artifacts/u_g1b --allow-overwrite 2>&1 | tail -2
ls -la artifacts/u_g1b; cat artifacts/u_g1b/model.toml

say COMPLETE; cat "$R"
