"""Simple CLI to test speech-to-text (faster-whisper).

Usage: run from repo root: python -m scripts.test_stt

Records audio via push-to-talk and transcribes it to text, printing the result.
"""

from __future__ import annotations

from assistant.audio.capture import record_push_to_talk
from assistant.audio.stt import transcribe


def main() -> None:
    print("Recording audio (push-to-talk)...")
    result = record_push_to_talk()
    if result is None:
        print("No audio recorded.")
        return

    audio, sr = result
    print(f"Recorded {len(audio) / sr:.2f}s of audio at {sr}Hz")

    print("Transcribing...")
    text = transcribe(audio, sr)

    if text:
        print(f"Transcribed text: {text}")
    else:
        print("No speech detected or transcription failed.")


if __name__ == "__main__":
    main()
