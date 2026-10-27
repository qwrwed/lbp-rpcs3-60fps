"""Make a guest u32 tick counter advance at half rate for a while, through memsrv.

Usage: halfclock.py <addr> <seconds>
Polls the counter; every increment the game makes is counted, and the counter is rewritten
to start + (increments // 2). Prints the poll rate and how many increments were seen.
"""
import socket
import sys
import time


def q(line):
    s = socket.socket(socket.AF_UNIX)
    s.connect("/tmp/memsrv.sock")
    s.sendall((line + "\n").encode())
    r = b""
    while not r.endswith(b"\n"):
        r += s.recv(4096)
    s.close()
    return r.decode().strip()


addr, secs = int(sys.argv[1], 0), float(sys.argv[2])
start = last = int(q("read %d 4" % addr), 16)
n = polls = 0
t0 = time.monotonic()
while time.monotonic() - t0 < secs:
    v = int(q("read %d 4" % addr), 16)
    polls += 1
    if v != last:
        n += (v - last) & 0xFFFFFFFF
        last = start + n // 2
        q("write %d %08x" % (addr, last))
print("polls/s %.0f increments %d" % (polls / secs, n))
