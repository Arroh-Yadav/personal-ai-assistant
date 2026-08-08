"""Simple CLI to test text-to-speech (edge-tts).

Usage: run from repo root: python -m scripts.test_tts

Synthesizes and plays a fixed test sentence to verify audio output.
"""

from __future__ import annotations

from assistant.audio.tts import speak


def main() -> None:
    test_text = "Hello, this is a test of the text to speech system."
    print(f'Speaking: "{test_text}"')
    speak(test_text)
    print("Done.")


if __name__ == "__main__":
    main()
