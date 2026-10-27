"""Find the footstep rhythm in a mono WAV: onset envelope of the 2-8 kHz band, its periods and onset times.

Usage: step_audio.py <wav> [<start s> <end s>]
"""
import sys
import wave

import numpy as np

w = wave.open(sys.argv[1])
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), {2: "<i2", 4: "<i4"}[w.getsampwidth()]).astype(float)
if len(sys.argv) > 3:
    x = x[int(float(sys.argv[2]) * sr):int(float(sys.argv[3]) * sr)]
X = np.fft.rfft(x)
f = np.fft.rfftfreq(len(x), 1 / sr)
X[(f < 2000) | (f > 8000)] = 0
y = np.fft.irfft(X, len(x))
hop = sr // 200
env = np.sqrt(np.add.reduceat(y ** 2, np.arange(0, len(y), hop)))
on = np.maximum(np.diff(env), 0)
on -= on.mean()
ac = np.correlate(on, on, "full")[len(on) - 1:]
ac /= ac[0]
peaks = [i for i in range(10, min(len(ac) - 1, 200)) if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.1]
print("rms %.0f  periods:" % y.std(), ", ".join("%.3f s (r %.2f)" % (i / 200, ac[i]) for i in peaks[:5]) or "none")
thr = on.mean() + 3 * on.std()
times = [i / 200 for i in range(1, len(on) - 1) if on[i] > thr and on[i] >= on[i - 1] and on[i] >= on[i + 1]]
print("onsets:", " ".join("%.2f" % t for t in times))
