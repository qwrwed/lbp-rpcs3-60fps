"""Minimal GDB remote-protocol client for RPCS3's GDB server (PPU threads).

Usage: rsp.py <host:port> <command> [args]
Commands:
  threads                 list thread ids and each thread's PC and LR
  sample <n> <gap_s>      n times: interrupt, record main thread PC/LR and a short stack walk, continue
  mem <addr> <len>        read memory (hex)
Connecting pauses emulation; every command ends by continuing it.
"""
import socket
import struct
import sys
import time


class RSP:
    def __init__(self, hostport):
        host, port = hostport.rsplit(":", 1)
        self.s = socket.create_connection((host, int(port)), timeout=10)
        self.buf = b""

    def _recv_packet(self):
        while True:
            i = self.buf.find(b"$")
            j = self.buf.find(b"#", i + 1) if i >= 0 else -1
            if i >= 0 and j >= 0 and len(self.buf) >= j + 3:
                data = self.buf[i + 1:j]
                self.buf = self.buf[j + 3:]
                self.s.sendall(b"+")
                return data.decode(errors="replace")
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buf += chunk

    def cmd(self, payload, expect_reply=True):
        csum = sum(payload.encode()) & 0xFF
        self.s.sendall(b"$" + payload.encode() + b"#" + b"%02x" % csum)
        return self._recv_packet() if expect_reply else None

    def interrupt(self):
        self.s.sendall(b"\x03")
        return self._recv_packet()

    def cont(self):
        csum = sum(b"vCont;c") & 0xFF
        self.s.sendall(b"$vCont;c#" + b"%02x" % csum)


def regs(r):
    raw = r.cmd("g")
    vals = [int(raw[i:i + 16], 16) for i in range(0, 32 * 16, 16)]
    return vals, raw


def read_reg(r, n):
    v = r.cmd("p%x" % n)
    return int(v, 16) if v and not v.startswith("E") else None


def main():
    r = RSP(sys.argv[1])
    what = sys.argv[2]
    print("reason:", r.cmd("?"), flush=True)
    if what == "threads":
        info = r.cmd("qfThreadInfo")
        print("threads:", info)
        for tid in info.lstrip("m").split(","):
            if not tid:
                continue
            r.cmd("Hg" + tid)
            # RPCS3 PPU register numbering: 0-31 GPR, 32-63 FPR, 64 PC, 65 MSR?, 66 CR, 67 LR, 68 CTR, 69 XER
            pc, lr = read_reg(r, 64), read_reg(r, 67)
            print(tid, "pc", pc and hex(pc), "lr", lr and hex(lr), flush=True)
    elif what == "sample":
        n, gap = int(sys.argv[3]), float(sys.argv[4])
        tid = sys.argv[5] if len(sys.argv) > 5 else None
        for k in range(n):
            if k:
                r.cont()
                time.sleep(gap)
                r.s.sendall(b"\x03")
                time.sleep(0.1)
                r.s.settimeout(0.3)
                try:
                    while r.s.recv(65536):
                        pass
                except (socket.timeout, TimeoutError):
                    pass
                r.s.settimeout(10)
                r.buf = b""
            if tid:
                r.cmd("Hg" + tid)
            gpr, _ = regs(r)
            pc, lr = read_reg(r, 64), read_reg(r, 67)
            sp = gpr[1]
            chain = []
            for _ in range(8):
                m = r.cmd("m%x,10" % sp)
                if not m or m.startswith("E") or len(m) < 32:
                    break
                back = int(m[0:16], 16) & 0xFFFFFFFF
                if not back:
                    break
                m2 = r.cmd("m%x,8" % (back + 16))
                if m2 and not m2.startswith("E"):
                    chain.append(hex(int(m2, 16) & 0xFFFFFFFF))
                sp = back
            print("sample", k, "pc", pc and hex(pc), "lr", lr and hex(lr), "stack", " ".join(chain), flush=True)
    elif what == "mem":
        print(r.cmd("m%x,%x" % (int(sys.argv[3], 16), int(sys.argv[4], 16))))
    r.cont()
    time.sleep(0.3)


main()
