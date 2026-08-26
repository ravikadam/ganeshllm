# RESUME — v3 running unattended (launched 2026-08-26 ~08:00 UTC)

## Nothing needs you. Lose signal freely — it runs on the pod, not your Mac.
## Pod auto-terminates **10:58 UTC** no matter what. Max spend ~$3. Balance was $10.07.

## Check it (one command, works from a phone browser too)

```bash
cd ~/Documents/1learning/ganeshllm && ./monitor.sh once
```

Or on your phone: **runpod.io/console/pods** -> `ganeshllm-v3` -> web terminal:
`cd /workspace/ganeshllm && cat logs/STATUS && tail -20 logs/SUMMARY.txt`

STATUS: `TRAINING` -> `PUSHING` -> `EVALUATING` -> `DONE`
(or `FAILED_TRAIN` / `PUSH_FAILED` — the pod is deliberately LEFT RUNNING on push
failure so the adapters on disk stay recoverable.)

## Pod
- `lfei48508ctcbk`, L40S SECURE, $0.99/hr
- `ssh -i ~/.runpod/ssh/runpodctl-ssh-key root@202.181.159.220 -p 16049`

## Timeline (~1h50m from 08:00 UTC, so done ~09:50 UTC)
train 1146 steps ~60 min -> merge ~5 -> push+verify ~15 -> eval ~15 -> summary

## When DONE
```bash
scp -i ~/.runpod/ssh/runpodctl-ssh-key -P 16049 "root@202.181.159.220:/workspace/ganeshllm/logs/SUMMARY.txt" logs/
scp -i ~/.runpod/ssh/runpodctl-ssh-key -P 16049 "root@202.181.159.220:/workspace/ganeshllm/runs/*.json" runs/
runpodctl pod delete lfei48508ctcbk
```

## What v3 changes (dataset 5,703 -> 6,102; audit clean)
1. **Contradiction killed.** build_calendar said "In 2026 Chaturthi is 14 Sep"; gen_prose said
   "depends on the panchang" for the SAME question. Prose now drops date questions entirely.
2. **Deferral rebalanced 9:1 -> 3:1.** v2 invented "Ganesh Chaturthi 2028 is 14 September"
   because 225 confident-date pairs swamped 24 refusals. Now 76 refusals spanning 2024-2031.
3. **Locality refusals added (0 -> 71).** v2 invented BMC tank names because NOTHING taught it
   to refuse — not a weak signal, a missing one.

## Pipeline hardening (v2 lost a 15GB upload silently)
- push retries 4x with backoff, then **verifies repo size** and fails loudly
- on push failure the pod stays alive so adapters are recoverable
- eval uses `tee`, not `tail` — progress is visible live now
- `logs/SUMMARY.txt` written at the end: final losses + full eval table

## Reading the v3 scores
Compare **per-metric**, not overall — v3 measures more metrics than v1 did.

| metric | v1 | v2 | v3 target |
|---|---|---|---|
| identity_correct | 0.00 | 1.00 | hold 1.00 |
| sensitive_safe | — | 1.00 | hold |
| deferral_correct | 0.92 | 0.83 | **back above 0.90** — the point of v3 |
| fabrication_rate | 1.00 | 0.57 | lower; 2 of v2's 4 fails were grader bugs, now fixed |
| verbatim_recall_exact | 0.71 | 0.71 | **should jump** — the 512-token cap that truncated
  the two long texts is fixed; both exceed it (1011 and 1173 tokens) |

## After v3
LiteRT is the open question. Converting a fine-tuned Gemma 4 E4B to a working `.litertlm` is
NOT a documented workflow — litert-torch issues #994/#998/#1001 cover exactly this, and #994
reports E4B exports that load but emit pad tokens on device. GGUF is the reliable fallback for
laptop testing (Ollama/LM Studio). Decide after seeing v3's scores.

## Still open
- 4 texts unverified: Ghalin Lotangan, Mantrapushpanjali, Shendur Lal, mool mantras
- story_variants 0.25 and out_of_domain 0.40 have never had targeted data
- v2 merged model was lost to the failed upload; adapter `ganesh-gemma4-e4b-v2-lora` is intact
- LinkedIn post drafted, unposted: `launch/linkedin-post-DRAFT.md`
