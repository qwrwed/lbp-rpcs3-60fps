#!/bin/sh
# Restart LittleBigPlanet under the memory server and press through to the pod with vpadd
# (8 presses of A, about 40 s; Sackboy ends at the pod computer). With "level", also open the
# pod computer and enter the first level (The Meerkat Kingdom, about 35 s more).
# Needs vpadd.py running on /tmp/vpad.fifo before RPCS3 starts, and player 1 set to its pad.
# Usage: boot_lbp.sh <rpcs3 executable> <path to the game's USRDIR/EBOOT.BIN> [level]
D=$(dirname "$(readlink -f "$0")")
sh "$D/launch_lbp.sh" "$1" "$2" >/dev/null 2>&1
S=''
for i in 1 2 3 4 5 6 7 8; do S="$S wait:4 press:a"; done
[ "$3" = level ] && S="$S wait:2 press:x wait:6 press:a wait:6 press:a wait:6 press:a wait:5 press:a wait:12"
echo "$S" > /tmp/vpad.fifo
date +%T
