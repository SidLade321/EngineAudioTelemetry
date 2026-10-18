"""RPM from audio with a continuity constraint (Viterbi), compared with the frame-by-frame tracker."""
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
LAMBDA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.001   # penalty per RPM jumped between frames
LAG, PITCH = 0.125, 1.024
ORDERS = {1.5: 1.0, 2.0: 1.0, 3.0: 0.7, 4.5: 1.5, 6.0: 0.5}

raw, out = Path("data/raw"), Path("data/processed")
audio, sr = sf.read(raw / f"audio_{RUN}.wav")
f, t, S = spectrogram(audio.mean(axis=1), fs=sr, nperseg=4096, noverlap=3072, window="hann")
L = np.log10(S + 1e-12)
L -= np.median(L, axis=0)
df_hz = f[1] - f[0]

cand = np.arange(5000, 13500, 20)     # 20 RPM steps keeps Viterbi fast
score = np.zeros((len(cand), len(t)))
for k, w in ORDERS.items():
    fi = k * PITCH * cand / 60 / df_hz
    i0 = np.clip(np.floor(fi).astype(int), 0, len(f) - 2)
    frac = (fi - i0)[:, None]
    score += w * (L[i0] * (1 - frac) + L[i0 + 1] * frac)

# 1) frame-by-frame (previous method)
rpm_raw = medfilt(cand[score.argmax(axis=0)].astype(float), 5)

# 2) Viterbi: best whole path = high harmonic score minus jump penalties
P = LAMBDA * np.abs(cand[:, None] - cand[None, :])
cols = np.arange(len(cand))
D = score[:, 0].copy()
back = np.zeros(score.shape, dtype=np.int32)
for i in range(1, len(t)):
    M = D[:, None] - P                 # M[j, k] = arrive at candidate k from candidate j
    idx = M.argmax(axis=0)
    back[:, i] = idx
    D = M[idx, cols] + score[:, i]
path = np.zeros(len(t), dtype=int)
path[-1] = D.argmax()
for i in range(len(t) - 1, 0, -1):
    path[i - 1] = back[path[i], i]
rpm_vit = cand[path].astype(float)

# --- score both against telemetry ---
tel = pd.read_csv(out / f"telemetry_{RUN}.csv")
true = np.interp(t, tel.t_audio + LAG, tel.rpm, left=np.nan, right=np.nan)
thr = np.interp(t, tel.t_audio + LAG, tel.throttle, left=np.nan, right=np.nan)
valid = ~np.isnan(true)
print(f"LAMBDA = {LAMBDA}")
for label, est in [("Frame-by-frame", rpm_raw), ("Viterbi", rpm_vit)]:
    err = est - true
    pct = np.abs(err) / true * 100
    for name, m in [("All", valid), ("Full throttle", valid & (thr > 0.95)),
                    ("Part/off throttle", valid & (thr <= 0.95))]:
        print(f"{label:15s} {name:18s} median |err| {np.median(np.abs(err[m])):5.0f} RPM | "
              f"within 2%: {np.mean(pct[m] < 2) * 100:5.1f}%")

pd.DataFrame({"t_audio": t, "rpm_raw": rpm_raw, "rpm_viterbi": rpm_vit, "rpm_true": true}).to_csv(
    out / f"rpm_viterbi_{RUN}.csv", index=False)

fig, ax = plt.subplots(2, 1, figsize=(14, 8))
for a, (t0, t1) in zip(ax, [(0, t[-1]), (10, 22)]):
    m = (t >= t0) & (t <= t1)
    a.plot(t[m], true[m], label="Telemetry (truth)", lw=2)
    a.plot(t[m], rpm_raw[m], label="Frame-by-frame", lw=0.8, alpha=0.5)
    a.plot(t[m], rpm_vit[m], label="Viterbi", lw=1.2)
    a.set_xlim(t0, t1); a.set_ylabel("RPM"); a.grid(alpha=0.3)
ax[0].legend(); ax[1].set_xlabel("Time from audio start (s)")
fig.tight_layout()
fig.savefig(out / f"rpm_viterbi_{RUN}_lam{LAMBDA}.png", dpi=120)
print("Saved Viterbi comparison")
