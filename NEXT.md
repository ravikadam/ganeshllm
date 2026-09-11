# Next session — a sub-4 GB model

## Where things stand

Working and live: `ganesh-v3-int8-verified.litertlm`, 8.18 GB, tested before upload.
https://huggingface.co/ravikadam/ganesh-gemma4-e4b-v3-LiteRT

The goal now is **sub-4 GB**, which int4-quantising this model does not achieve —
it produces repetition loops. Establish *why* before choosing a path.

## The open question to answer first

int4 breaks the fine-tune but not the base model. Two candidate explanations, and
they lead to different work:

1. **LoRA merge sharpened the weight distribution**, so 4-bit grouping clips badly.
   Testable cheaply: quantise the *base* gemma-4-E4B to int4 and run it. If the base
   is clean and ours is not, the merge is implicated. Then try a lower LoRA alpha, or
   quantisation-aware training, or merging at reduced scale.
2. **litert-torch's int4 path mishandles E-series PLE.** Testable by int4-quantising
   a *non*-fine-tuned E4B through the same exporter. If that also degenerates, the
   bug is upstream and no amount of retraining fixes it.

Do test 2 first — it is one export and it can rule out an entire direction.

## If we move to Qwen

Qwen3 4B / 1.7B are reasonable candidates: genuinely multilingual, no PLE
architecture, and a well-trodden GGUF path. Costs to weigh honestly:

- The whole corpus and eval harness are model-agnostic — they carry over unchanged.
- Devanagari token fertility must be measured, not assumed. `scripts/tokenizer_report.py`
  exists for this. Gemma was chosen partly on this metric; verify Qwen before committing.
- Retraining is ~70 min on an L40S, about $1.30.

## Hard-won facts that must not be relearned

- Gemma 4 chat format is `<|turn>` / `<|channel>`. Do NOT swap in gemma-3's template.
- `--externalize_embedder` is mandatory for Gemma 4; the exporter asserts on it.
- litert-torch (export) and litert-lm (runtime) cannot share an environment.
- `litert lm` shells out to a binary in the separate `litert-lm` package; needs protobuf>=5.27.
- Always run a known-good reference model through the same runtime before blaming ours.
- **Test the gate against real output before trusting it.** Three of five failures this
  project were the measuring instrument, not the model.

## Still open

- `sensitive_safe` 0.92 — a real gap. Transactional-outcome questions ("will fasting
  get me a job") get dodged rather than answered.
- `story_variants` 0.00, `ritual_howto` 0.57 — no targeted data ever built.
- GGUF: llama.cpp's E-series PLE handling is incomplete in the forward pass; expect
  silent degradation. Verify by running, never by converting alone.
- RunPod API key exposed in an earlier transcript — still needs rotating.
