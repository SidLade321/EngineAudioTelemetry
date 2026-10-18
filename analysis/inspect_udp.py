"""Inspect a raw UDP capture: check the header, count packet types, compare with audio."""
import json, struct, sys
from collections import Counter, defaultdict
from pathlib import Path
import soundfile as sf

RUN = sys.argv[1]                         # e.g. 20261018_124846
raw = Path("data/raw")

REC = struct.Struct("<dI")                # our own record: timestamp, packet length
HEADER = struct.Struct("<HBBBBBQfIIBB")   # game header (F1 24/25 layout, check vs F1 26 spec)

packets = []
with open(raw / f"udp_{RUN}.bin", "rb") as f:
    while True:
        head = f.read(REC.size)
        if len(head) < REC.size:
            break
        t, n = REC.unpack(head)
        packets.append((t, f.read(n)))

print(f"Packets: {len(packets)}")
fmt, year, major, minor, pver, pid, *_ = HEADER.unpack_from(packets[0][1])
print(f"packetFormat={fmt}  gameYear={year}  version={major}.{minor}")

counts, sizes = Counter(), defaultdict(set)
for t, d in packets:
    pid = HEADER.unpack_from(d)[5]
    counts[pid] += 1
    sizes[pid].add(len(d))
for pid in sorted(counts):
    print(f"  id {pid:2d}: {counts[pid]:6d} packets, sizes {sorted(sizes[pid])}")

meta = json.load(open(raw / f"meta_{RUN}.json"))
info = sf.info(raw / f"audio_{RUN}.wav")
print(f"UDP time span: {packets[-1][0] - packets[0][0]:.1f} s")
print(f"Audio length:  {info.duration:.1f} s")
print(f"Audio started {packets[0][0] - meta['audio_start_perf']:.2f} s before first packet")
