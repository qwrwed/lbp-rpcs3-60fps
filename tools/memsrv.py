"""Start a program as a child and serve reads of its PS3 guest memory over a Unix socket.

Usage: memsrv.py <socket> <program> [args...]
The Yama ptrace_scope=1 rule lets a process read /proc/<pid>/mem of its descendants only,
so the emulator must be started by this script.

Protocol: one request line per connection, one reply.
  base                  -> host address of guest address 0 (found on first use)
  read <addr> <len>     -> hex bytes of guest memory
  pid                   -> pid of the process holding guest memory
  ranges                -> writable guest ranges, as hex lo-hi pairs
  write <addr> <hex>    -> writes the bytes into guest memory; replies the byte count
  dump <path> <lo-hi>.. -> writes those guest ranges, concatenated, to <path>; replies the byte count
The guest base is found as the descendant's readable mapping that starts with the bytes
given in env MEMSRV_PROBE (hex), which are the bytes at guest 0x10000, minus 0x10000.
"""
import os
import socket
import subprocess
import sys

sock_path, cmd = sys.argv[1], sys.argv[2:]
probe = bytes.fromhex(os.environ["MEMSRV_PROBE"])
child = subprocess.Popen(cmd)
state = {"pid": None, "base": None}


def descendants(root):
    kids = {}
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                ppid = int(open("/proc/%s/stat" % p).read().rsplit(")", 1)[1].split()[1])
            except OSError:
                continue
            kids.setdefault(ppid, []).append(int(p))
    out, todo = [], [root]
    while todo:
        p = todo.pop()
        out.append(p)
        todo += kids.get(p, [])
    return out


def find_base():
    notes = []
    for pid in descendants(child.pid):
        try:
            maps = open("/proc/%d/maps" % pid).read().splitlines()
            mem = open("/proc/%d/mem" % pid, "r+b", buffering=0)
        except OSError as exc:
            notes.append("%d open %s" % (pid, exc.strerror))
            continue
        for line in maps:
            lo, hi = (int(x, 16) for x in line.split()[0].split("-"))
            if lo & 0xFFFF or "r" not in line.split()[1] or hi - lo < len(probe):
                continue
            try:
                mem.seek(lo)
                got = mem.read(len(probe))
            except OSError:
                continue
            if got == probe:
                state["pid"], state["base"], state["mem"] = pid, lo - 0x10000, mem
                return ""
        notes.append("%d: no mapping starts with the probe" % pid)
        mem.close()
    return "; ".join(notes)


def handle(req):
    parts = req.split()
    if not state["base"]:
        notes = find_base()
        if not state["base"]:
            return "ERR base not found: " + notes
    if parts[0] == "base":
        return hex(state["base"])
    if parts[0] == "pid":
        return str(state["pid"])
    if parts[0] == "ranges":
        base, out = state["base"], []
        for line in open("/proc/%d/maps" % state["pid"]).read().splitlines():
            lo, hi = (int(x, 16) for x in line.split()[0].split("-"))
            if base <= lo and hi <= base + (1 << 32) and "rw" in line.split()[1]:
                out.append("%x-%x" % (lo - base, hi - base))
        return " ".join(out)
    if parts[0] == "dump":
        # dump <path> <lo-hi> [<lo-hi> ...]: raw guest bytes of each range, concatenated
        mem = state["mem"]
        total = 0
        with open(parts[1], "wb") as f:
            for r in parts[2:]:
                lo, hi = (int(x, 16) for x in r.split("-"))
                mem.seek(state["base"] + lo)
                f.write(mem.read(hi - lo))
                total += hi - lo
        return str(total)
    if parts[0] == "write":
        mem = state["mem"]
        mem.seek(state["base"] + int(parts[1], 0))
        return str(mem.write(bytes.fromhex(parts[2])))
    if parts[0] == "read":
        addr, n = int(parts[1], 0), int(parts[2], 0)
        mem = state["mem"]
        mem.seek(state["base"] + addr)
        return mem.read(n).hex()
    return "ERR unknown"


if os.path.exists(sock_path):
    os.unlink(sock_path)
srv = socket.socket(socket.AF_UNIX)
srv.bind(sock_path)
srv.listen(4)
while child.poll() is None:
    conn, _ = srv.accept()
    with conn:
        req = conn.makefile().readline()
        try:
            reply = handle(req)
        except Exception as exc:
            reply = "ERR %r" % exc
        conn.sendall((reply + "\n").encode())
