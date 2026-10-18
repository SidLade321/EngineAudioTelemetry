"""Decode the player's Car Telemetry packets (id 6) into a CSV and a quick plot."""
import json, struct, sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN = sys.argv[1]
raw, out = Path("data/raw"), Path("data/processed")
out.mkdir(parents=True, exist_ok=True)

REC = struct.Struct("<dI")
HEADER = struct.Struct("<HBBBBBQfIIBB")
CAR = struct.Struct("<HfffBbH")      # speed, throttle, steer, brake, clutch, gear, rpm
NUM_CARS, CAR_SIZE = 24, 59          # inferred: 29 + 24*59 + 3 = 1448 bytes

meta = json.load(open(raw / f"meta_{RUN}.json"))
rows = []
with open(raw / f"udp_{RUN}.bin", "rb") as f:
    while (head := f.read(REC.size)) and len(head) == REC.size:
        t, n = REC.unpack(head)
        d = f.read(n)
        h = HEADER.unpack_from(d)
        if h[5] != 6:                 # only Car Telemetry packets
            continue
        player = h[10]
        speed, thr, steer, brake, clutch, gear, rpm = CAR.unpack_from(
            d, HEADER.size + player * CAR_SIZE)
        rows.append(dict(t_audio=t - meta["audio_start_perf"], session_time=h[7],
                         speed_kph=speed, throttle=thr, brake=brake, gear=gear, rpm=rpm))

df = pd.DataFrame(rows)
df.to_csv(out / f"telemetry_{RUN}.csv", index=False)
print(df.describe().round(1).to_string())

fig, ax = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
ax[0].plot(df.t_audio, df.rpm); ax[0].set_ylabel("RPM")
ax[1].step(df.t_audio, df.gear, where="post"); ax[1].set_ylabel("Gear")
ax[2].plot(df.t_audio, df.speed_kph); ax[2].set_ylabel("Speed (km/h)")
ax[2].set_xlabel("Time from audio start (s)")
fig.tight_layout()
fig.savefig(out / f"telemetry_{RUN}.png", dpi=120)
print("Saved CSV and plot to data/processed/")
