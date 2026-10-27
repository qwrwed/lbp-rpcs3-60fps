import socket,sys,time,threading
def rd(a):
    s=socket.socket(socket.AF_UNIX);s.connect("/tmp/memsrv.sock");s.sendall(b"read %d 4\n"%a)
    r=b""
    while not r.endswith(b"\n"): r+=s.recv(64)
    return r
addrs=[int(x,0) for x in sys.argv[2:]]
threading.Thread(target=lambda: open("/tmp/vpad.fifo","w").write(sys.argv[1]+":0.8\n")).start()
last={a:None for a in addrs}; n={a:0 for a in addrs}; t0=time.monotonic()
while time.monotonic()-t0<1.0:
    for a in addrs:
        v=rd(a)
        if v!=last[a]: n[a]+=1; last[a]=v
    time.sleep(0.002)
for a in addrs: print(hex(a), n[a])
