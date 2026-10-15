#!/bin/bash
# Unattended chain: wait for the conversion notebook, then train 1024, then 1280. Log: weights_local/full_chain.log
cd /c/Users/ASUS/Desktop/MP-Code
LOG=weights_local/full_chain.log
K() { PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m kaggle "$@" 2>&1; }
wait_done() {
  while true; do
    s=$(K kernels status "$1" | tail -1 | sed 's/.*has status //')
    case "$s" in *RUNNING*|*QUEUED*|*queued*|*running*|*Errno*|*Timeout*|*Connection*) sleep 600;;
      *) echo "$(date '+%F %H:%M') $1 -> $s" >> $LOG; break;; esac
  done
}
echo "$(date '+%F %H:%M') chain started" >> $LOG
wait_done prakyats/wood-full-convert
for sz in 1024 1280; do
  (cd kaggle_upload/notebook_full_train/full_$sz && K kernels push -p . >> ../../../$LOG)
  sleep 120
  wait_done prakyats/yolo11s-wood-full-4cls-$sz
done
echo "$(date '+%F %H:%M') chain finished" >> $LOG
