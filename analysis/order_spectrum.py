"""Order analysis: average the spectrum in engine-order space to find which harmonics the engine makes."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import spectrogram, find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN = sys.argv[1]
raw, out = Path("data/raw"), Path("data/processed")

audio, sr = sf.read(raw / f"audio_{RUN}.wav")
x = audio.mean(axis=1)
f, t, S = spectrogram(x, fs=sr, nperseg=8192, noverlap=6144, window="hann")

tel = pd.read_csv(out / f"telemetry_{RUN}.csv")
rpm = np.interp(t, tel.t_audio, tel.rpm, left=np.nan, right=np.nan)
thr = np.interp(t, tel.t_audio, tel.throttle, left=np.nan, right=np.nan)
keep = (thr > 0.95) & ~np.isnan(rpm)                 # full-throttle frames only
print(f"Using {keep.sum()} of {len(t)} frames (full throttle)")

orders = np.arange(0.25, 12, 0.02)
O = np.array([np.interp(orders * r / 60, f, S[:, i])  # resample each frame onto the order axis
              for i, r in zip(np.where(keep)[0], rpm[keep])])
spec = 10 * np.log10(O.mean(axis=0) + 1e-12)

peaks, _ = find_peaks(spec, prominence=3)
top = peaks[np.argsort(spec[peaks])[::-1][:12]]
print("Strongest engine orders:")
for p in sorted(top):
    print(f"  order {orders[p]:5.2f}   {spec[p]:6.1f} dB")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(orders, spec)
ax.plot(orders[top], spec[top], "rx")
for p in top:
    ax.annotate(f"{orders[p]:.2f}", (orders[p], spec[p]), textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=8)
ax.set_xlabel("Engine order (cycles per crank revolution)")
ax.set_ylabel("Mean power (dB)")
ax.set_title("Order spectrum, full-throttle frames")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out / f"order_spectrum_{RUN}.png", dpi=120)
print("Saved order spectrum")
