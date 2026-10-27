#!/bin/sh
# In the pod, find a per-tick copy of Sackboy's position and measure a jump with it.
# Needs memsrv.py (launch_lbp.sh), vpadd.py on /tmp/vpad.fifo, and numpy. Dumps go to /tmp (about 0.4 GB each).
# Prints the candidates tried and, for each, gravity per tick², top upward step and ticks.
D=$(dirname "$(readlink -f "$0")")
python3 "$D/mq.py" ranges > /tmp/ranges.txt
R=$(cat /tmp/ranges.txt)
for i in 0 1 2 3 4 5; do
  case $i in 2|3) echo "right:0.3" > /tmp/vpad.fifo; sleep 1.5 ;; 4|5) echo "left:0.3" > /tmp/vpad.fifo; sleep 1.5 ;; 1) sleep 0.5 ;; esac
  python3 "$D/mq.py" dump /tmp/d$i.bin $R > /dev/null
done
python3 "$D/find_pos.py" | grep "^0x" > /tmp/cands_all.txt
echo "candidates: $(wc -l < /tmp/cands_all.txt)"
A=$(awk '{p=substr($1,1,6); if(!(p in s)){s[p]=1; print $1}}' /tmp/cands_all.txt)
python3 "$D/rate.py" right $A | sort -k2 -n -r | head -3 | while read a n; do
  y=$(printf "0x%x" $((a + 4)))
  sleep 1
  echo "$a ($n changes/s) height $y: $(sh "$D/gmeasure.sh" $y)"
done
