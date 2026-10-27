"""Find guest data floats that change Sackboy's jump, by halving groups of them live.

Usage: bisect_jump.py <height addr> <floats file>
The floats file has lines "<hex addr> <hex original value>". Only entries whose live value
still equals the original are changed, and every change is undone after its test jump.
A group has an effect when the jump's peak upward speed moves by more than 3 from the
baseline. Prints each test and every single address found, then "done".
"""
import socket
import struct
import sys
import time


def q(line):
    s = socket.socket(socket.AF_UNIX)
    s.connect("/tmp/memsrv.sock")
    s.sendall((line + "\n").encode())
    r = b""
    while not r.endswith(b"\n"):
        r += s.recv(1 << 16)
    return r.decode().strip()


def rf(a):
    return struct.unpack(">f", bytes.fromhex(q("read %d 4" % a)))[0]


Y = int(sys.argv[1], 0)
ALL = [(int(a, 16), w) for a, w in (l.split() for l in open(sys.argv[2]) if l.strip())]


def peak():
    with open("/tmp/vpad.fifo", "w") as f:
        f.write("press:a\n")
    t0 = time.monotonic()
    ys = [rf(Y)]
    while time.monotonic() - t0 < 0.6:
        y = rf(Y)
        if y != ys[-1]:
            ys.append(y)
        time.sleep(0.002)
    d = [b - a for a, b in zip(ys, ys[1:]) if abs(b - a) < 80]
    time.sleep(1.6)
    return max(d) if d else 0.0


def test(lo, hi):
    live = [(a, w) for a, w in ALL[lo:hi] if q("read %d 4" % a) == w]
    for a, w in live:
        f = struct.unpack(">f", bytes.fromhex(w))[0]
        q("write %d %s" % (a, struct.pack(">f", f / 2).hex()))
    time.sleep(0.2)
    p = peak()
    for a, w in live:
        q("write %d %s" % (a, w))
    eff = abs(p - BASE) > 3
    print("test", lo, hi, "changed", len(live), "peak %.2f" % p, "EFFECT" if eff else "", flush=True)
    return eff


def rec(lo, hi):
    if not test(lo, hi):
        return
    if hi - lo == 1:
        print("FOUND", hex(ALL[lo][0]), ALL[lo][1], flush=True)
        return
    mid = (lo + hi) // 2
    rec(lo, mid)
    rec(mid, hi)


def halve(items):
    live = [(a, w) for a, w in items if q("read %d 4" % a) == w]
    for a, w in live:
        f = struct.unpack(">f", bytes.fromhex(w))[0]
        q("write %d %s" % (a, struct.pack(">f", f / 2).hex()))
    return live


def restore(live):
    for a, w in live:
        q("write %d %s" % (a, w))


BASE = peak()
print("baseline peak %.2f" % BASE, flush=True)
if len(sys.argv) > 3 and sys.argv[3] == "pairs":
    # Values may only act together: keep one half halved while bisecting the other.
    mid = len(ALL) // 2
    for keep, search in (((0, mid), (mid, len(ALL))), ((mid, len(ALL)), (0, mid))):
        held = halve(ALL[keep[0]:keep[1]])
        print("holding", keep, "halved", flush=True)
        rec(*search)
        restore(held)
elif len(sys.argv) > 3 and sys.argv[3].startswith("chunk="):
    # Test fixed-size chunks first, so no single test changes too much at once.
    size = int(sys.argv[3].split("=")[1])
    for lo in range(0, len(ALL), size):
        rec(lo, min(lo + size, len(ALL)))
else:
    rec(0, len(ALL))
print("done", flush=True)
