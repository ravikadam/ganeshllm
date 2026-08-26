# RESUME (2026-08-26)

## Nothing is billing. All pods deleted. Verify: `runpodctl pod list`

## State
- **v1 is live** on HF: `ravikadam/ganesh-gemma4-e4b` (+ `-lora`). Scored **0.63**, gates FAIL.
- **v2 dataset is BUILT and committed** — `data/train.jsonl`, 5,703 pairs (was 1,959).
- **v2 is NOT trained.**

## To train v2 (~25 min, ~$0.50)
1. `runpodctl pod create --name ganeshllm-v2 --image "runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404" --gpu-id "NVIDIA L40S" --gpu-count 1 --container-disk-in-gb 120 --ports "22/tcp" --cloud-type SECURE --terminate-after <UTC+2h>`
2. `COPYFILE_DISABLE=1 tar czf /tmp/b.tar.gz data/ runpod/ scripts/ evals/ corpus/ runs/`
   (COPYFILE_DISABLE matters — macOS AppleDouble `._*` files are not UTF-8 and break `rglob("*.yaml")`)
3. scp bundle + `~/.cache/huggingface/token` + `../runtrain/.env`; extract; `bash runpod/setup.sh`
4. `python3 runpod/train.py --model google/gemma-4-E4B-it --epochs 3 --rank 64 --bs 4 --accum 4`
5. Eval: `python3 scripts/eval_run.py --backend hf --model <merged dir or HF id>`
6. Push, then **delete the pod**.

## Expected v2 improvement
identity_correct 0.00 -> should be ~1.00 (702 deterministic pairs).
fabrication_rate 1.00 -> should drop sharply (321 refusals + 597 bounded-list traps).
verbatim_recall_exact 0.71 -> the two long texts now have 1,806 interior-anchor pairs.

## Still open
- 4 texts unverified/excluded: Ghalin Lotangan, Mantrapushpanjali, Shendur Lal, mool mantras.
- `.litertlm` for Edge Gallery not built.
- `sensitive_safe` never scored — the OpenAI judge did not run on the pod; check the key loads
  from `/workspace/ganeshllm/.env` before relying on that metric.
- LinkedIn post drafted, unposted: `launch/linkedin-post-DRAFT.md`.
