"""Time the pulses of one region of a video: frames where its bright area peaks.

Usage: pulse_times.py <video> <x> <y> <w> <h>
Counts pixels brighter than the region's 80th percentile in each frame, smooths over 3 frames,
and prints the times of local maxima that stand out by more than a sixth of the signal's
range, plus the intervals between them in seconds.
"""
import subprocess
import sys

import numpy as np

path, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "crop=%d:%d:%d:%d,format=gray" % (w, h, x, y),
                      "-f", "rawvideo", "-"], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
thr = np.percentile(f, 80)
s = (f > thr).sum((1, 2)).astype(float)
s = np.convolve(s, np.ones(3) / 3, "same")
rng = s.max() - s.min()
peaks = [i for i in range(4, len(s) - 4) if s[i] == s[i - 4:i + 5].max() and s[i] - s[i - 4:i + 5].min() > rng / 6]
t = np.array(peaks) / 60.0
print("peaks:", " ".join("%.2f" % v for v in t))
print("intervals:", " ".join("%.2f" % v for v in np.diff(t)))
