"""Install edited LittleBigPlanet resources as loose files that the game accepts.

The game checks each file against the SHA-1 in USRDIR/output/brg_patch.map. This script
reads the original resource from data.farc (by the SHA-1 in the original map), applies
edits, writes the result to USRDIR/<path>, and rewrites the map entry's size and SHA-1.

Usage (on the Deck, run from USRDIR):
  lbpmod.py <original map> <edits.json>
edits.json: {"<game path>": [edit, ...], ...} where an edit is one of
  {"text": [old, new]}                 replace bytes in a text resource (e.g. .cha)
  {"f32": [offset, value]}             set a big-endian float in the unpacked data of a
                                       compressed binary resource (e.g. .mat)
  {"f32mul": [offset, factor]}         multiply that float by factor instead
The map is written to output/brg_patch.map; data.farc is only read.
"""
import hashlib
import json
import os
import struct
import sys
import zlib


def read_map(path):
    b = open(path, "rb").read()
    rev, n = struct.unpack(">II", b[:8])
    p, ents = 8, {}
    for _ in range(n):
        ln = struct.unpack(">I", b[p:p + 4])[0]
        name = b[p + 4:p + 4 + ln].decode()
        q = p + 4 + ln
        ents[name] = {"size_at": q + 8, "sha_at": q + 12,
                      "size": struct.unpack(">I", b[q + 8:q + 12])[0], "sha": b[q + 12:q + 32]}
        p = q + 36
    return bytearray(b), ents


def farc_lookup(sha):
    size = os.path.getsize("data.farc")
    with open("data.farc", "rb") as f:
        f.seek(size - 8)
        n = struct.unpack(">I", f.read(4))[0]
        f.seek(size - 8 - n * 28)
        table = f.read(n * 28)
        for k in range(n):
            s, off, sz = struct.unpack(">20sII", table[k * 28:k * 28 + 28])
            if s == sha:
                f.seek(off)
                return f.read(sz)
    raise KeyError(sha.hex())


def unpack_binary(res):
    """Split a compressed resource (magic, revision, dep offset, flag, chunks) into parts."""
    magic, rev, dep_off = res[:4], res[4:8], struct.unpack(">I", res[8:12])[0]
    # Revisions from 0x271 carry a 4-byte branch descriptor after the dependency offset.
    branch = res[12:16] if int.from_bytes(rev, "big") >= 0x271 else b""
    q = 12 + len(branch)
    # Newer revisions have a compressed-flag byte (1) before the chunk table; older ones start
    # the table straight away with a 16-bit 1.
    flag = res[q] == 1
    p = q + 1 if flag else q
    assert flag or res[12:14] == b"\x00\x01", "unknown resource header"
    unk, count = struct.unpack(">HH", res[p:p + 4])
    sizes = [struct.unpack(">HH", res[p + 4 + 4 * i:p + 8 + 4 * i]) for i in range(count)]
    p, data = p + 4 + 4 * count, b""
    for csz, usz in sizes:
        chunk = zlib.decompress(res[p:p + csz])
        assert len(chunk) == usz
        data += chunk
        p += csz
    assert p == dep_off
    return magic, rev, (unk, flag, branch), data, res[dep_off:]


def pack_binary(magic, rev, unk_flag, data, deps):
    unk, flag, branch = unk_flag
    chunks = [zlib.compress(data[i:i + 0x8000], 9) for i in range(0, len(data), 0x8000)]
    head = struct.pack(">HH", unk, len(chunks))
    head += b"".join(struct.pack(">HH", len(c), min(0x8000, len(data) - 0x8000 * i))
                     for i, c in enumerate(chunks))
    body = b"".join(chunks)
    pre = branch + (b"\x01" if flag else b"")
    dep_off = 12 + len(pre) + len(head) + len(body)
    return magic + rev + struct.pack(">I", dep_off) + pre + head + body + deps


def main():
    orig_map, edits_path = sys.argv[1], sys.argv[2]
    _, orig = read_map(orig_map)
    new_map, ents = read_map("output/brg_patch.map")
    for path, edits in json.load(open(edits_path)).items():
        res = farc_lookup(orig[path]["sha"])
        assert hashlib.sha1(res).digest() == orig[path]["sha"]
        if any("f32" in e or "f32mul" in e for e in edits):
            magic, rev, unk, data, deps = unpack_binary(res)
            data = bytearray(data)
            for e in edits:
                if "f32" in e:
                    off, val = e["f32"]
                elif "f32mul" in e:
                    off, factor = e["f32mul"]
                    val = struct.unpack(">f", data[off:off + 4])[0] * factor
                else:
                    continue
                data[off:off + 4] = struct.pack(">f", val)
            res = pack_binary(magic, rev, unk, bytes(data), deps)
        for e in edits:
            if "text" in e:
                old, new = (s.encode() for s in e["text"])
                assert res.count(old) == 1, (path, old)
                res = res.replace(old, new)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(res)
        ent = ents[path]
        new_map[ent["size_at"]:ent["size_at"] + 4] = struct.pack(">I", len(res))
        new_map[ent["sha_at"]:ent["sha_at"] + 20] = hashlib.sha1(res).digest()
        print(path, len(res), hashlib.sha1(res).hexdigest())
    open("output/brg_patch.map", "wb").write(new_map)


if __name__ == "__main__":
    main()
