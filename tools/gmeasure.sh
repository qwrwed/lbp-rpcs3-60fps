#!/bin/sh
# Jump once and print gravity per tick², top upward step and ticks from a height address. Usage: gmeasure.sh <height addr>
D=$(dirname "$(readlink -f "$0")")
timeout 8 python3 "$D/sample_walk.py" $1 steps "press:a" 1.3 | python3 -c "
import sys,statistics
v=[float(l.split()[1]) for l in sys.stdin if len(l.split())>=2]
d=[b-a for a,b in zip(v,v[1:])]
d=[x for x in d if abs(x)<60]
g=[b-a for a,b in zip(d,d[1:]) if abs(b-a)<5]
print(\"median g %.3f  max up %.2f  ticks %d\"%(statistics.median(g),max(d),len(d)))"
