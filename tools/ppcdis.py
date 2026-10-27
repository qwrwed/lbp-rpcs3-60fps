"""Disassemble PPU code from a decrypted LittleBigPlanet EBOOT (ELF) with capstone.

Usage: ppcdis.py <EBOOT.elf> <hex addr> <count>
Assumes the code segment starts at file offset 0x468 and loads at 0x10000.
"""
import sys

import capstone

d = open(sys.argv[1], 'rb').read()[0x468:]
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)
a0, n = int(sys.argv[2], 16), int(sys.argv[3])
code = d[a0 - 0x10000:a0 - 0x10000 + 4 * n]
for i in range(n):
    w = code[4 * i:4 * i + 4]
    ins = list(md.disasm(w, a0 + 4 * i))
    print(hex(a0 + 4 * i), w.hex(), (ins[0].mnemonic + ' ' + ins[0].op_str) if ins else '?')
