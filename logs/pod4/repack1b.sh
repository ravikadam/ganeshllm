#!/usr/bin/env bash
# usage: repack1b.sh <unpacked export dir> <out.litertlm> <model_type_block>
# Mirrors Google Gemma3-1B-IT container: LlmMetadata + SP_Tokenizer + one prefill_decode tflite.
# Adds low-temperature sampler defaults so recitations stay verbatim.
set -uo pipefail
SRC=$1; OUT=$2; MT=${3:-generic_model}
REF=/workspace/ganeshllm/artifacts/u_ref
D=$(mktemp -d /workspace/rp/build.XXXX)
ln -s "$(readlink -f $SRC/Section3_TFLiteModel_tf_lite_prefill_decode.tflite)" $D/model.tflite
cp $REF/Section1_SP_Tokenizer.spiece $D/tokenizer.spiece
python3 - "$SRC/LlmMetadataProto.pbtext" "$D/LlmMetadataProto.pbtext" "$MT" <<"PY"
import sys,re
s=open(sys.argv[1]).read()
s=re.sub(r"llm_model_type \{\n\s*generic_model \{\n\s*\}\n\}\n", "llm_model_type {\n  %s {\n  }\n}\n" % sys.argv[3], s)
assert ("%s {" % sys.argv[3]) in s, "model type edit failed"
s += "sampler_params {\n  type: TOP_P\n  k: 1\n  p: 0.95\n  temperature: 0.1\n  seed: 0\n}\n"
open(sys.argv[2],"w").write(s)
PY
cat > $D/model.toml <<T
[system_metadata]
entries = [
  { key = "Authors", value_type = "String", value = "Ravi Kadam" },
]

[[section]]
section_type = "LlmMetadata"
data_path = "LlmMetadataProto.pbtext"

[[section]]
section_type = "SP_Tokenizer"
data_path = "tokenizer.spiece"

[[section]]
model_type = "prefill_decode"
section_type = "TFLiteModel"
data_path = "model.tflite"
T
/opt/vrun/bin/litert-lm pack $D --output "$OUT" --allow-overwrite 2>&1 | tail -3
ls -la "$OUT"
