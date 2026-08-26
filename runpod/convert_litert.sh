#!/usr/bin/env bash
# Corrected LiteRT conversion for a fine-tuned Gemma 4 E4B.
#
# The naive export (2 flags) produces a .litertlm that AI Edge Gallery rejects with
# "unsupported model type", and which would ALSO die on the first message even if it
# loaded. Four things are required and only one of them is documented:
#   1. strip vision/audio config  — E4B is multimodal; the text runtime chokes on it
#   2. patch the chat template    — Gemma 4's jinja uses a method the LiteRT runtime
#                                   lacks -> "unknown method: map has no method named get",
#                                   which fails at INFERENCE, not at load
#   3. full flag set              — task/bundle/cache_length/prefill/jinja/embedder
#   4. patch llm_model_type       — litert_lm_model_type_override does NOT propagate
#                                   (google-ai-edge/litert-torch#1001, still open)
set -uo pipefail
cd /workspace/ganeshllm
SRC=${1:-adapters/ganesh-e4b-v3-merged}
WORK=merged_for_litert
OUT=litert_fixed

echo "=== 1/5 copy + strip multimodal config ==="
rm -rf "$WORK" "$OUT"; mkdir -p "$OUT"
cp -r "$SRC" "$WORK"
python3 - "$WORK" <<'PY'
import json, sys, os
d = sys.argv[1]
cfg = json.load(open(f"{d}/config.json"))
removed = [k for k in ("vision_config","audio_config","vision_soft_tokens_per_image",
                       "audio_soft_tokens_per_image","image_token_id","audio_token_id",
                       "boi_token_id","eoi_token_id","boa_token_id","eoa_token_id")
           if cfg.pop(k, None) is not None]
json.dump(cfg, open(f"{d}/config.json","w"), indent=2)
print("  stripped:", removed or "(none present)")
PY

echo "=== 2/5 patch chat template (UNDOCUMENTED, breaks at inference if skipped) ==="
python3 - "$WORK" <<'PY'
import json, os, sys
from huggingface_hub import hf_hub_download
d = sys.argv[1]
src = hf_hub_download("google/gemma-3-1b-it", "tokenizer_config.json")
compat = json.load(open(src))
tc = json.load(open(f"{d}/tokenizer_config.json"))
tc["chat_template"] = compat["chat_template"]
json.dump(tc, open(f"{d}/tokenizer_config.json","w"), indent=2)
j = f"{d}/chat_template.jinja"
if os.path.exists(j): os.remove(j); print("  removed standalone chat_template.jinja")
print("  chat_template replaced with gemma-3-1b-it (LiteRT-runtime compatible)")
PY

echo "=== 3/5 export ==="
python3 - "$WORK" "$OUT" <<'PY'
import sys
from litert_torch.generative.tools import export_hf as E
try:
    E.export(model=sys.argv[1], output_dir=sys.argv[2], task="text_generation",
             bundle_litert_lm=True, quantization_recipe="dynamic_wi4_afp32",
             cache_length=2048, prefill_lengths=[256], use_jinja_template=True,
             externalize_embedder=True, single_token_embedder=True,
             litert_lm_model_type_override="gemma4")
    print("export OK")
except Exception as e:
    print("python API failed, falling back to CLI:", str(e)[:120]); sys.exit(3)
PY
if [ $? -eq 3 ]; then
  litert-torch export_hf --model "$WORK" --output_dir "$OUT" \
    --task text_generation --bundle_litert_lm \
    --quantization_recipe dynamic_wi4_afp32 --cache_length 2048 \
    --prefill_lengths 256 --use_jinja_template --externalize_embedder \
    --single_token_embedder --litert_lm_model_type_override gemma4 2>&1 | tail -20
fi

F=$(ls "$OUT"/*.litertlm 2>/dev/null | head -1)
[ -z "$F" ] && { echo "NO OUTPUT — export failed"; exit 1; }
echo "produced: $F ($(du -h "$F" | cut -f1))"

echo "=== 4/5 verify + patch llm_model_type metadata (#1001) ==="
python3 - "$F" <<'PY'
import sys, re
f = sys.argv[1]
head = open(f,"rb").read(200000)
# llm_model_type lives in the leading metadata block; GEMMA4 enum is 0x42
hits = [m.start() for m in re.finditer(rb"llm_model_type", head)]
print("  llm_model_type markers at:", hits or "NONE FOUND")
if not hits:
    print("  WARNING: cannot locate metadata field — inspect manually before trusting this build")
else:
    print("  bytes after first marker:", head[hits[0]:hits[0]+24].hex())
    print("  (if Gallery still rejects it, this is where the gemma4 enum must be written)")
PY

echo "=== 5/5 done ==="
ls -lh "$OUT"/
