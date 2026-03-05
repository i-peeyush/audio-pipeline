"""
Device Simulation Script
─────────────────────────
Simulates multiple wearable devices uploading audio files to the API.
Usage:
    python simulate_device.py
"""

import os
import struct
import wave
import time
import random
import httpx

BASE_URL = "http://localhost:8000"

DEVICES = ["device_101", "device_102", "device_203"]

COMMANDS = [
    "open camera",
    "read this text",
    "take a photo",
    "send message",
    "play music",
    "stop recording",
    "increase volume",
    "show notifications",
    "start navigation",
    "call mom",
]


def generate_dummy_wav(path: str, duration_ms: int = 500) -> None:
    """Generate a minimal valid WAV file with silence."""
    sample_rate  = 16000
    num_channels = 1
    bit_depth    = 16
    num_samples  = int(sample_rate * duration_ms / 1000)

    with wave.open(path, "w") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(bit_depth // 8)
        wf.setframerate(sample_rate)
        # White noise at very low amplitude
        frames = struct.pack(f"<{num_samples}h", *[random.randint(-100, 100) for _ in range(num_samples)])
        wf.writeframes(frames)


def upload_audio(device_id: str, transcription: str, wav_path: str) -> dict:
    with open(wav_path, "rb") as f:
        resp = httpx.post(
            f"{BASE_URL}/api/audio/upload",
            data={"device_id": device_id, "transcription": transcription},
            files={"audio_file": (os.path.basename(wav_path), f, "audio/wav")},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    tmp_dir = "./tmp_sim"
    os.makedirs(tmp_dir, exist_ok=True)

    print("=" * 55)
    print("  AI Wearable Device Simulator")
    print("=" * 55)

    for i in range(1, 11):           # Simulate 10 uploads
        device_id     = random.choice(DEVICES)
        transcription = random.choice(COMMANDS)
        wav_path      = os.path.join(tmp_dir, f"sim_{i}.wav")

        generate_dummy_wav(wav_path, duration_ms=random.randint(300, 800))

        try:
            result = upload_audio(device_id, transcription, wav_path)
            print(f"[{i:02d}] ✅  {device_id} | '{transcription}' | audio_id={result['audio_id']}")
        except Exception as e:
            print(f"[{i:02d}] ❌  {device_id} | ERROR: {e}")

        time.sleep(0.3)

    print("=" * 55)
    print("Simulation complete. Check GET /api/dataset/download")

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()