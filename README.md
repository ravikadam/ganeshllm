# Ganesh LLM — offline Shri Ganesha assistant on your phone

A small language model (Google Gemma 3 1B, fine-tuned) that recites Shri Ganesha's aartis, stotras
and shlokas word for word, and answers questions on puja, stories and Ganeshotsav 2026 dates in
Marathi, Hindi and English. About 1 GB. Runs fully offline once downloaded.

## Install on your phone

1. Install **Google AI Edge Gallery** from the Play Store (Android) or the App Store (iPhone).
2. Open the app → **menu (top left)** → **Models**.
3. **Import new model** → **from Hugging Face**, and paste this URL:

```
https://huggingface.co/ravikadam/ganesh-gemma3-1b-LiteRT/resolve/main/ganesh-gemma3-1b-v2.litertlm
```

4. Wait for the download (about 1 GB — use Wi-Fi).
5. Tap **Try** and start chatting, e.g. *सुखकर्ता दुखहर्ता आरती म्हण* or *Recite Vakratunda Mahakaya*.

It is a small model: recitations are its strength; stories and detailed puja steps can be wrong.
For family customs and muhurat times, ask your elders and your panchang.

## For developers

* **Model card, scores and loss curve:** [release/g1b-v2/README.md](release/g1b-v2/README.md) ·
  [Hugging Face](https://huggingface.co/ravikadam/ganesh-gemma3-1b-LiteRT)
* **Corpus** (hand-verified canon, YAML): [`corpus/`](corpus)
* **Training data builders:** [`scripts/build_*.py`](scripts) → `data/train.jsonl`
* **Training:** [`runpod/train.py`](runpod/train.py) (full fine-tune for 1B, LoRA for Gemma 4) and
  the pod pipelines [`runpod/run_g1b.sh`](runpod/run_g1b.sh), [`runpod/run_g1b_v2.sh`](runpod/run_g1b_v2.sh)
* **Evaluation:** [`scripts/eval_run.py`](scripts/eval_run.py), prompts in [`evals/`](evals)
* **Phone export (LiteRT / Edge Gallery):** [`runpod/repack_litertlm_1b.sh`](runpod/repack_litertlm_1b.sh);
  the full story of what failed and why is in [PIPELINE.md](PIPELINE.md)

Made by [Ravi Kadam](https://www.linkedin.com/in/ravikadam/) for Ganeshotsav 2026.
Gemma is provided under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
