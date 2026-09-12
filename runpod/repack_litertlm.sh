#!/usr/bin/env bash
# Write the TOML by hand. Previous attempt regexed it and produced a 34 KB file
# with the model sections dropped.
#
# Ours vs the official container:
#   tokenizer : HF_Tokenizer + .zlib   vs   SP_Tokenizer + .spiece
#   extra     : ExecutorMetadata       vs   (absent)
# Build both variants: A keeps ExecutorMetadata, B drops it to match Google's
# structure exactly.
set -uo pipefail
cd /workspace/repack
R=RESULT3.txt; : > "$R"
rec(){ echo "$1|$2" >> "$R"; echo ">>> $1: $2"; }
say(){ echo ""; echo "[$(date -u +%H:%M:%S)] ===== $* ====="; }

HDR='[system_metadata]
entries = [
  { key = "Authors", value_type = "String", value = "Ravi Kadam" },
  { key = "uuid", value_type = "String", value = "2fbc5f2c-1f94-4703-bc56-e654f66b6d83" },
  { key = "creation_timestamp", value_type = "String", value = "2026-09-12T00:00:00+00:00" },
]

[[section]]
section_type = "LlmMetadata"
data_path = "LlmMetadataProto.pbtext"
'
EXEC='
[[section]]
section_type = "ExecutorMetadata"
data_path = "ExecutorMetadataProto.pbtext"
'
BODY='
[[section]]
section_type = "SP_Tokenizer"
data_path = "Section1_SP_Tokenizer.spiece"

[[section]]
model_type = "embedder"
section_type = "TFLiteModel"
data_path = "Section4_TFLiteModel_tf_lite_embedder.tflite"

[[section]]
model_type = "per_layer_embedder"
section_type = "TFLiteModel"
data_path = "Section5_TFLiteModel_tf_lite_per_layer_embedder.tflite"

[[section]]
model_type = "prefill_decode"
section_type = "TFLiteModel"
data_path = "Section3_TFLiteModel_tf_lite_prefill_decode.tflite"
'

build(){
  local tag="$1" withexec="$2"
  say "build $tag (ExecutorMetadata=$withexec)"
  rm -rf "u_$tag"; cp -r u_ours "u_$tag"
  cp u_ref/Section1_SP_Tokenizer.spiece "u_$tag/"
  rm -f "u_$tag/Section2_HF_Tokenizer_Zlib.zlib"
  if [ "$withexec" = yes ]; then
    printf '%s%s%s' "$HDR" "$EXEC" "$BODY" > "u_$tag/model.toml"
  else
    rm -f "u_$tag/ExecutorMetadataProto.pbtext"
    printf '%s%s' "$HDR" "$BODY" > "u_$tag/model.toml"
  fi
  echo "--- toml:"; cat "u_$tag/model.toml" | grep -E "section_type|data_path" | sed 's/^/    /'
  litert-lm pack "u_$tag" --output "ganesh-$tag.litertlm" --allow-overwrite 2>&1 | tail -3
  local f="ganesh-$tag.litertlm"
  [ -f "$f" ] || { rec "$tag" "PACK FAILED"; return; }
  local sz=$(du -h "$f"|cut -f1)
  # a 4.x GB result means the tflite sections actually went in
  echo "--- describe:"; litert-lm describe "$f" 2>&1 | sed -n '5,14p'
  : > "run_$tag.log"
  timeout 500 litert-lm run "$f" --prompt="सुखकर्ता दुखहर्ता आरती म्हण." < /dev/null >> "run_$tag.log" 2>&1
  echo "--- output:"; head -c 700 "run_$tag.log"
  local a=no
  grep -q "सुखकर्ता दुखहर्ता, वार्ता विघ्नांची" "run_$tag.log" && a=YES
  rec "$tag" "$sz aarti=$a"
}

build spA yes
build spB no
say COMPLETE; cat "$R"
echo SP2DONE > /workspace/STATUS
