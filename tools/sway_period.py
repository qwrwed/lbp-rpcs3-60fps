"""Estimate the main period of motion in one region of a video.

Usage: sway_period.py <video> <x> <y> <w> <h>   (region in the video's pixels)
Reads the region's greyscale frames with ffmpeg, takes the mean absolute change of each
frame against the clip's mean frame, and prints the strongest periods (seconds) from
its autocorrelation, along with the frame rate and frame count.
"""
import subprocess
import sys

import numpy as np

path, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                       "stream=avg_frame_rate", "-of", "csv=p=0", path],
                      capture_output=True, text=True).stdout.strip()
num, den = map(int, rate.split("/"))
fps = num / den
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "crop=%d:%d:%d:%d,format=gray" % (w, h, x, y),
                      "-f", "rawvideo", "-"], capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
# Project each frame onto the first principal component of the region's change.
flat = frames.reshape(len(frames), -1)
flat = flat - flat.mean(0)
u, s, _ = np.linalg.svd(flat, full_matrices=False)
sig = u[:, 0] * s[0]
sig = sig - sig.mean()
ac = np.correlate(sig, sig, "full")[len(sig) - 1:]
ac /= ac[0]
peaks = [i for i in range(2, len(ac) - 1) if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.2]
print("fps %.2f frames %d" % (fps, len(frames)))
for i in peaks[:5]:
    print("period %.3f s (lag %d frames, r %.2f)" % (i / fps, i, ac[i]))
