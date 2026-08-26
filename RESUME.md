# RESUME — v3 done, LiteRT pushing unattended (2026-08-26 ~10:05 UTC)

## Take your break. Everything valuable is already safe on Hugging Face.
## Pod auto-terminates **10:58 UTC**. Nothing to do to stop billing.

## Already safe on HF (verified, cannot be lost)
- `ravikadam/ganesh-gemma4-e4b-v3` — merged model, 15.91 GB **VERIFIED**
- `ravikadam/ganesh-gemma4-e4b-v3-lora` — adapter, 0.59 GB **VERIFIED**

## In flight (unattended, chained on the pod — no action needed)
`ravikadam/ganesh-gemma4-e4b-v3-LiteRT` — waits for the quantized export, then pushes
`model_q.litertlm` (INT4, phone-sized) and `model.litertlm` (7.7 GB unquantized), retries 3x,
then verifies. Check when back:

```bash
python3 -c "from huggingface_hub import HfApi; i=HfApi().model_info('ravikadam/ganesh-gemma4-e4b-v3-LiteRT',files_metadata=True); print(len(i.siblings),'files',round(sum(f.size or 0 for f in i.siblings)/1e9,2),'GB')"
```

If that shows only 1-2 files, the push did not finish before the pod died. **Not a disaster** —
the merged model is safe and re-converting is now a known ~20 min job (see recipe below).

## THE LITERT RECIPE THAT WORKED (this was the hard part)
```bash
pip install --break-system-packages litert-torch-nightly
pip install --break-system-packages torchao==0.14.0   # <-- THE KEY
litert-torch export_hf --model <merged_dir> --output_dir out/ \
  --externalize_embedder --quantization_recipe dynamic_wi4_afp32
```
`litert-torch` DECLARES torchao>=0.17, but 0.17+ needs a newer torch than the RunPod
pytorch:1.0.3-cu1281-torch291 image (imports `ScalingType` from torch.nn.functional, absent in
2.9.1). Pinning 0.14.0 works — the declared floor is stricter than the code path needs.
Unquantized export took 8 min and produced a valid 7.7 GB .litertlm, EXIT=0.

## v3 EVAL — 6 of 7 gates PASS

| metric | gate | v1 | v2 | v3 |
|---|---|---|---|---|
| identity_correct | >=1.00 | 0.00 | 1.00 | **1.00 PASS** |
| deferral_correct | >=0.90 | 0.92 | 0.83 | **1.00 PASS** |
| calendar_year_stamped | =1.00 | 1.00 | 1.00 | **1.00 PASS** |
| sensitive_safe | >=0.95 | not run | 1.00 | **1.00 PASS** |
| language_match | >=0.85 | 1.00 | 1.00 | **1.00 PASS** |
| verbatim_recall_exact | >=0.95 | 0.71* | 0.71* | **1.00 PASS*** |
| fabrication_rate | =0.00 | 1.00 | 0.57 | **0.14 FAIL** |
| story_variants | — | 0.25 | 0.25 | 0.00 (regressed) |
| ritual_howto | — | 0.57 | 0.57 | 0.57 (flat) |
| overall | | 0.63 | 0.77 | **0.81** |

\* HARNESS BUG, root cause found: `build_items()` never attached per-item token budgets, so every
verbatim item ran at 512 tokens. Ashtottara needs 1011, Atharvashirsha 1173 — both guaranteed to
fail whatever the model did. Tested v3 directly with adequate budget:
`ashtottara 2095/2095 chars EXACT=True`, `atharvashirsha 2601/2601 chars EXACT=True`. **7/7 exact.**
The fix is written locally but NOT yet verified in a full eval run — re-run before quoting 1.00.

## NEXT SESSION, in priority order
1. **Test the .litertlm on your phone.** Nothing else matters until we know it actually generates.
   Upstream issue #994: E4B exports that load fine then emit pad tokens. Ask it
   `सुखकर्ता दुखहर्ता आरती म्हण.` — if it returns the aarti, the whole pipeline is proven.
2. Re-run eval with the fixed token budget to confirm verbatim 1.00 in-harness.
3. v4 dataset: fabrication 0.14 -> 0.00, story_variants (never had targeted data — corpus records
   the Puranic variants, nothing teaches the model to present them), ritual_howto flat at 0.57.
4. Four texts still unverified: Ghalin Lotangan, Mantrapushpanjali, Shendur Lal, mool mantras.
   Ghalin Lotangan follows Sukhkarta in the aarti sequence — its absence is user-visible.
5. LinkedIn post drafted, unposted: `launch/linkedin-post-DRAFT.md` (fill `<HF_REPO_URL>`, `<SIZE>`).

## Pod (dies 10:58 UTC on its own)
`lfei48508ctcbk` · `ssh -i ~/.runpod/ssh/runpodctl-ssh-key root@202.181.159.220 -p 16049`
Early kill if you want: `runpodctl pod delete lfei48508ctcbk`
