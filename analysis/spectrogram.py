"""Spectrogram of the lap audio with engine-order lines from telemetry overlaid."""
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
x = audio.mean(axis=1)                                   # stereo -> mono
f, t, S = spectrogram(x, fs=sr, nperseg=4096, noverlap=3072, window="hann")
S_db = 10 * np.log10(S + 1e-12)

tel = pd.read_csv(out / f"telemetry_{RUN}.csv")
orders = {1.5: "tab:green", 3: "tab:red", 6: "tab:orange"}
fm = f <= 2500

fig, axes = plt.subplots(2, 1, figsize=(14, 9))
for ax, (t0, t1) in zip(axes, [(0, t[-1]), (10, 22)]):   # full lap, then a zoom
    m = (t >= t0) & (t <= t1)
    ax.pcolormesh(t[m], f[fm], S_db[np.ix_(fm, m)], shading="auto", cmap="magma",
                  vmin=np.percentile(S_db[fm], 30), vmax=S_db[fm].max())
    tm = tel[(tel.t_audio >= t0) & (tel.t_audio <= t1)]
    for k, c in orders.items():
        ax.plot(tm.t_audio, k * tm.rpm / 60, c, lw=1, ls="--", alpha=0.8, label=f"order {k}")
    ax.set_xlim(t0, t1); ax.set_ylim(0, 2500)
    ax.set_ylabel("Frequency (Hz)")
axes[0].legend(loc="upper right")
axes[1].set_xlabel("Time from audio start (s)")
fig.tight_layout()
fig.savefig(out / f"spectrogram_{RUN}.png", dpi=120)
print("Saved spectrogram")
