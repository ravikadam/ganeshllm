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

## Current status (2026-09-11, verified)

**Use `ganesh-v3-int8-verified.litertlm` — 8.18 GB.**

    https://huggingface.co/ravikadam/ganesh-gemma4-e4b-v3-LiteRT

This build was executed before it was uploaded, and it recited the aarti correctly
across multiple verses:

    सुखकर्ता दुखहर्ता, वार्ता विघ्नांची ।
    नुरवी; पुरवी प्रेम, कृपा जयाची ।
    सर्वांगी सुंदर, उटी शेंदुराची ।
    कंठी झळके माळ, मुक्ताफळांची ॥१॥
    जय देव, जय देव जय मंगलमूर्ती ।

Uploaded bytes match the tested file exactly (8,180,845,792).

**Needs roughly 12 GB RAM.** At 8.18 GB this is not an 8 GB-phone model.

### Ignore the other two files

`model.litertlm` and `model_q.litertlm` are from 26 August. Edge Gallery rejected
them, and they carry the wrong chat template. They are kept only as a record.

### Why there is no 4 GB build

int4 (`dynamic_wi4_afp32`) destroys this fine-tune. Two independent int4 builds with
different flag sets both degenerated into repetition loops — one emitted the first
two words of the aarti and then looped a single phrase ~100 times. The identical
pipeline at int8 recites correctly. The base model survives int4 fine; the LoRA
fine-tune does not. A sub-4 GB build needs a different approach, not a different flag.
