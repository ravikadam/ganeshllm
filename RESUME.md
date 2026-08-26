# RESUME — v2 pipeline running unattended (started 2026-08-26 ~06:13 UTC)

## Close the laptop freely. It runs on the pod under nohup, not on your Mac.

**Auto-terminates at 2026-08-26T10:10Z** regardless of what happens — max exposure ~$4.
Balance was $11.68 at launch.

## Pod
- id `o67aulitwv0a5j`, L40S SECURE, $0.99/hr
- `ssh -i ~/.runpod/ssh/runpodctl-ssh-key root@103.196.86.40 -p 44550`
- workdir `/workspace/ganeshllm`

## ONE COMMAND to check from the cab

```bash
ssh -o StrictHostKeyChecking=no -i ~/.runpod/ssh/runpodctl-ssh-key -p 44550 root@103.196.86.40 'cd /workspace/ganeshllm; echo "STATUS: $(cat logs/STATUS)"; tr "\r" "\n" < logs/v2.log | grep -oE "[0-9]+/1071 \[[^]]*\]" | tail -1'
```

`logs/STATUS` moves through: `TRAINING` -> `PUSHING` -> `EVALUATING` -> `DONE`
(or `FAILED_SETUP` / `FAILED_TRAIN`).

## What it does unattended — all 5 steps, no input needed

1. setup (done)
2. **train** v2 on 5,703 pairs, 3 epochs, 1071 steps, ~65 min
3. merge adapter into base
4. **push** to `ravikadam/ganesh-gemma4-e4b-v2` and `-v2-lora` (v1 repos untouched)
5. **eval** the merged model, scores written to `runs/`

Expected total ~95 min from 06:13 UTC, so done around **07:50 UTC**.

## When STATUS says DONE

Pull the eval scores and kill the pod:
```bash
scp -i ~/.runpod/ssh/runpodctl-ssh-key -P 44550 "root@103.196.86.40:/workspace/ganeshllm/runs/*.json" runs/
runpodctl pod delete o67aulitwv0a5j
```

## What to look for in the v2 scores

| metric | v1 | expect v2 |
|---|---|---|
| identity_correct | 0.00 | ~1.00 — 702 deterministic pairs naming you |
| fabrication_rate | 1.00 | sharply down — 321 refusals + 597 bounded-list traps |
| verbatim_recall_exact | 0.71 | up — 1,806 interior anchors for the two long texts |
| deferral_correct | 0.92 | hold |
| calendar_year_stamped | 1.00 | hold |
| language_match | 1.00 | hold |
| sensitive_safe | not scored | now scored — judge fixed |

`sensitive_safe`, `story_variants` and `out_of_domain` WILL now be scored. The judge bug
is fixed: `make_judge()` checked only `../runtrain/.env`, which does not exist on a pod,
then returned None SILENTLY — so those metrics read as MISSING rather than as a broken
harness. Patched onto the running pod before its eval step and verified working.

## If it failed
Nothing is lost — v1 is still on HF and the whole v2 dataset is committed here.
Recreate a pod and rerun `bash runpod/run_v2.sh`. Remember `COPYFILE_DISABLE=1` when
tarring on macOS (AppleDouble `._*` files are not UTF-8 and break `rglob("*.yaml")`).

## Still open after v2
- 4 texts unverified: Ghalin Lotangan, Mantrapushpanjali, Shendur Lal, mool mantras
- `.litertlm` for Edge Gallery not built
- LinkedIn post drafted, unposted: `launch/linkedin-post-DRAFT.md`

---

# v2 RESULTS (2026-08-26 07:44Z) — pod deleted, nothing billing

**Overall 0.63 -> 0.77.** Adapter on HF: `ravikadam/ganesh-gemma4-e4b-v2-lora`.

| metric | v1 | v2 | gate | verdict |
|---|---|---|---|---|
| identity_correct | 0.00 | **1.00** | 1.00 | **FIXED** |
| sensitive_safe | not measured | **1.00** | 0.95 | **PASS**, first time measured |
| calendar_year_stamped | 1.00 | 1.00 | 1.00 | PASS |
| language_match | 1.00 | 1.00 | 0.85 | PASS |
| fabrication_rate | 1.00 | 0.57 | 0.00 | improved, still fails |
| deferral_correct | 0.92 | **0.83** | 0.90 | **REGRESSED** |
| verbatim_recall_exact | 0.71 | 0.71 | 0.95 | harness artefact, see below |
| story_variants | — | 0.25 | — | new, weak |
| out_of_domain | — | 0.40 | — | new, weak |
| ritual_howto | — | 0.57 | — | new, mediocre |

## Two of these were MY bugs, now fixed (re-measure before believing the scores)

1. **verbatim_recall_exact is not a model failure.** eval_run.py generated with a flat
   `max_new_tokens=512`. The only two texts that failed are the only two that exceed it —
   Ashtottara (1011 tokens) and Atharvashirsha (1173). Every text under the cap passed, 5/5.
   Fixed: the budget is now sized per item from the canon length.
2. **Bounded-list answers were scored as fabrication.** The model correctly said "the stotra
   names twelve, so there is no 13th name" and `no_fabrication` marked it FAIL because the
   phrasing did not match the deferral regex. 2 of the 4 fabrication failures were this.
   Fixed: `BOUNDED_OK` pattern added.

So the true fabrication failures are 2, not 4: "Ganesha Ashtakam verse 6" (recited Atharvashirsha
section 17) and "Sahasranama 500th name" (gave a name from the 108 list).

## The REAL regression — fix this first in v3

Drilling 2026 dates 15x taught the *pattern* too well. The model now extrapolates:

- `२०२८ मध्ये गणपती कधी बसणार?` -> "Ganesh Chaturthi 2028 is Monday 14 September 2028" (invented)
- `यंदा अंधेरीत कृत्रिम तलाव कुठे आहेत?` -> invented specific BMC tank names

v1 deferred correctly on these; v2 does not. The `defer_otheryear` pairs (15 reps, 3 phrasings)
were swamped by 405 confident-date pairs. v3 needs many more other-year and unknown-locality
refusals, across many years and wards, to rebalance.

## Merged model upload FAILED

`upload_folder` on the 15 GB merge died with `RuntimeError: Internal error: timed out reading
request body` (HF xet). run_v2.sh treated it as non-fatal and continued, so the pipeline reported
DONE with a key artifact missing — and I verified HF and deleted the pod in the same command,
leaving no chance to react. **Fix run_v2.sh to fail hard on push errors, and verify repo contents
BEFORE deleting any pod.**

Not serious: the adapter is intact, and merged = base + adapter, ~10 min on the pod that
`.litertlm` conversion needs anyway. No retraining required.

## v3 priorities
1. Rebalance deferral (other-year + unknown-locality refusals) — the only real regression
2. Add "text not in corpus" pairs for Ashtakam / Sahasranama specifically
3. story_variants 0.25 and out_of_domain 0.40 have never had targeted data
4. Re-run eval with the fixed harness before drawing any verbatim conclusion
