# Loading the model on a phone

## Status — read this first

As of 2026-09-11 there is **no verified working phone build yet**. The files currently
sitting in `ravikadam/ganesh-gemma4-e4b-v3-LiteRT` (`model.litertlm`, `model_q.litertlm`)
are the ones Edge Gallery rejected with "unsupported model type". Do not expect them to
work. A corrected export is being tested; when one passes its own run test it will be
pushed as `ganesh-v3-verified.litertlm`.

Until then, the steps below are verified against the **official** Google model, which
does work. Use it to get Edge Gallery set up and confirm your phone is ready, so that
loading ours later is a one-file swap.

---

## Android

Edge Gallery is Android-only. There is no official iOS build.

### 1. Install Google AI Edge Gallery

Either:
- **Play Store** — search "Google AI Edge Gallery" (published by Google), or
- **GitHub release APK** — https://github.com/google-ai-edge/gallery/releases
  Download the `.apk`, then allow "Install unknown apps" for your browser or file
  manager when prompted.

Needs roughly 8 GB free for a 4 GB model plus working space, and realistically 8 GB of
RAM. On less, it will either refuse to load or be very slow.

### 2a. Load a model from Hugging Face (easiest)

Open the app → **Import model** / the model browser → paste or search a repo id:

    litert-community/gemma-4-E2B-it-litert-lm

Pick the plain `gemma-4-E2B-it.litertlm` (about 2.6 GB) — **not** the `-gpu`, `-web`,
or vendor-specific (`_qualcomm_`, `_intel_`, `Google_Tensor_`) variants, which are built
for particular hardware and will fail to load elsewhere.

Signing in to Hugging Face inside the app may be required for gated repos.

### 2b. Load a model from a file (how ours will be installed)

1. Download the `.litertlm` on a computer.
2. Copy it to the phone over USB, or upload to Drive and download on the phone.
   Put it somewhere the file picker can reach — `Download/` is reliable.
3. In Edge Gallery choose **Import model** → **From local file** → pick the file.
4. Wait for it to index. First load is slow; later loads are fast.

### 3. Talk to it

Open **AI Chat**, select the model, and ask something. Try:

    सुखकर्ता दुखहर्ता आरती म्हण.
    वक्रतुंड महाकाय श्लोक सांग.
    Name three things Ganesha is known for.

If it answers with looping nonsense or Latin-script word salad in reply to Marathi, the
build is bad — that is exactly the failure being chased right now. Report it rather than
assuming the phone is at fault.

---

## iPhone / iPad

There is no official Edge Gallery for iOS. Options, roughly in order of effort:

- **Any third-party on-device LLM app that accepts GGUF.** This is the usual iOS route.
  It needs a GGUF build, which we do not have yet — the conversion currently fails with
  a transformers tokenizer mismatch (`extra_special_tokens` is a list where a dict is
  expected). Tracked, not yet fixed.
- **Build LiteRT-LM into a small SwiftUI app yourself** — supported by Google's runtime
  but a real development task, not an afternoon.
- **Demo from a laptop** at the pandal instead. Least glamorous, most certain.

---

## Troubleshooting

**"Unsupported model type"** — the container's model-type metadata is not one Edge
Gallery recognises. Not fixable on the phone; the export has to change.

**Loads, then dies on the first message** — usually the chat template. Gemma 4 uses
`<|turn>` / `<|channel>`, not Gemma 3's `<start_of_turn>`. A model exported with the
wrong template loads fine and then emits its own control tokens as visible text.

**Out of memory / immediate crash** — model too large for the device. A 4 GB int4 build
needs about 8 GB RAM. Try the 2 GB E2B model first to confirm the app works at all.

**Downloads but never appears** — check the file actually landed in a directory the
picker can see, and that the extension is exactly `.litertlm`.
