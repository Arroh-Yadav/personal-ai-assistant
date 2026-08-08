"""Simple CLI to test push-to-talk audio capture.

Usage: run from repo root: python -m scripts.test_capture

Records while the configured push-to-talk key is held and writes a WAV file
into the system temp directory (tempfile.gettempdir()). Prints the file path
and duration when done.
"""

from __future__ import annotations

import os
import time
import tempfile
import wave

import numpy as np

from assistant import config
from assistant.audio.capture import record_push_to_talk


def main() -> None:
    key = getattr(config, "PUSH_TO_TALK_KEY", None)
    print(f"Press and hold the push-to-talk key: {key}")
    res = record_push_to_talk()
    if res is None:
        print("No audio recorded.")
        return
    audio, sr = res
    audio = np.asarray(audio, dtype=np.float32)

    # Convert float32 [-1.0,1.0] to int16 PCM for WAV
    int16 = (audio * 32767.0).clip(-32768, 32767).astype('<i2')

    out_dir = tempfile.gettempdir()
    fname = os.path.join(out_dir, f"capture_{int(time.time())}.wav")

    with wave.open(fname, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())

    duration = len(audio) / float(sr)
    print(f"Wrote: {fname} ({duration:.2f}s)")


if __name__ == "__main__":
    main()
