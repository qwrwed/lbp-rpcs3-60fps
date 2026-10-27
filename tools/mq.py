"""Send one request to memsrv.py and print the reply. Usage: mq.py <request words...>"""
import socket
import sys

s = socket.socket(socket.AF_UNIX)
s.connect("/tmp/memsrv.sock")
s.sendall((" ".join(sys.argv[1:]) + "\n").encode())
b = b""
while not b.endswith(b"\n"):
    c = s.recv(1 << 20)
    if not c:
        break
    b += c
print(b.decode().strip())
