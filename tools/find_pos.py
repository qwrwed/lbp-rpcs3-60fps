"""Find guest floats that track Sackboy's x across six memory dumps.

Dumps /tmp/d0.bin..d5.bin come from `mq.py dump` over the ranges in /tmp/ranges.txt, taken:
idle, idle, after right, after right, after left, after left.
Prints every guest address whose value was still between the idle dumps, rose on both
right moves and fell on both left moves. Needs numpy.
"""
import numpy as np

R = [tuple(int(x, 16) for x in r.split("-")) for r in open("/tmp/ranges.txt").read().split()]
off = np.cumsum([0] + [b - a for a, b in R])


def guest(i):
    k = np.searchsorted(off, i, side="right") - 1
    return R[k][0] + i - off[k]


mm = [np.memmap("/tmp/d%d.bin" % i, dtype=">f4", mode="r") for i in range(6)]
n = len(mm[0])
step = 1 << 22
np.seterr(all="ignore")
hits = 0
for s in range(0, n, step):
    d = [m[s:s + step].astype(np.float32) for m in mm]
    a, b, c, e = d[2] - d[1], d[3] - d[2], d[4] - d[3], d[5] - d[4]
    ok = np.isfinite(d[0]) & np.isfinite(d[5]) & (np.abs(d[1]) < 2000) & (d[0] == d[1])
    ok &= (a > 20) & (b >= 0) & (c < -20) & (e < -20)
    for i in np.nonzero(ok)[0]:
        hits += 1
        print(hex(guest((s + i) * 4)), [round(float(x[i]), 3) for x in d], flush=True)
print("hits", hits, flush=True)
