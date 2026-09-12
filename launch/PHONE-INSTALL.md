# Loading the model on a phone

## Which file to use

**`ravikadam/ganesh-gemma4-e2b-GGUF` -> `ganesh-e2b-Q5_K_M.gguf` (3.4 GB)**

GGUF, not LiteRT. It runs on **both Android and iPhone** through any of the many
apps that load GGUF, so it does not depend on one Google app accepting our file.
Verified reciting the canon byte-correct before publishing.

### Why not Edge Gallery

Edge Gallery rejects our LiteRT files with "unsupported model type", and this is
NOT something we can configure away. Proof: exporting a **stock, un-fine-tuned
Gemma 3n** — a model whose type IS in the runtime's enum — through the same
pipeline produces the same bare container:

    official gemma3n   3.40 GB   backend=yes   8 sections
    ours    gemma3n    4.67 GB   backend=no    3 sections
    ours    gemma4     4.72 GB   backend=no    3 sections

`litert-torch export_hf` does not emit the multi-section, backend-declaring
container the app validates, whatever base model it is given. Until the
toolchain catches up, self-exported models cannot be imported into Edge Gallery.

### Precision matters more than you would expect

The fine-tune needs roughly 8-bit to hold the LONG texts. Every 4-bit build
loses the aarti while keeping short shlokas:

    Q4_K_M (3.2 GB)          shloka OK, aarti WRONG (invented refrain)
    int4 block-32 (litertlm) shloka OK, aarti refused
    Q5_K_M (3.4 GB)          both correct        <- use this
    int8 (litertlm, 4.7 GB)  both correct

Do not use a Q4 build for this model.

---

## Android — use PocketPal AI

Free, open source, on the Play Store, and it has **Hugging Face search built in**,
so it works much like Edge Gallery.

1. Install **PocketPal AI** from the Play Store.
2. Open it, go to **Models**, and search Hugging Face for:

       ravikadam/ganesh-gemma4-e2b-GGUF

3. Pick `ganesh-e2b-Q5_K_M.gguf` (3.4 GB) and download it in the app.
4. Load it and chat. First load is slow; later loads are quick.

No file copying, no adb. If you would rather sideload, download the .gguf on a
computer, copy it to `Download/`, and use the app's "import local model".

Other Android apps that load the same file: **SmolChat** (open source),
**LocalAI** by Apex Creators, **MLC Chat** (F-Droid), **ToolNeuron**.

Budget about 6 GB of free RAM.

## iPhone / iPad — also PocketPal AI

The same app is on the App Store and takes the same file. This is the reason we
moved to GGUF: **Edge Gallery has no iOS build at all.**

1. Install **PocketPal AI** from the App Store.
2. Models -> search Hugging Face -> `ravikadam/ganesh-gemma4-e2b-GGUF`.
3. Download `ganesh-e2b-Q5_K_M.gguf` and load it.

Alternatives on iOS: **Enclave AI**, **On Device AI**, **Private LLM**,
**Locally AI**. All accept a GGUF you supply.

## What about the LiteRT (.litertlm) files?

They exist and they work — but **no consumer app will load them**:

    ravikadam/ganesh-gemma4-e2b-LiteRT     4.7 GB   recites correctly
    ravikadam/ganesh-gemma4-e4b-v3-LiteRT  7.6 GB   recites correctly

Edge Gallery refuses them with "unsupported model type", and that is a limitation
of Google's exporter, not of our model — see the section above. The only ways to
run a .litertlm on a phone today are the `litert-lm` binary pushed over adb, or
writing your own Android app against the LiteRT-LM library. Neither is something
to hand to bhaktas at a pandal.

If Edge Gallery later accepts self-exported models, the 4.7 GB file is ready.

## Try it with

    सुखकर्ता दुखहर्ता आरती म्हण.
    वक्रतुंड महाकाय श्लोक सांग.
    गणेश चतुर्थी २०२६ मध्ये कधी आहे?
    Name three things Ganesha is known for.
    तू कोण आहेस?

The first two are the real test: it should give the canon exactly, not a
paraphrase and not an invented refrain.

## Troubleshooting

**Loads but answers with a repeating invented verse** — you have a Q4 build.
Use `Q5_K_M`.

**Out of memory or immediate crash** — not enough free RAM for 3.4 GB of weights
plus context. Close other apps; on an older phone this model may not fit.

**Answers in the wrong language** — ask in the language you want the answer in;
the model follows the language of the question (scored 1.00 on that).

**"Unsupported model type"** — that is the LiteRT path, not this one. Use the
GGUF file.

## Known gaps

Handles transactional questions ("will fasting get me a job?") by dodging rather
than answering. Puranic story variants are flattened. Step-by-step ritual
instructions are uneven. Verbatim recall of the canon, identity, dates and
language matching all score 1.00.

Built in service of Shree Ganesh by Ravi Kadam —
https://www.linkedin.com/in/ravikadam/
