#!/usr/bin/env bash
# Full-dataset chain v2 (Kaggle mirror, no Zenodo conversion):
#   CPU smoke test -> verify smoke_ok.json -> push 1024 and 1280 GPU runs (push retried every 10 min until accepted)
#   -> wait for each -> download outputs to weights_local/full_v2/<run>.
# Run from the repo root: bash kaggle_upload/run_full_chain_v2.sh
cd "$(dirname "$0")/.."
LOG=weights_local/full_chain_v2.log
OUT=weights_local/full_v2
K() { PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m kaggle "$@" 2>&1; }
say() { echo "$(date '+%Y-%m-%d %H:%M') $*" >> $LOG; }
status() { K kernels status prakyats/$1 | tail -n 1; }
push() {   # push until Kaggle accepts it
  for i in $(seq 1 60); do
    r=$(cd kaggle_upload/notebook_full_train/full_$1 && K kernels push -p .)
    echo "$r" >> $LOG
    if echo "$r" | grep -q "successfully pushed"; then say "pushed $2"; return 0; fi
    say "push of $2 refused, retry in 10 min"; sleep 600
  done
  say "giving up on $2"; return 1
}
wait_done() {   # wait until a kernel reaches a final state; echo it
  while true; do
    s=$(status $1)
    case "$s" in
      *COMPLETE*|*ERROR*|*CANCEL*) say "$1 -> $s"; echo "$s"; return;;
    esac
    sleep 600
  done
}
fetch() { mkdir -p $OUT/$2; K kernels output prakyats/$1 -p $OUT/$2 > /dev/null; say "downloaded $1 to $OUT/$2"; }

say "chain v2 started"
push smoke wood-full4-smoke || exit 1
sleep 120
s=$(wait_done wood-full4-smoke)
fetch wood-full4-smoke smoke
if ! grep -q '"ok": true' $OUT/smoke/smoke_ok.json 2>/dev/null; then
  say "SMOKE FAILED ($s) - GPU runs NOT started; see $OUT/smoke/*.log"; exit 1
fi
say "smoke OK: $(cat $OUT/smoke/smoke_ok.json)"
push 1024 wood-full4-v2-1024 || exit 1
sleep 300
push 1280 wood-full4-v2-1280 || exit 1
sleep 120
for r in 1024 1280; do
  s=$(wait_done wood-full4-v2-$r)
  fetch wood-full4-v2-$r $r
done
say "chain v2 finished"
