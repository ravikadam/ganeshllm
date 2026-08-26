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

`sensitive_safe` may still read MISSING if the OpenAI judge key does not load from
`/workspace/ganeshllm/.env` — that is a metric gap, not a model failure.

## If it failed
Nothing is lost — v1 is still on HF and the whole v2 dataset is committed here.
Recreate a pod and rerun `bash runpod/run_v2.sh`. Remember `COPYFILE_DISABLE=1` when
tarring on macOS (AppleDouble `._*` files are not UTF-8 and break `rglob("*.yaml")`).

## Still open after v2
- 4 texts unverified: Ghalin Lotangan, Mantrapushpanjali, Shendur Lal, mool mantras
- `.litertlm` for Edge Gallery not built
- LinkedIn post drafted, unposted: `launch/linkedin-post-DRAFT.md`
