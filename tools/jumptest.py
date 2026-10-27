"""Measure a jump through memsrv and vpadd, optionally with guest floats halved during it.

Usage: jumptest.py <height addr> [<addr> ...]
Each extra address holds a float that is halved for the jump and restored after.
Prints the steepest upward step per tick (v0), the mean change per tick after it (g)
and the number of ticks in which the height changed.
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


def wf(a, v):
    q("write %d %s" % (a, struct.pack(">f", v).hex()))


def jump(y_addr):
    with open("/tmp/vpad.fifo", "w") as f:
        f.write("press:a\n")
    t0 = time.monotonic()
    ys = [rf(y_addr)]
    while time.monotonic() - t0 < 1.4:
        y = rf(y_addr)
        if y != ys[-1]:
            ys.append(y)
        time.sleep(0.002)
    d = [b - a for a, b in zip(ys, ys[1:])]
    if not d:
        return "v0 0.00 g 0.000 ticks 0"
    vmin = min(d)
    i = d.index(vmin)
    g = [b - a for a, b in zip(d[i + 1:i + 8], d[i + 2:i + 9])]
    return "v0 %.2f g %.3f ticks %d" % (vmin, sum(g) / len(g) if g else 0, len(d))


if __name__ == "__main__":
    y_addr = int(sys.argv[1], 0)
    halved = [int(a, 0) for a in sys.argv[2:]]
    old = [rf(a) for a in halved]
    for a, v in zip(halved, old):
        wf(a, v / 2)
    time.sleep(0.2)
    try:
        print(jump(y_addr))
    finally:
        for a, v in zip(halved, old):
            wf(a, v)
