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

## Android

Any app that loads a local GGUF file will run this. Common ones on the Play Store
describe themselves as offline/local LLM chat apps and offer "import GGUF" or
"load local model". The steps are the same in all of them:

1. Download `ganesh-e2b-Q5_K_M.gguf` (3.4 GB) — on the phone, or on a computer
   and copy it across. `Download/` is the folder every file picker can see.
2. In the app choose **import / load local model** and pick the file.
3. First load is slow while it maps the weights; later loads are quick.

Budget about 6 GB of free RAM. On a phone with less it will either refuse to load
or swap badly.

## iPhone / iPad

Same file. Several iOS apps run local GGUF models; pick one that advertises
importing your own GGUF, then load it from Files or iCloud Drive. This is the
main reason we moved off LiteRT — Edge Gallery has no iOS build at all, GGUF
works on both platforms.

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
