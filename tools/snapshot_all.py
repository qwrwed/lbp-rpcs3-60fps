"""One-shot snapshot of every PPU thread through RPCS3's GDB server: PC, LR and a short stack walk.

Usage: snapshot_all.py <host:port> <out.txt>
Each thread's line is written and flushed as soon as it is read. The connection is left
open at the end, because RPCS3's server freezes the emulator when a client disconnects.
"""
import os
import sys
import time

sys.argv, out_path = sys.argv[:2], sys.argv[2]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rsp.py")).read().split("\ndef main")[0])

out = open(out_path, "w", buffering=1)
r = RSP(sys.argv[1])
out.write("reason " + r.cmd("?") + "\n")
tids = [t for t in r.cmd("qfThreadInfo").lstrip("m").split(",") if t]
out.write("threads %d\n" % len(tids))
for tid in tids:
    r.cmd("Hg" + tid)
    pc, lr = read_reg(r, 64), read_reg(r, 67)
    sp = read_reg(r, 1)
    chain = []
    for _ in range(10):
        if not sp:
            break
        m = r.cmd("m%x,8" % sp)
        if not m or m.startswith("E"):
            break
        back = int(m, 16) & 0xFFFFFFFF
        if not back:
            break
        m2 = r.cmd("m%x,8" % (back + 16))
        if m2 and not m2.startswith("E"):
            chain.append(hex(int(m2, 16) & 0xFFFFFFFF))
        sp = back
    out.write("%s pc %s lr %s stack %s\n" % (tid[-3:], pc and hex(pc), lr and hex(lr), " ".join(chain)))
out.write("done\n")
time.sleep(600)
