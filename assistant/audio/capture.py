"""Push-to-talk audio capture utility.

Provides record_push_to_talk(key=None) -> Optional[Tuple[np.ndarray, int]]
that records audio while a configured push-to-talk key is held.

Behavior:
- Poll keyboard.is_pressed(key) to detect press/release (no VAD).
- While held, record via sounddevice.InputStream at 16kHz mono float32
  into a callback-appended list.
- On release, concatenate frames and return (audio_array, samplerate).
- Return None if nothing was recorded.

The default key is read from assistant.config.PUSH_TO_TALK_KEY when
`key` is None.
"""
from typing import Optional, Tuple
import time

import numpy as np

try:
    import sounddevice as sd
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("sounddevice is required for audio capture") from exc

try:
    import keyboard
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("keyboard is required for push-to-talk key detection") from exc

from assistant import config


def record_push_to_talk(key: str | None = None) -> Optional[Tuple[np.ndarray, int]]:
    """Record from the default input device while `key` is held.

    Args:
        key: Keyboard key name understood by keyboard.is_pressed (e.g. 'space').
             If None, uses assistant.config.PUSH_TO_TALK_KEY.

    Returns:
        (audio_array, samplerate) where audio_array is a 1-D numpy.float32 array
        of samples at 16000 Hz, or None if no audio was recorded.
    """
    if key is None:
        key = getattr(config, "PUSH_TO_TALK_KEY", None)

    if not key:
        raise ValueError(
            "Push-to-talk key is not set. Provide `key` or set assistant.config.PUSH_TO_TALK_KEY"
        )

    samplerate = 16000
    channels = 1
    frames: list[np.ndarray] = []

    def _callback(indata, frames_count, time_info, status):
        # indata shape: (frames_count, channels)
        # copy to avoid referencing recycled buffers
        frames.append(indata.copy())

    # Wait for key press
    try:
        while not keyboard.is_pressed(key):
            time.sleep(0.01)
    except Exception as exc:  # keyboard may raise on some platforms
        raise RuntimeError(f"Error while waiting for push-to-talk key press: {exc}")

    # Start recording while key is held
    stream = None
    try:
        stream = sd.InputStream(samplerate=samplerate, channels=channels, dtype="float32", callback=_callback)
        stream.start()
        # Record until key release
        while keyboard.is_pressed(key):
            time.sleep(0.01)
        stream.stop()
        stream.close()
    except Exception:
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
        raise

    if not frames:
        return None

    # Concatenate per-callback arrays into a single 1-D array
    audio = np.concatenate([f.reshape(-1) for f in frames]).astype(np.float32)
    return audio, samplerate
