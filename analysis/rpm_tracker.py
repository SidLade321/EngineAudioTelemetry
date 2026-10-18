"""Estimate RPM from audio alone (harmonic-sum tracker) and score it against telemetry."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import spectrogram, medfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN = sys.argv[1]
LAG = 0.125        # audio arrives this long after telemetry (from lag_scan.py)
PITCH = 1.024      # game pitches engine audio this much above reported RPM
ORDERS = {1.5: 1.0, 2.0: 1.0, 3.0: 0.7, 4.5: 1.5, 6.0: 0.5}   # harmonic: weight

raw, out = Path("data/raw"), Path("data/processed")
audio, sr = sf.read(raw / f"audio_{RUN}.wav")
f, t, S = spectrogram(audio.mean(axis=1), fs=sr, nperseg=4096, noverlap=3072, window="hann")
L = np.log10(S + 1e-12)
L -= np.median(L, axis=0)              # per-frame normalisation (ignore overall loudness)
df_hz = f[1] - f[0]

cand = np.arange(5000, 13500, 10)      # candidate RPMs
score = np.zeros((len(cand), len(t)))
for k, w in ORDERS.items():
    fi = k * PITCH * cand / 60 / df_hz            # fractional bin index of each harmonic
    i0 = np.clip(np.floor(fi).astype(int), 0, len(f) - 2)
    frac = (fi - i0)[:, None]
    score += w * (L[i0] * (1 - frac) + L[i0 + 1] * frac)   # linear interpolation between bins
rpm_est = medfilt(cand[score.argmax(axis=0)].astype(float), 5)

# --- score against telemetry ---
tel = pd.read_csv(out / f"telemetry_{RUN}.csv")
true = np.interp(t, tel.t_audio + LAG, tel.rpm, left=np.nan, right=np.nan)
thr = np.interp(t, tel.t_audio + LAG, tel.throttle, left=np.nan, right=np.nan)
valid = ~np.isnan(true)
err = rpm_est - true
pct = np.abs(err) / true * 100
for name, m in [("All", valid),
                ("Full throttle", valid & (thr > 0.95)),
                ("Part/off throttle", valid & (thr <= 0.95))]:
    print(f"{name:18s} median |error| {np.median(np.abs(err[m])):5.0f} RPM | "
          f"within 2%: {np.mean(pct[m] < 2) * 100:5.1f}% | frames: {m.sum()}")

pd.DataFrame({"t_audio": t, "rpm_est": rpm_est, "rpm_true": true}).to_csv(
    out / f"rpm_estimate_{RUN}.csv", index=False)

fig, ax = plt.subplots(2, 1, figsize=(14, 8))
for a, (t0, t1) in zip(ax, [(0, t[-1]), (10, 22)]):
    m = (t >= t0) & (t <= t1)
    a.plot(t[m], true[m], label="Telemetry (truth)", lw=2)
    a.plot(t[m], rpm_est[m], label="Estimated from audio", lw=1)
    a.set_xlim(t0, t1); a.set_ylabel("RPM"); a.grid(alpha=0.3)
ax[0].legend(); ax[1].set_xlabel("Time from audio start (s)")
fig.tight_layout()
fig.savefig(out / f"rpm_estimate_{RUN}.png", dpi=120)
print("Saved RPM estimate")
