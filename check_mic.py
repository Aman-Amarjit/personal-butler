"""
Microphone diagnostic tool.
Run this to check your mic is working and see live dB levels.

Usage:
    python check_mic.py
"""
import sys
import time
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("ERROR: sounddevice not installed. Run: pip install sounddevice")
    sys.exit(1)

SAMPLE_RATE = 16000
DURATION    = 10  # seconds to monitor


def rms_db(audio):
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    if rms < 1e-10:
        return -100.0
    return 20.0 * np.log10(rms)


def main():
    print("=" * 50)
    print("  PANDA Microphone Diagnostic")
    print("=" * 50)
    print()

    # List devices
    devices = sd.query_devices()
    print("Available input devices:")
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            marker = " <-- DEFAULT" if i == sd.default.device[0] else ""
            print(f"  [{i:2d}] {d['name']}{marker}")
    print()

    default_dev = sd.query_devices(kind="input")
    print(f"Using: {default_dev['name']}")
    print()
    print(f"Monitoring for {DURATION}s — speak into your mic...")
    print(f"  Silence threshold : -20 dB  (below = silent)")
    print(f"  Wake trigger      : -25 dB  (above = PANDA checks for wake word)")
    print()

    peak_db = -100.0
    start = time.monotonic()

    def callback(indata, frames, time_info, status):
        nonlocal peak_db
        db = rms_db(indata)
        peak_db = max(peak_db, db)
        bar_len = max(0, int(db + 60))  # shift so -60 dB = 0 chars
        bar = "█" * min(bar_len, 50)
        label = "SPEECH" if db >= -20 else ("QUIET " if db >= -35 else "SILENT")
        print(f"\r  {db:6.1f} dB  [{bar:<50}]  {label}   ", end="", flush=True)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=1024, callback=callback):
        time.sleep(DURATION)

    print()
    print()
    print(f"Peak level: {peak_db:.1f} dB")
    if peak_db < -35:
        print("⚠  Mic level very low — check mic permissions or volume in Windows settings")
    elif peak_db < -20:
        print("⚠  Mic level low — speak louder or move closer to the mic")
    else:
        print("✓  Mic level looks good — PANDA should be able to hear you")
    print()


if __name__ == "__main__":
    main()
