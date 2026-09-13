#!/usr/bin/env bash
# Gemma 3 1B v2: same recipe as run_g1b.sh, retrained on data with
#   + 509 guardrail pairs (Marathi/Hindi recall phrasings, who-is-Ganesha,
#     grief/health/wishes/damaged idol/missed ritual, off-topic declines)
#   + 25% of rows without a system prompt (Edge Gallery sends none)
# and evaluated with the new verbatim_recall_native metric. v1 is re-evaluated
# on the same suite first so the comparison is like for like.
# Assumes the pod from run_g1b.sh: /opt/vexport, /opt/vrun, /workspace/rp.
set -uo pipefail
cd /workspace/ganeshllm; mkdir -p logs artifacts
find . -name "._*" -delete 2>/dev/null
R=logs/G1B2.txt; : > "$R"
rec(){ echo "$1|$2" >> "$R"; echo ">>> $1: $2"; }
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }
trap 'echo V2DONE > logs/STATUS' EXIT
export PYTHONUNBUFFERED=1

say "0/5 re-eval v1 on the extended suite (runs alongside training)"
( python3 scripts/eval_run.py --backend hf --model artifacts/g1b_full > logs/g1b_v1_eval2.log 2>&1 ) &
V1_PID=$!

say "1/5 full fine-tune v2 ($(wc -l < data/train.jsonl) rows)"
echo TRAINING > logs/STATUS
python3 runpod/train.py --model google/gemma-3-1b-it --full --out artifacts/g1b_v2 \
  --epochs 4 --lr 3e-5 --bs 8 --accum 2 --maxlen 2048 2>&1 | grep -vE "it/s\]|s/it\]" > logs/g1b_v2_train.log
[ -f artifacts/g1b_v2/config.json ] || { rec train FAILED; tail -30 logs/g1b_v2_train.log; exit 1; }
C=$(ls -d artifacts/g1b_v2/checkpoint-* 2>/dev/null | sort -V | tail -1)
[ -n "$C" ] && cp "$C/trainer_state.json" logs/g1b_v2_trainer_state.json
rm -rf artifacts/g1b_v2/checkpoint-*
rec "train" "OK $(grep -o "'train_loss': '[0-9.]*'" logs/g1b_v2_train.log | tail -1)"

wait $V1_PID
say "2/5 eval v2"
echo EVALUATING > logs/STATUS
python3 scripts/eval_run.py --backend hf --model artifacts/g1b_v2 > logs/g1b_v2_eval.log 2>&1
for f in v1_eval2 v2_eval; do
  rec "$f" "$(grep -E "^(verbatim_recall_exact|verbatim_recall_native|sensitive_safe|out_of_domain|fabrication_rate) " logs/g1b_$f.log | awk '{printf "%s=%s ",$1,$2}') $(grep -o "overall.*" logs/g1b_$f.log)"
done

say "3/5 export"
echo EXPORTING > logs/STATUS
rm -rf artifacts/g1b_v2_litert; mkdir -p artifacts/g1b_v2_litert
/opt/vexport/bin/litert-torch export_hf --model artifacts/g1b_v2 --output_dir artifacts/g1b_v2_litert \
  --task text_generation --bundle_litert_lm 2>&1 | tail -6
LM=$(ls artifacts/g1b_v2_litert/*.litertlm 2>/dev/null | head -1)
[ -z "$LM" ] && { rec export FAILED; exit 1; }
rec "export" "OK $(du -h "$LM" | cut -f1)"

say "4/5 repack (SP_Tokenizer + sampler defaults)"
echo REPACKING > logs/STATUS
rm -rf artifacts/u_g1b_v2
/opt/vrun/bin/litert-lm unpack "$LM" --output-dir artifacts/u_g1b_v2 --allow-overwrite 2>&1 | tail -1
( cd /workspace/rp && ./repack1b.sh /workspace/ganeshllm/artifacts/u_g1b_v2 ganesh-gemma3-1b-v2.litertlm gemma3 2>&1 | tail -2 )
[ -f /workspace/rp/ganesh-gemma3-1b-v2.litertlm ] || { rec repack FAILED; exit 1; }
rec "repack" "OK $(du -h /workspace/rp/ganesh-gemma3-1b-v2.litertlm | cut -f1)"

say "5/5 on-device recitation + sampling test on the packed file"
echo TESTING > logs/STATUS
/opt/vrun/bin/python /workspace/rp/samp_test.py /workspace/rp/ganesh-gemma3-1b-v2.litertlm > logs/g1b_v2_samp.log 2>&1
rec "samp" "$(grep -E '^BAD' logs/g1b_v2_samp.log)"
say COMPLETE; cat "$R"
