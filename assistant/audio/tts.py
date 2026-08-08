"""Text-to-speech module using edge-tts and playsound.

Synthesizes text to speech via Microsoft's edge-tts service (free, no API key)
and plays it back using playsound.

Provides:
  speak(text: str, voice: Optional[str] = None) -> None
    - Synthesizes text to an MP3 temp file.
    - Plays the file immediately.
    - Cleans up the temp file afterward.
    - Failures log and return gracefully (no exceptions raised).
"""

import asyncio
import logging
import os
import tempfile
from typing import Optional

try:
    import edge_tts
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("edge-tts is required for text-to-speech") from exc

try:
    import playsound
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("playsound is required for audio playback") from exc

from assistant import config

logger = logging.getLogger(__name__)


def speak(text: str, voice: Optional[str] = None) -> None:
    """Synthesize and play text-to-speech.

    Args:
        text: Text to synthesize (can be multiline).
        voice: TTS voice name (e.g. "en-US-AriaNeural"). If None, uses
               assistant.config.TTS_VOICE.

    Returns:
        None. Failures are logged but do not raise exceptions.
    """
    # Skip if text is empty or whitespace-only
    if not text or not text.strip():
        return

    if voice is None:
        voice = getattr(config, "TTS_VOICE", "en-US-AriaNeural")

    temp_file = None
    try:
        # Create a temp MP3 file. Use delete=False because Windows locks open
        # file handles, preventing edge-tts from writing to the file.
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file = f.name
        # f is closed here; temp file is now writable by edge-tts

        # Synthesize audio asynchronously and save to the temp file
        logger.info(f"Synthesizing speech ({voice}): {text[:50]}...")
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(temp_file))

        # Play the audio
        logger.info(f"Playing audio from {temp_file}")
        playsound.playsound(temp_file)

    except Exception as e:
        logger.error(f"Error during TTS synthesis or playback: {e}", exc_info=True)

    finally:
        # Clean up the temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.debug(f"Deleted temp file {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
