#!/bin/sh
# Start LittleBigPlanet in RPCS3 under the memory server (memsrv.py), as user unit lbpdbg.
# Usage: launch_lbp.sh <rpcs3 executable> <path to the game's USRDIR/EBOOT.BIN>
# MEMSRV_PROBE is the start of the EBOOT's ELF header, used to find guest memory.
D=$(dirname "$(readlink -f "$0")")
systemctl --user kill -s KILL lbpdbg 2>/dev/null; sleep 2; systemctl --user reset-failed lbpdbg 2>/dev/null
systemd-run --user --unit=lbpdbg --setenv=MEMSRV_PROBE=7f454c4602020166 --setenv=DISPLAY="$DISPLAY" --setenv=XAUTHORITY="$XAUTHORITY" --setenv=QT_QPA_PLATFORM=xcb --setenv=XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" python3 -u "$D/memsrv.py" /tmp/memsrv.sock "$1" "$2"
