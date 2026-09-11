# Loading the model on a phone

## Status — read this first

**There is a verified working build.** Download:

    ravikadam/ganesh-gemma4-e4b-v3-LiteRT  ->  ganesh-v3-int8-verified.litertlm  (7.6 GB)

It was executed before publishing: it recites Sukhkarta Dukhharta complete and
correct, and answers English questions coherently.

**Do not download `model_q.litertlm`** (3.8 GB). It is an int4 build whose output
begins correctly and then collapses into a loop with foreign characters spliced in.
`model.litertlm` is superseded — wrong chat template.

Needs about 12 GB RAM, so a flagship phone. If yours has 8 GB, test with the
official `litert-community/gemma-4-E2B-it-litert-lm` (2.6 GB) first to confirm the
app works, and expect ours to be tight or to fail to load.

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
