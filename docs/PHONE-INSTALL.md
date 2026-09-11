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

## 2. Get the model file onto the phone

The app can pull models from Hugging Face, but a **personal repo is easier to
sideload than to browse to**, so download the file directly:

1. In the phone's browser open the repo's Files tab.
2. Download the `.litertlm` file (several GB — use Wi-Fi).
3. It lands in `Downloads`.

Alternatively, from a computer with the phone connected:

```bash
adb push ganesh-v3-verified.litertlm /sdcard/Download/
```

## 3. Import it into the app

1. Open AI Edge Gallery.
2. Choose the **AI Chat** / **Ask Image**-style task tile — for this model, plain
   chat.
3. Use the **+** / **Import model** control (wording varies by release) and pick
   the `.litertlm` from `Downloads`.
4. First load takes a while — it is unpacking several GB. Subsequent loads are fast.

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
