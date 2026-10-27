"""Install frame-doubled copies of LittleBigPlanet animations as loose files the game accepts.

Usage (run from the update's USRDIR): anim_install.py <disc USRDIR> <base map> <path substring> [<looping name> ...]
Takes every .anim whose path contains the substring, from the update's map (original bytes
from the update's data.farc) or, if only on the disc, from the disc's blurayguids.map and
data.farc. Each is frame-doubled with anim_resample (clips named in <looping name> loop,
the rest clamp), written to USRDIR/<path>, and entered in output/brg_patch.map, which is
rebuilt from <base map> (entries updated in place; disc-only entries appended).
"""
import hashlib
import os
import struct
import sys

import anim_resample
import lbpmod


def read_entries(path):
    b = open(path, "rb").read()
    n = struct.unpack(">I", b[4:8])[0]
    p, out = 8, {}
    for _ in range(n):
        ln = struct.unpack(">I", b[p:p + 4])[0]
        name = b[p + 4:p + 4 + ln].decode()
        out[name] = b[p + 4 + ln:p + 4 + ln + 36]
        p += 4 + ln + 36
    return out


def farc_reader(path):
    size = os.path.getsize(path)
    f = open(path, "rb")
    f.seek(size - 8)
    n = struct.unpack(">I", f.read(4))[0]
    f.seek(size - 8 - n * 28)
    t = f.read(n * 28)
    idx = {t[k * 28:k * 28 + 20]: struct.unpack(">II", t[k * 28 + 20:k * 28 + 28]) for k in range(n)}

    def get(sha):
        off, sz = idx[sha]
        f.seek(off)
        return f.read(sz)
    return get


def main():
    disc, base_map, sub = sys.argv[1], sys.argv[2], sys.argv[3]
    looping = set(sys.argv[4:])
    upd = read_entries(base_map)
    dsc = read_entries(os.path.join(disc, "output", "blurayguids.map"))
    get_upd, get_dsc = farc_reader("data.farc"), farc_reader(os.path.join(disc, "data.farc"))
    m = bytearray(open(base_map, "rb").read())
    _, ents = lbpmod.read_map(base_map)
    count = struct.unpack(">I", m[4:8])[0]
    names = sorted({n for n in list(upd) + list(dsc) if n.endswith(".anim") and sub in n})
    done = skipped = 0
    for name in names:
        src = upd.get(name) or dsc[name]
        res = (get_upd if name in upd else get_dsc)(src[12:32])
        assert hashlib.sha1(res).digest() == src[12:32]
        magic, rev, unk, data, deps = lbpmod.unpack_binary(res)
        if int.from_bytes(rev, "big") >= 0x378:
            skipped += 1
            continue
        a = anim_resample.parse(data)
        loop = os.path.basename(name)[:-5] in looping
        out = lbpmod.pack_binary(magic, rev, unk, anim_resample.build(anim_resample.resample(a, loop)), deps)
        os.makedirs(os.path.dirname(name), exist_ok=True)
        open(name, "wb").write(out)
        if name in ents:
            e = ents[name]
            m[e["size_at"]:e["size_at"] + 4] = struct.pack(">I", len(out))
            m[e["sha_at"]:e["sha_at"] + 20] = hashlib.sha1(out).digest()
        else:
            e = bytearray(src)
            e[8:12] = struct.pack(">I", len(out))
            e[12:32] = hashlib.sha1(out).digest()
            m += struct.pack(">I", len(name)) + name.encode() + e
            count += 1
        done += 1
    m[4:8] = struct.pack(">I", count)
    open("output/brg_patch.map", "wb").write(m)
    print("doubled", done, "skipped (newer revision)", skipped, "map entries", count)


if __name__ == "__main__":
    main()
