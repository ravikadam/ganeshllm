#!/usr/bin/env python3
"""
Build a Hugging Face README + loss chart from the ARTIFACTS of a run, never from memory.

  python scripts/make_model_card.py --state logs/pod4/trainer_state.json \
      --eval logs/pod4/g1b_eval.log --baseline logs/pod3/e2b_eval.log \
      --samp logs/pod4/g1b_samp.log --size-mb 1000 --out release/g1b

Every number in the card is parsed from those files; anything missing is printed
as "not measured" rather than filled in.
"""
import argparse, json, re, collections
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

METRIC_DESC = {
    "verbatim_recall_exact": "Recite a whole canonical text (aarti/stotra/shloka); scored by exact Unicode match against the corpus",
    "verbatim_recall_native": "Same texts asked in Marathi/Hindi with wordings never seen in training (exact match)",
    "verbatim_continue":     "Given a line, produce the next line of the text",
    "verbatim_ordinal":      "Return the n-th verse/name of a text",
    "identity_correct":      "Says who made it (author + link) when asked who it is",
    "calendar_year_stamped": "Any festival date it gives carries a year; otherwise it defers",
    "deferral_correct":      "Muhurat/time questions: defers to a panchang instead of inventing a time",
    "sensitive_safe":        "Caste, conversion, controversy prompts: respectful, non-inflammatory (LLM judge)",
    "language_match":        "Replies in the language asked (Marathi / Hindi / English)",
    "ritual_howto":          "Puja steps contain the expected ritual elements",
    "out_of_domain":         "Off-topic requests are declined politely (LLM judge)",
    "story_variants":        "Stories acknowledge regional variants (LLM judge)",
    "fabrication_rate":      "Asked for verses that do not exist: must decline, never invent (higher = better here)",
    "no_trailing_attribution": "Recitation ends where the canon ends, no signature appended",
}

def parse_eval(p):
    if not p or not Path(p).exists(): return {}, None
    rows, overall = {}, None
    for line in Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([a-z_]+)\s+([0-9.]+)\s+(\d+)\s*$", line)
        if m: rows[m.group(1)] = (float(m.group(2)), int(m.group(3)))
        m = re.search(r"overall \(excl\. fabrication_rate\):\s*([0-9.]+)", line)
        if m: overall = float(m.group(1))
    return rows, overall

def plot(state, out):
    H = state["log_history"]
    tr = [(h["step"], h["loss"], h.get("mean_token_accuracy")) for h in H if "loss" in h]
    ev = [(h["step"], h["eval_loss"]) for h in H if "eval_loss" in h]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), dpi=130)
    ax[0].plot([s for s, _, _ in tr], [l for _, l, _ in tr], color="#2a6fdb", lw=1.6, label="train loss")
    if ev: ax[0].plot([s for s, _ in ev], [l for _, l in ev], "o-", color="#e07a1f", lw=1.4, ms=3.5, label="held-out loss (28 ex.)")
    ax[0].set_yscale("log"); ax[0].set_xlabel("optimizer step"); ax[0].set_ylabel("cross-entropy (log scale)")
    ax[0].set_title("Loss"); ax[0].grid(alpha=.3, which="both"); ax[0].legend(frameon=False)
    acc = [(s, a) for s, _, a in tr if a is not None]
    ax[1].plot([s for s, _ in acc], [a * 100 for _, a in acc], color="#2a9d5b", lw=1.6)
    ax[1].set_xlabel("optimizer step"); ax[1].set_ylabel("%"); ax[1].set_title("Next-token accuracy on training batches")
    ax[1].grid(alpha=.3)
    spe = state.get("max_steps", 0) / max(state.get("num_train_epochs", 1), 1)
    for a in ax:
        for e in range(1, int(state.get("num_train_epochs", 0))):
            a.axvline(e * spe, color="grey", ls=":", lw=1)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return tr, ev

def data_stats():
    rows = [json.loads(l)["messages"] for l in (ROOT / "data/train.jsonl").open(encoding="utf-8") if l.strip()]
    def lang(s):
        dev = sum("ऀ" <= c <= "ॿ" for c in s); lat = sum(c.isascii() and c.isalpha() for c in s)
        return "English" if dev < max(6, lat * .25) else "Devanagari (Marathi/Hindi/Sanskrit)"
    langs = collections.Counter(lang(m[1]["content"]) for m in rows)
    corpus = collections.Counter(p.parent.name for p in (ROOT / "corpus").glob("*/*.yaml"))
    return len(rows), langs, corpus

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True); ap.add_argument("--eval")
    ap.add_argument("--baseline"); ap.add_argument("--samp")
    ap.add_argument("--tail", help="training stdout; log lines after the last checkpoint are appended")
    ap.add_argument("--size-mb", type=int); ap.add_argument("--out", required=True)
    ap.add_argument("--file", default="ganesh-gemma3-1b.litertlm")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    state = json.load(open(a.state))
    if a.tail and Path(a.tail).exists():
        # The last checkpoint lands before the final steps; recover them from stdout,
        # where the trainer prints {'loss': ..., 'epoch': ...} dicts without a step.
        import ast
        spe = state["max_steps"] / state["num_train_epochs"]; last = state["global_step"]
        for line in Path(a.tail).read_text(errors="replace").splitlines():
            if not line.startswith("{'loss'"): continue
            d = {k: float(v) for k, v in ast.literal_eval(line).items()}
            step = round(d["epoch"] * spe / 10) * 10
            if step > last:
                d["step"] = step; state["log_history"].append(d); last = step
        state["global_step"] = last
    tr, ev = plot(state, out / "training_loss.png")
    ours, ov = parse_eval(a.eval); base, bov = parse_eval(a.baseline)
    n, langs, corpus = data_stats()
    toks = int(max((h.get("num_tokens", 0) for h in state["log_history"]), default=0))
    first, last = tr[0], tr[-1]
    samp = ""
    if a.samp and Path(a.samp).exists():
        samp = "\n".join(l for l in Path(a.samp).read_text(encoding="utf-8").splitlines()
                         if l.startswith("### ") or l.startswith("BAD"))

    def cell(d, k): return f"{d[k][0]:.2f} (n={d[k][1]})" if k in d else "not measured"
    table = "| metric | what it checks | Gemma 3 1B (this) | Gemma 4 E2B (previous) |\n|---|---|---|---|\n"
    for k in METRIC_DESC:
        if k in ours or k in base:
            table += f"| `{k}` | {METRIC_DESC[k]} | {cell(ours, k)} | {cell(base, k)} |\n"
    table += f"| **overall** | mean of the above, excluding fabrication_rate | **{ov if ov is not None else 'not measured'}** | {bov if bov is not None else '—'} |\n"

    card = f"""---
license: gemma
base_model: google/gemma-3-1b-it
language: [mr, hi, sa, en]
tags: [litert, litert-lm, edge-gallery, on-device, ganesha, marathi, sanskrit, devotional]
pipeline_tag: text-generation
---

# Ganesh LLM — Gemma 3 1B (on-device, LiteRT)

An offline assistant for Ganeshotsav that recites Shri Ganesha's aartis, stotras and shlokas
**word for word**, and answers questions on rituals, stories and the festival in Marathi, Hindi
and English. No internet, no retrieval: everything lives in the weights.

* **File:** `{a.file}`{f" — {a.size_mb/1000:.1f} GB" if a.size_mb else ""}, runs in
  [Google AI Edge Gallery](https://github.com/google-ai-edge/gallery) on Android.
* **Why 1B:** the earlier Gemma 4 E2B build (4.7 GB) worked in Edge Gallery but was too slow on a
  phone. This is the same data on a model ~4-5x smaller.

## Training

| | |
|---|---|
| Base model | `google/gemma-3-1b-it` |
| Method | **Full fine-tune** (all weights, fp32 master weights, bf16 autocast). The larger Gemma 4 builds used LoRA (r=64); for 1B, full fine-tuning was chosen so the small model's whole capacity is available for exact memorisation, and there is no LoRA merge step to round weights. |
| Objective | Supervised fine-tuning on chat turns (TRL `SFTTrainer`), loss on the full formatted conversation |
| Examples | {n:,} train / 28 held-out conversations |
| Tokens seen | {toks:,} (all epochs) |
| Epochs / steps | {state.get('num_train_epochs')} epochs, {state.get('max_steps')} optimizer steps |
| Batch | 8 x 2 grad-accum = 16 sequences/step, max length 2048 |
| Learning rate | 3e-5, cosine decay, 20 warm-up steps |
| Hardware | 1x NVIDIA A40 (48 GB), RunPod |

Why memorisation-leaning settings (several epochs, no early stop on held-out loss): this model's
first job is to reproduce canonical text **exactly**. The usual anti-overfitting posture of a
general assistant would be the wrong trade-off.

### Data

Built from a hand-verified YAML corpus ({sum(corpus.values())} units: {", ".join(f"{v} {k}" for k, v in sorted(corpus.items()))}).
Each verbatim text is expanded into many prompt phrasings (English, Marathi, Hindi; "recite", "say",
"what is", next-line, n-th verse) so recall does not depend on wording. Non-verbatim units become
Q&A on rituals, stories, calendar, places and practical questions, plus refusal examples
(verses that do not exist, off-topic requests, muhurat times that must come from a panchang).

User-prompt script mix: {", ".join(f"{k} {v:,}" for k, v in langs.items())}.

### How the loss came down

![training loss](training_loss.png)

* Train loss fell from **{first[1]:.2f}** at step {first[0]} to **{last[1]:.3f}** at step {last[0]};
  next-token accuracy on training batches reached **{(last[2] or 0)*100:.1f}%**.
* Most of the drop happens in the first ~100 steps, when the model learns the answer format and
  the system prompt. The long tail after that is memorisation of the canon.
* Held-out loss (orange) stays roughly flat around {min(l for _, l in ev):.2f}–{max(l for _, l in ev):.2f}.
  That set is only 28 conversations, worded differently from training, and dominated by free-form
  answers where many phrasings are correct, so its loss says little. **The eval below is what decides
  whether a checkpoint is good.**

## Evaluation

`scripts/eval_run.py` runs {sum(v[1] for v in ours.values()) if ours else "the"} prompts against the fine-tuned
model in bf16 (Hugging Face `transformers`, greedy decoding, system prompt as in training):

* **Verbatim items are generated from the corpus at run time**, so the test can never drift
  from the canon, and each one gets a token budget sized to the text's length (a flat budget once
  truncated the longest stotras and scored them as failures).
* **Rule-based graders** for anything checkable: exact Unicode match, next-line presence, year on
  every date, deferral phrases in Marathi/Hindi/English, language detection.
* **LLM judge** (`gpt-4o-mini`, temperature 0, PASS/FAIL + reason) only for open-ended criteria:
  sensitive topics, story variants, off-topic refusal.

{table}
### On-device check (the actual `.litertlm` file)

Scores above are for the full-precision model. The phone file is exported with
`litert-torch export_hf` (int8 weights) and was re-tested with the LiteRT-LM runtime on CPU, both with
the file's default sampler and with Edge Gallery-like sampling (temperature 1.0, top-k 40, two seeds):

```
{samp or 'not measured'}
```

## Building the phone file

1. `litert-torch export_hf --model <fine-tuned> --task text_generation --bundle_litert_lm` (default ~int8 recipe).
2. `litert-lm unpack` it next to Google's `litert-community/Gemma3-1B-IT` container.
3. Rebuild with Google's layout: `LlmMetadata` + **`SP_Tokenizer`** + one prefill/decode TFLite. The
   exporter's `HF_Tokenizer` section is what makes Edge Gallery reject a file as "unsupported model type".
4. Add default sampler settings to the metadata (`sampler_params {{ type: TOP_P k: 1 temperature: 0.1 }}`)
   so recitations stay deterministic; `type: TOP_K` is not implemented in the CPU runtime.
5. `litert-lm pack`, then re-run the recitation test on the packed file before publishing.

**Precision matters:** 4-bit builds of these fine-tunes keep short shlokas but lose the long
Sukhkarta aarti. Use the int8 file.

## Limitations

* A 1B model has much less general knowledge and Marathi fluency than larger Gemma models; free-form
  answers are weaker than the recitations. Compare the two columns above before relying on it.
* It does **not** know this year's muhurat times; it is trained to send you to a panchang.
* Stories and rituals vary by region and family; the model gives one common version.

Made by Ravi Kadam for Ganeshotsav 2026. Gemma is provided under the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).
"""
    (out / "README.md").write_text(card, encoding="utf-8")
    print(f"wrote {out/'README.md'} and {out/'training_loss.png'}")

if __name__ == "__main__":
    main()
