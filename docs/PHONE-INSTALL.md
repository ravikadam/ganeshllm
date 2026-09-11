# Loading the model on a phone

## Platform reality

**Google AI Edge Gallery is Android-only.** There is no official iOS build, and
iOS cannot sideload a `.litertlm` this way. On iPhone the realistic options are a
separate app (e.g. an MLC/llama.cpp-based client with its own format) or running
the model on a laptop and reaching it over the local network. Everything below is
Android.

Practical requirements: **8 GB+ RAM** for a 4 GB int4 model, and roughly double the
model size free on storage during install.

## 1. Install AI Edge Gallery

Either:

- **Play Store** — search "Google AI Edge Gallery", or
- **APK** — https://github.com/google-ai-edge/gallery/releases, download the
  latest `.apk`. Android will ask you to allow installs from unknown sources for
  your browser/file manager; that prompt is expected for a sideloaded APK.

## 2. Import straight from a Hugging Face URL (easiest)

Edge Gallery can pull a model from a **Hugging Face model card URL** — no cable, no
file manager, no multi-GB download you have to babysit in a browser. Added in
v1.0.16 and called out again in v1.0.18 ("Hugging Face Imports: Seamlessly import
LiteRT-LM models using Hugging Face model card URLs"). Latest release is v1.0.19
(2 Sep 2026), so make sure you are on a current build.

In the app, choose the import option and paste the **model card URL** (the repo
page, not the raw file link):

    https://huggingface.co/ravikadam/ganesh-gemma4-e4b-v3-LiteRT

The repo must be **public**, and it must contain a `.litertlm` file.

## 3. Or sideload the file (fallback)

If URL import misbehaves, push the file directly:

```bash
adb push ganesh-v3-verified.litertlm /sdcard/Download/
```

Then in the app: tap the **+** icon at the bottom-right, pick the `.litertlm` from
the file picker, and in the **Import Model** dialog set the default parameters and
CPU/GPU preference. Leave "Support image"/"Support audio" unchecked — this is a
text-only export.

## 4. Verify it actually works

Do not assume a model that loads is a model that works. Ask it:

    सुखकर्ता दुखहर्ता आरती म्हण.

A correct answer begins `सुखकर्ता दुखहर्ता वार्ता विघ्नाची`. If you instead get
English word salad, looping text, or control tokens like `<|turn>` printed as
literal text, the file is broken — that is exactly the failure we hit on
2026-09-11, and it means the export is wrong, not your phone.

## Current status — read before downloading

As of 2026-09-11 there is **no verified-working `.litertlm` for this model yet.**

- `ravikadam/ganesh-gemma4-e4b-v3-LiteRT` currently holds `model.litertlm` and
  `model_q.litertlm` from the earlier v3 run. Edge Gallery **rejected** those with
  "unsupported model type", and we have since established they also carry the wrong
  chat template. **Do not bother loading them.**
- The fixed export is still being worked out. When one passes its run test it will
  be pushed as `ganesh-v3-verified.litertlm` — the name is the signal that it was
  actually executed and recited the canon before being uploaded.

Known-good comparison, if you want to see Edge Gallery working tonight: the stock
`litert-community/gemma-4-E2B-it-litert-lm` loads and answers correctly. It is not
our fine-tune — no shlokas from the corpus — but it confirms the app and phone are
fine.
