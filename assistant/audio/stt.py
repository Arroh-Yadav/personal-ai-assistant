"""Speech-to-text module using faster-whisper.

Consumes (audio_array, samplerate) tuples from assistant.audio.capture
and returns transcribed text.

Provides:
  transcribe(audio: np.ndarray, samplerate: int) -> str
    - Lazily loads a WhisperModel singleton (CPU + int8 by default).
    - Passes audio directly (no temp files or ffmpeg).
    - Returns transcribed text or empty string on failure.
"""

import logging
from typing import Optional

import numpy as np

try:
    from faster_whisper import WhisperModel
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("faster-whisper is required for speech-to-text") from exc

from assistant import config

logger = logging.getLogger(__name__)

# Module-level singleton for the WhisperModel (loaded lazily).
_model: Optional[WhisperModel] = None


def _get_model() -> WhisperModel:
    """Lazily load and return the global WhisperModel singleton."""
    global _model
    if _model is None:
        model_size = getattr(config, "STT_MODEL_SIZE", "small")
        logger.info(f"Loading WhisperModel (size={model_size}, device=cpu, compute_type=int8)")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio: np.ndarray, samplerate: int) -> str:
    """Transcribe audio to text using faster-whisper.

    Args:
        audio: 1-D numpy array of audio samples (typically float32, 16kHz mono
               from assistant.audio.capture.record_push_to_talk).
        samplerate: Sample rate in Hz (typically 16000).

    Returns:
        Transcribed text as a string, or empty string if no speech is detected
        or an error occurs.
    """
    if audio is None or len(audio) == 0:
        return ""

    try:
        model = _get_model()
        # Convert to the format expected by faster-whisper: mono float32 in [-1, 1].
        # If audio is already 16kHz mono float32 from capture.py, pass directly.
        audio_input = np.asarray(audio, dtype=np.float32)

        # Transcribe; returns (text, language_prob, segments_list).
        # We're interested in the segments to rebuild the full text with proper handling.
        segments, info = model.transcribe(audio_input, language="en")

        # Collect text from all segments
        texts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                texts.append(text)

        result = " ".join(texts).strip()
        return result

    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        return ""
