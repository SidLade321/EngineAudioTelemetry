"""Record game audio (WASAPI loopback) + raw UDP telemetry with a shared clock."""
import json, socket, struct, threading, time
import soundcard as sc
import soundfile as sf

OUT = r"C:\f1data"
SR = 48000
PORT = 20777

def udp_logger(stop, path):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(0.5)
    n = 0
    with open(path, "wb") as f:
        while not stop.is_set():
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            f.write(struct.pack("<dI", time.perf_counter(), len(data)))
            f.write(data)
            n += 1
    print(f"UDP packets logged: {n}")

def main():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stop = threading.Event()
    t = threading.Thread(target=udp_logger, args=(stop, rf"{OUT}\udp_{stamp}.bin"))
    t.start()

    speaker = sc.default_speaker()
    loop = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    chunk = SR // 10
    first_chunk_time = None
    print("Recording... drive your lap, then press Ctrl+C")
    try:
        with loop.recorder(samplerate=SR, channels=2) as rec, \
             sf.SoundFile(rf"{OUT}\audio_{stamp}.wav", "w", SR, 2) as wav:
            while True:
                data = rec.record(numframes=chunk)
                if first_chunk_time is None:
                    # approx start time of the first audio sample
                    first_chunk_time = time.perf_counter() - chunk / SR
                wav.write(data)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        t.join()
        with open(rf"{OUT}\meta_{stamp}.json", "w") as f:
            json.dump({"sample_rate": SR, "audio_start_perf": first_chunk_time}, f)
        print("Saved.")

if __name__ == "__main__":
    main()
