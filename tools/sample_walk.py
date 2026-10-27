"""Send pad steps through vpadd and sample a guest float through memsrv while it moves.

Usage: sample_walk.py <guest addr> <left|right> <hold s>
       sample_walk.py <guest addr> steps "<vpadd steps>" <sample s>
Prints each change of the float as: time since the input started (ms), value, change.
"""
import socket
import struct
import sys
import threading
import time

addr, direction = int(sys.argv[1], 0), sys.argv[2]
if direction == "steps":
    steps, hold = sys.argv[3], float(sys.argv[4])
else:
    hold = float(sys.argv[3])
    steps = "%s:%s" % (direction, hold)


def read_float():
    s = socket.socket(socket.AF_UNIX)
    s.connect("/tmp/memsrv.sock")
    s.sendall(b"read %d 4\n" % addr)
    reply = b""
    while not reply.endswith(b"\n"):
        reply += s.recv(64)
    s.close()
    return struct.unpack(">f", bytes.fromhex(reply.decode().strip()))[0]


def press():
    with open("/tmp/vpad.fifo", "w") as f:
        f.write(steps + "\n")


t0 = time.monotonic()
threading.Thread(target=press).start()
last = read_float()
print("0 %.3f" % last)
while time.monotonic() - t0 < hold + 1.0:
    v = read_float()
    if v != last:
        print("%d %.3f %+.3f" % ((time.monotonic() - t0) * 1000, v, v - last))
        last = v
    time.sleep(0.004)
