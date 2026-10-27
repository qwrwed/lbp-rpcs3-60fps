"""Double the frame count of LittleBigPlanet animation resources (old layout, revision < 0x378).

The game plays character animations one frame per game tick, so at 60 ticks per second
they run twice as fast. Inserting an interpolated frame between every pair of frames
(rotations by normalised lerp, positions, scales and morphs linearly) restores their speed.

Usage: anim_resample.py <in.anim> <out.anim> [loop|clamp]
loop (default) also interpolates from the last frame back to the first, giving 2N frames;
clamp gives 2N-1 frames ending on the original last frame.
"""
import struct
import sys

import lbpmod


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def take(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v


def parse(data):
    r = Reader(data)
    nb = r.take(">I")[0]
    bones = r.take(">%dI" % (4 * nb))
    nframes, fps, morphs = r.take(">III")
    lists = []
    for _ in range(4):
        n = r.take(">I")[0]
        lists.append(list(r.take(">%dh" % n)))
    packed = []
    for comps in (4, 4, 4, 1):
        n = r.take(">I")[0]
        packed.append([r.take(">%df" % comps) for _ in range(n)])
    return dict(nb=nb, bones=bones, nframes=nframes, fps=fps, morphs=morphs, lists=lists,
                packed=packed, tail=data[r.p:])


def frames_of(base_count, animated, packed, nframes):
    """Per frame, the values of the animated entries (frame 0 from the base block)."""
    out = [[packed[i] for i in animated]]
    for f in range(1, nframes):
        o = base_count + len(animated) * (f - 1)
        out.append(packed[o:o + len(animated)])
    return out


def lerp(a, b, t, quat):
    if quat and sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-x for x in b)
    v = tuple(x + (y - x) * t for x, y in zip(a, b))
    if quat:
        n = sum(x * x for x in v) ** 0.5 or 1.0
        v = tuple(x / n for x in v)
    return v


def resample(a, loop):
    n = a["nframes"]
    m = 2 * n if loop else 2 * n - 1
    counts = [a["nb"], a["nb"], a["nb"], a["morphs"]]
    new_packed = []
    for k in range(4):
        animated, packed = a["lists"][k], a["packed"][k]
        fr = frames_of(counts[k], animated, packed, n)
        new = []
        for i in range(m):
            lo, t = divmod(i, 2)
            hi = (lo + 1) % n
            new.append([lerp(x, y, 0.5 * t, k == 0) for x, y in zip(fr[lo], fr[hi])] if t else fr[lo])
        base = list(packed[:counts[k]])
        body = [v for f in new[1:] for v in f]
        new_packed.append(base + body)
    out = dict(a, nframes=m, packed=new_packed)
    return out


def build(a):
    b = struct.pack(">I", a["nb"]) + struct.pack(">%dI" % len(a["bones"]), *a["bones"])
    b += struct.pack(">III", a["nframes"], a["fps"], a["morphs"])
    for lst in a["lists"]:
        b += struct.pack(">I", len(lst)) + struct.pack(">%dh" % len(lst), *lst)
    for vals in a["packed"]:
        b += struct.pack(">I", len(vals)) + b"".join(struct.pack(">%df" % len(v), *v) for v in vals)
    return b + a["tail"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    loop = (sys.argv[3] if len(sys.argv) > 3 else "loop") == "loop"
    res = open(src, "rb").read()
    magic, rev, unk, data, deps = lbpmod.unpack_binary(res)
    assert int.from_bytes(rev, "big") < 0x378
    a = parse(data)
    assert build(a) == data, "parse does not round-trip"
    out = lbpmod.pack_binary(magic, rev, unk, build(resample(a, loop)), deps)
    open(dst, "wb").write(out)
    print(src, "frames", a["nframes"], "->", 2 * a["nframes"] - (0 if loop else 1), "bytes", len(out))


if __name__ == "__main__":
    main()
