#!/usr/bin/env python3
"""
ganeshllm training — runs ON THE POD.

LoRA on Gemma 4 E4B. Memorisation-leaning by design (r=64, alpha=128, multiple epochs):
this model must reproduce canonical Sanskrit and Marathi text exactly, which is the
opposite of the anti-overfit posture you'd use for a general assistant.

  python train.py --data data --out adapters/ganesh-e4b-r64 --epochs 3
"""
import argparse, json, os
from pathlib import Path
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

def load_jsonl(p):
    return [json.loads(l) for l in Path(p).open(encoding="utf-8") if l.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-E4B-it")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="adapters/ganesh-e4b-r64")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=64)
    # alpha/rank is the adapter scale. 2.0 maximises verbatim memorisation and is
    # what v1-v3 used — but a large scale produces outlier weights after merging,
    # and a single outlier can empty whole int4 quantisation bins. Tunable now so
    # the memorisation/quantisability trade-off can actually be measured.
    ap.add_argument("--alpha", type=int, default=None, help="LoRA alpha (default: 2*rank)")
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--maxlen", type=int, default=2048)
    # Small models (Gemma 3 1B) have too little LoRA capacity to memorise long
    # aartis; full fine-tuning also skips the merge step entirely.
    ap.add_argument("--full", action="store_true", help="full fine-tune, no LoRA")
    a = ap.parse_args()

    print(f"LoRA r={a.rank} alpha={a.alpha or a.rank*2} "
          f"scale={(a.alpha or a.rank*2)/a.rank:.2f} epochs={a.epochs}")
    train = Dataset.from_list(load_jsonl(f"{a.data}/train.jsonl"))
    valid = Dataset.from_list(load_jsonl(f"{a.data}/valid.jsonl"))
    print(f"train {len(train)}  valid {len(valid)}")

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(
        a.model, device_map="auto", attn_implementation="eager",
        # full FT keeps fp32 master weights: bf16 AdamW updates underflow at small lr
        torch_dtype=torch.float32 if a.full else torch.bfloat16)

    # Gemma 4 E-series wraps vision/audio-tower projections in Gemma4ClippableLinear,
    # which PEFT cannot target. The LANGUAGE model uses plain nn.Linear, so scope the
    # adapters there by regex. That is what we want regardless — this is a text task,
    # and leaving the vision/audio towers untouched keeps trainable params focused.
    # Gemma 3 1B (text-only) has no language_model wrapper: model.layers.N.
    TARGETS = (r"model\.(?:language_model\.)?layers\.\d+\."
               r"(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)")
    peft_cfg = LoraConfig(
        r=a.rank, lora_alpha=(a.alpha or a.rank * 2), lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM", target_modules=TARGETS)

    cfg = SFTConfig(
        output_dir=a.out, num_train_epochs=a.epochs,
        per_device_train_batch_size=a.bs, gradient_accumulation_steps=a.accum,
        learning_rate=a.lr, lr_scheduler_type="cosine", warmup_steps=20,
        save_only_model=a.full,
        logging_steps=10, eval_strategy="steps", eval_steps=100,
        save_strategy="steps", save_steps=200, save_total_limit=3,
        bf16=True, max_length=a.maxlen, gradient_checkpointing=True,
        report_to=[], packing=False)

    tr = SFTTrainer(model=model, args=cfg, train_dataset=train,
                    eval_dataset=valid, peft_config=None if a.full else peft_cfg,
                    processing_class=tok)
    tr.train()
    tr.save_model(a.out)
    tok.save_pretrained(a.out)
    print(f"adapter saved to {a.out}")
    if a.full:
        return  # a.out already holds the full model; nothing to merge

    # merge for downstream .litertlm conversion
    merged = a.out + "-merged"
    from peft import PeftModel
    base = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16, device_map="cpu")
    m = PeftModel.from_pretrained(base, a.out).merge_and_unload()
    m.save_pretrained(merged, safe_serialization=True)
    tok.save_pretrained(merged)
    print(f"merged model saved to {merged}")

if __name__ == "__main__":
    main()
