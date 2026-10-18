"""Scan audio/telemetry time offsets to explain the ~2% order shift."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import spectrogram
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN = sys.argv[1]
raw, out = Path("data/raw"), Path("data/processed")

audio, sr = sf.read(raw / f"audio_{RUN}.wav")
f, t, S = spectrogram(audio.mean(axis=1), fs=sr, nperseg=8192, noverlap=6144, window="hann")
tel = pd.read_csv(out / f"telemetry_{RUN}.csv")

orders = np.arange(4.2, 4.9, 0.005)        # zoom in around the order-4.5 peak
lags = np.arange(-0.5, 0.51, 0.025)        # +lag = audio arrives later than telemetry
pos, height = [], []
for lag in lags:
    rpm = np.interp(t, tel.t_audio + lag, tel.rpm, left=np.nan, right=np.nan)
    thr = np.interp(t, tel.t_audio + lag, tel.throttle, left=np.nan, right=np.nan)
    keep = np.where((thr > 0.95) & ~np.isnan(rpm))[0]
    O = np.array([np.interp(orders * rpm[i] / 60, f, S[:, i]) for i in keep])
    spec = 10 * np.log10(O.mean(axis=0) + 1e-12)
    pos.append(orders[spec.argmax()])
    height.append(spec.max())

best = int(np.argmax(height))
zero = int(np.argmin(np.abs(lags)))
print(f"At lag 0:      peak at order {pos[zero]:.3f}, {height[zero]:.1f} dB")
print(f"Sharpest peak: lag {lags[best]:+.3f} s -> order {pos[best]:.3f}, {height[best]:.1f} dB")

fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
ax[0].plot(lags, pos, "o-"); ax[0].axhline(4.5, color="r", ls="--")
ax[0].set_ylabel("Peak order")
ax[1].plot(lags, height, "o-"); ax[1].set_ylabel("Peak height (dB)")
ax[1].set_xlabel("Time shift applied to telemetry (s)")
for a in ax:
    a.axvline(lags[best], color="g", ls=":")
    a.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out / f"lag_scan_{RUN}.png", dpi=120)
print("Saved lag scan")
