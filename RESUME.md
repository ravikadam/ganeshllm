# RESUME — eval of v1 in flight (2026-08-26)

## If you closed the laptop: THE POD SELF-TERMINATES at 2026-08-26T05:00:10Z.
No action needed to stop billing. Verify anytime with:
```
runpodctl pod list
```

## Pod in use
- id `gg0xrqgpg3mo6r` (name ganeshllm-eval), L40S SECURE, $0.99/hr, auto-terminate 05:00Z
- ssh: `ssh -i ~/.runpod/ssh/runpodctl-ssh-key root@64.247.206.212 -p 13290`
- workdir `/workspace/ganeshllm`, log `logs/eval.log`

## What is running
`python3 scripts/eval_run.py --backend hf --model ravikadam/ganesh-gemma4-e4b`
90 behavioural items + 7 auto-derived verbatim-recall items, OpenAI judge for the
rubric categories. Writes scores into the run ledger and `runs/<id>-details.json`.

## To collect results if the pod is still alive
```
scp -i ~/.runpod/ssh/runpodctl-ssh-key -P 13290 \
  root@64.247.206.212:/workspace/ganeshllm/runs/*.json runs/
```

## If the pod is gone, just rerun it — nothing is lost
The model is safe on HF (`ravikadam/ganesh-gemma4-e4b`). The eval is cheap to repeat:
create a pod, upload `scripts/ evals/ corpus/ runs/`, `pip install --break-system-packages
transformers peft openai pyyaml`, copy `~/.cache/huggingface/token` and `runtrain/.env`, run
the command above.

## Gotchas already hit (do not rediscover)
- macOS `tar` ships AppleDouble `._*` files that `rglob("*.yaml")` picks up and that are not
  UTF-8. Run `find . -name "._*" -delete` on the pod after extracting, or use
  `COPYFILE_DISABLE=1 tar czf ...` when creating the bundle.
- transformers 5.x `apply_chat_template` returns a dict — already fixed in `eval_run.py`.

## Known result to expect
`fabrication_rate` should FAIL — v1 recites Sankatnashan when asked for the
Vajrakavacha stotra. That is the known blocker for release.
