"""Count how many frames of a video differ from the frame before, as a rate per second.

Usage: unique_frames.py <video> [<threshold>]
Compares greyscale 320-wide copies; a frame counts as new when its mean absolute difference
from the previous frame exceeds the threshold (default 0.3 of 255).
"""
import subprocess
import sys

import numpy as np

path = sys.argv[1]
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                       "stream=avg_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
num, den = map(int, rate.split("/"))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=320:180,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
d = np.abs(np.diff(f, axis=0)).mean((1, 2))
secs = len(f) / (num / den)
print("frames %d over %.1f s, new frames %d (%.1f per s), median change %.2f" % (len(f), secs, (d > thr).sum(), (d > thr).sum() / secs, np.median(d)))
