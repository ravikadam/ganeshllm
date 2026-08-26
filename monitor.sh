#!/usr/bin/env bash
# Live monitor for the v2 run. Ctrl-C to quit — it does NOT affect training.
#   ./monitor.sh          refresh every 60s
#   ./monitor.sh 15       refresh every 15s
#   ./monitor.sh once     print once and exit
IP=202.181.159.220; PORT=16049; PODID=lfei48508ctcbk
KEY=~/.runpod/ssh/runpodctl-ssh-key
EVERY="${1:-60}"

snap() {
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o ConnectTimeout=15 -o LogLevel=ERROR -i "$KEY" -p "$PORT" root@$IP '
    cd /workspace/ganeshllm 2>/dev/null || { echo "STATE|no workdir"; exit; }
    echo "STATE|$(cat logs/STATUS 2>/dev/null || echo starting)"
    echo "STEP|$(tr "\r" "\n" < logs/v2.log 2>/dev/null | grep -oE "[0-9]+/1146 \[[^]]*\]" | tail -1)"
    echo "LOSS|$(tr "\r" "\n" < logs/v2.log 2>/dev/null | grep -oE "'"'"'loss'"'"': '"'"'[0-9.]*'"'"'" | tail -1)"
    echo "ACC|$(tr "\r" "\n" < logs/v2.log 2>/dev/null | grep -oE "'"'"'mean_token_accuracy'"'"': '"'"'[0-9.]*'"'"'" | tail -1)"
    echo "GPU|$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null)"
    echo "PHASE|$(grep -oE "STEP [0-9]/5 [a-z ()0-9,]*" logs/v2.log 2>/dev/null | tail -1)"
  ' 2>/dev/null
}

while :; do
  D=$(snap)
  ST=$(echo "$D"  | grep '^STATE|' | cut -d'|' -f2-)
  SP=$(echo "$D"  | grep '^STEP|'  | cut -d'|' -f2-)
  LS=$(echo "$D"  | grep '^LOSS|'  | cut -d'|' -f2-)
  AC=$(echo "$D"  | grep '^ACC|'   | cut -d'|' -f2-)
  GP=$(echo "$D"  | grep '^GPU|'   | cut -d'|' -f2-)
  PH=$(echo "$D"  | grep '^PHASE|' | cut -d'|' -f2-)
  BAL=$(runpodctl me -o json 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print('$%.2f left, $%.2f/hr' % (d['clientBalance'],d['currentSpendPerHr']))" 2>/dev/null)
  clear 2>/dev/null
  echo "ganeshllm v3  —  $(date '+%H:%M:%S')"
  echo "──────────────────────────────────────────────"
  printf "  status   %s\n" "${ST:-?}"
  printf "  phase    %s\n" "${PH:-—}"
  printf "  step     %s\n" "${SP:-—}"
  printf "  loss     %s   acc %s\n" "${LS:-—}" "${AC:-—}"
  printf "  gpu      %s\n" "${GP:-—}"
  printf "  billing  %s\n" "${BAL:-?}"
  echo "──────────────────────────────────────────────"
  case "$ST" in
    DONE) echo "  ✅ COMPLETE — collect and shut down:"
          echo "     scp -i $KEY -P $PORT 'root@$IP:/workspace/ganeshllm/runs/*.json' runs/"
          echo "     runpodctl pod delete $PODID"; break;;
    FAILED*) echo "  ❌ $ST — see logs/v2.log on the pod"; break;;
    *) echo "  auto-terminates 10:58 UTC · Ctrl-C is safe";;
  esac
  [ "$EVERY" = "once" ] && break
  sleep "$EVERY"
done
