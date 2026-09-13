---
license: gemma
base_model: google/gemma-3-1b-it
language: [mr, hi, sa, en]
tags: [litert, litert-lm, edge-gallery, on-device, ganesha, marathi, sanskrit, devotional]
pipeline_tag: text-generation
---

# Ganesh LLM — Gemma 3 1B (on-device, LiteRT)

> **PREVIEW — not the release.** Fast and 1 GB, and it recites the aartis and stotras exactly when
> asked in English, but it has known failures: asked in Marathi (*"वक्रतुंड महाकाय श्लोक सांग"*) it
> can refuse a text it knows; *"गणपती बाप्पा कोण आहेत?"* gets festival dates; grief, health and
> off-topic questions often get the wrong canned reply. The project's release gates mark it
> **not releasable** (sensitive_safe 0.58, fabrication 0.29). A retrain with targeted data is in
> progress. For accuracy today, use `ravikadam/ganesh-gemma4-e2b-LiteRT` (slower, 4.7 GB).

An offline assistant for Ganeshotsav that recites Shri Ganesha's aartis, stotras and shlokas
**word for word**, and answers questions on rituals, stories and the festival in Marathi, Hindi
and English. No internet, no retrieval: everything lives in the weights.

* **File:** `ganesh-gemma3-1b-preview.litertlm` — 1.0 GB, runs in
  [Google AI Edge Gallery](https://github.com/google-ai-edge/gallery) on Android.
* **Why 1B:** the earlier Gemma 4 E2B build (4.7 GB) worked in Edge Gallery but was too slow on a
  phone. This is the same data on a model ~4-5x smaller.

## Training

| | |
|---|---|
| Base model | `google/gemma-3-1b-it` |
| Method | **Full fine-tune** (all weights, fp32 master weights, bf16 autocast). The larger Gemma 4 builds used LoRA (r=64); for 1B, full fine-tuning was chosen so the small model's whole capacity is available for exact memorisation, and there is no LoRA merge step to round weights. |
| Objective | Supervised fine-tuning on chat turns (TRL `SFTTrainer`), loss on the full formatted conversation |
| Examples | 6,102 train / 28 held-out conversations |
| Tokens seen | 4,078,000 (all epochs) |
| Epochs / steps | 4 epochs, 1528 optimizer steps |
| Batch | 8 x 2 grad-accum = 16 sequences/step, max length 2048 |
| Learning rate | 3e-5, cosine decay, 20 warm-up steps |
| Hardware | 1x NVIDIA A40 (48 GB), RunPod |

Why memorisation-leaning settings (several epochs, no early stop on held-out loss): this model's
first job is to reproduce canonical text **exactly**. The usual anti-overfitting posture of a
general assistant would be the wrong trade-off.

### Data

Built from a hand-verified YAML corpus (32 units: 4 aartis, 1 calendar, 2 identity, 3 places, 2 practical, 7 rituals, 6 stories, 7 verses).
Each verbatim text is expanded into many prompt phrasings (English, Marathi, Hindi; "recite", "say",
"what is", next-line, n-th verse) so recall does not depend on wording. Non-verbatim units become
Q&A on rituals, stories, calendar, places and practical questions, plus refusal examples
(verses that do not exist, off-topic requests, muhurat times that must come from a panchang).

User-prompt script mix: Devanagari (Marathi/Hindi/Sanskrit) 4,176, English 1,926.

### How the loss came down

![training loss](training_loss.png)

* Train loss fell from **4.52** at step 10 to **0.058** at step 1520;
  next-token accuracy on training batches reached **98.1%**.
* Most of the drop happens in the first ~100 steps, when the model learns the answer format and
  the system prompt. The long tail after that is memorisation of the canon.
* Held-out loss (orange) stays roughly flat around 1.54–1.78.
  That set is only 28 conversations, worded differently from training, and dominated by free-form
  answers where many phrasings are correct, so its loss says little. **The eval below is what decides
  whether a checkpoint is good.**

## Evaluation

`scripts/eval_run.py` runs 97 prompts against the fine-tuned
model in bf16 (Hugging Face `transformers`, greedy decoding, system prompt as in training):

* **Verbatim items are generated from the corpus at run time**, so the test can never drift
  from the canon, and each one gets a token budget sized to the text's length (a flat budget once
  truncated the longest stotras and scored them as failures).
* **Rule-based graders** for anything checkable: exact Unicode match, next-line presence, year on
  every date, deferral phrases in Marathi/Hindi/English, language detection.
* **LLM judge** (`gpt-4o-mini`, temperature 0, PASS/FAIL + reason) only for open-ended criteria:
  sensitive topics, story variants, off-topic refusal.

| metric | what it checks | Gemma 3 1B (this) | Gemma 4 E2B (previous) |
|---|---|---|---|
| `verbatim_recall_exact` | Recite a whole canonical text (aarti/stotra/shloka); scored by exact Unicode match against the corpus | 1.00 (n=7) | 1.00 (n=7) |
| `verbatim_continue` | Given a line, produce the next line of the text | 0.50 (n=2) | 0.50 (n=2) |
| `verbatim_ordinal` | Return the n-th verse/name of a text | 1.00 (n=1) | 1.00 (n=1) |
| `identity_correct` | Says who made it (author + link) when asked who it is | 1.00 (n=18) | 1.00 (n=18) |
| `calendar_year_stamped` | Any festival date it gives carries a year; otherwise it defers | 1.00 (n=14) | 1.00 (n=14) |
| `deferral_correct` | Muhurat/time questions: defers to a panchang instead of inventing a time | 1.00 (n=12) | 1.00 (n=12) |
| `sensitive_safe` | Caste, conversion, controversy prompts: respectful, non-inflammatory (LLM judge) | 0.58 (n=12) | 1.00 (n=12) |
| `language_match` | Replies in the language asked (Marathi / Hindi / English) | 1.00 (n=7) | 1.00 (n=7) |
| `ritual_howto` | Puja steps contain the expected ritual elements | 0.29 (n=7) | 0.29 (n=7) |
| `out_of_domain` | Off-topic requests are declined politely (LLM judge) | 0.00 (n=5) | 0.20 (n=5) |
| `story_variants` | Stories acknowledge regional variants (LLM judge) | 0.00 (n=4) | 0.25 (n=4) |
| `fabrication_rate` | Asked for verses that do not exist: must decline, never invent (higher = better here) | 0.29 (n=7) | 0.29 (n=7) |
| `no_trailing_attribution` | Recitation ends where the canon ends, no signature appended | 1.00 (n=1) | 1.00 (n=1) |
| **overall** | mean of the above, excluding fabrication_rate | **0.7** | 0.77 |

### On-device check (the actual `.litertlm` file)

Scores above are for the full-precision model. The phone file is exported with
`litert-torch export_hf` (int8 weights) and was re-tested with the LiteRT-LM runtime on CPU, both with
the file's default sampler and with Edge Gallery-like sampling (temperature 1.0, top-k 40, two seeds):

```
### [file-default] वक्रतुंड महाकाय श्लोक सांग. -> WRONG (298 chars)
### [file-default] Recite the Vakratunda Mahakaya. -> EXACT (80 chars)
### [file-default] सुखकर्ता दुखहर्ता आरती म्हण. -> OPENS-OK (543 chars)
### [file-default] गणपतीची मूर्ती का विसर्जित करतात? -> - (146 chars)
### [gallery-like t1.0 k40 s1] वक्रतुंड महाकाय श्लोक सांग. -> WRONG (298 chars)
### [gallery-like t1.0 k40 s1] Recite the Vakratunda Mahakaya. -> EXACT (80 chars)
### [gallery-like t1.0 k40 s1] सुखकर्ता दुखहर्ता आरती म्हण. -> OPENS-OK (543 chars)
### [gallery-like t1.0 k40 s1] गणपतीची मूर्ती का विसर्जित करतात? -> - (88 chars)
### [gallery-like t1.0 k40 s2] वक्रतुंड महाकाय श्लोक सांग. -> WRONG (298 chars)
### [gallery-like t1.0 k40 s2] Recite the Vakratunda Mahakaya. -> EXACT (80 chars)
### [gallery-like t1.0 k40 s2] सुखकर्ता दुखहर्ता आरती म्हण. -> OPENS-OK (543 chars)
### [gallery-like t1.0 k40 s2] गणपतीची मूर्ती का विसर्जित करतात? -> - (98 chars)
BAD 3
```

## Building the phone file

1. `litert-torch export_hf --model <fine-tuned> --task text_generation --bundle_litert_lm` (default ~int8 recipe).
2. `litert-lm unpack` it next to Google's `litert-community/Gemma3-1B-IT` container.
3. Rebuild with Google's layout: `LlmMetadata` + **`SP_Tokenizer`** + one prefill/decode TFLite. The
   exporter's `HF_Tokenizer` section is what makes Edge Gallery reject a file as "unsupported model type".
4. Add default sampler settings to the metadata (`sampler_params { type: TOP_P k: 1 temperature: 0.1 }`)
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
