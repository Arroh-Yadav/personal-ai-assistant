"""Thin wrapper around the Google Gemini (google-generativeai) SDK.

Reads GEMINI_API_KEY from environment (use python-dotenv in development).
Provides a single helper `generate_response(messages)` where `messages` is
a list of dicts: [{'role': 'user'|'assistant'|'system', 'content': '...'}, ...]

If the google.generativeai SDK is not installed or the API call fails, the
wrapper falls back to a safe echo response so the app remains runnable.
"""
from typing import List, Dict, Optional
import os
import logging

try:
    # Optional: SDK may be installed as `google.generativeai`
    import google.generativeai as genai  # type: ignore
    _HAS_GENAI = True
except Exception:
    genai = None  # type: ignore
    _HAS_GENAI = False

# Load .env if present (no hard dependency on python-dotenv at import time)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

logger = logging.getLogger(__name__)


def generate_response(messages: List[Dict[str, str]], model: str = "gemini-1.0") -> str:
    """Generate an assistant response for the provided messages.

    messages: list of {'role': 'user'|'assistant'|'system', 'content': str}
    Returns assistant text.
    """
    # Simple safety: find the last user message for echo fallback
    last_user = None
    for m in reversed(messages):
        if m.get('role') == 'user':
            last_user = m.get('content')
            break

    # If the SDK is available and an API key exists, try to call Gemini.
    if _HAS_GENAI and GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Normalize messages for the SDK: author / content list of text blocks
            sdk_messages = []
            for m in messages:
                sdk_messages.append({
                    'author': m.get('role', 'user'),
                    'content': [{'type': 'text', 'text': m.get('content', '')}]
                })

            # This call may vary across SDK versions; wrap in try/except and
            # fall back to a safe echo if anything unexpected happens.
            resp = genai.chat.create(model=model, messages=sdk_messages)

            # Attempt to extract text from known response shapes.
            # Newer SDKs expose candidates; older ones may expose 'last'.
            text = None
            # Try common paths (guarded)
            if hasattr(resp, 'candidates') and resp.candidates:
                c = resp.candidates[0]
                # candidate may have content with text blocks
                if isinstance(c, dict):
                    # dict-based response
                    cont = c.get('content') or []
                    if cont and isinstance(cont, list) and isinstance(cont[0], dict):
                        text = ''.join(part.get('text', '') for part in cont if isinstance(part, dict))
                else:
                    # object-based candidate
                    try:
                        parts = getattr(c, 'content', None)
                        if parts:
                            text = ''.join(getattr(p, 'text', '') for p in parts)
                    except Exception:
                        text = None

            if not text and hasattr(resp, 'last'):
                try:
                    last = resp.last
                    # last may have 'content' list of dicts
                    content = getattr(last, 'content', None)
                    if content:
                        text = ''.join(getattr(p, 'text', '') for p in content)
                except Exception:
                    text = None

            if text:
                return text.strip()
            else:
                logger.warning('Unexpected response shape from google.generativeai; falling back to echo')
        except Exception as e:
            logger.exception('Gemini SDK call failed — falling back to echo: %s', e)

    # Fallback behavior (safe, deterministic): echo the user's last message with a prefix.
    if last_user:
        return f"(local-echo) I received: {last_user}"

    return "(local-echo) Hello — no user message provided."
