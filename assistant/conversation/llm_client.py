"""LLM wrapper using google-genai's Client.models.list() to select a model
and then client.chats.create() + chat.send_message() to get a reply.

Behavior:
- If GEMINI_MODEL env var is set, use that model string directly.
- Otherwise, call client.models.list(), filter for models with 'gemini' and
  'flash' in their name (case-insensitive), and use the first match.
- If none matches, fall back to the first model containing 'gemini'.
- Print (and log) the selected model so the user can confirm.

The chat uses history by concatenating prior turns into a single prompt
that is sent as one message to chat.send_message().
"""
from typing import List, Dict, Optional
import os
import logging

try:
    from google import genai  # type: ignore
    _HAS_GENAI = True
except Exception:
    genai = None  # type: ignore
    _HAS_GENAI = False

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL_OVERRIDE = os.environ.get('GEMINI_MODEL')
DEFAULT_MODEL = 'gemini-flash-latest'
logger = logging.getLogger(__name__)


def _build_prompt_from_messages(messages: List[Dict[str, str]]) -> str:
    parts = []
    for m in messages:
        role = m.get('role')
        content = m.get('content', '')
        if role == 'system':
            parts.append(f"[System]\n{content}\n")
    parts.append('[Conversation history]')
    for m in messages:
        role = m.get('role')
        content = m.get('content', '')
        if role == 'user':
            parts.append(f"User: {content}")
        elif role == 'assistant':
            parts.append(f"Assistant: {content}")
    parts.append('\nAssistant, please reply concisely to the latest user message above.')
    return '\n'.join(parts)


def _select_model(client, prefer_flash=True) -> Optional[str]:
    # If override provided, use it
    if GEMINI_MODEL_OVERRIDE:
        logger.info('Using GEMINI_MODEL override: %s', GEMINI_MODEL_OVERRIDE)
        print(f"Selected model (override): {GEMINI_MODEL_OVERRIDE}")
        return GEMINI_MODEL_OVERRIDE

    try:
        models = client.models.list()
    except Exception as e:
        logger.exception('Failed to list models: %s', e)
        return None

    candidate = None
    gemini_candidates = []
    # Iterate through models and find matching names
    for m in models:
        # model objects may be dict-like or have 'name' attribute
        name = None
        if isinstance(m, dict):
            name = m.get('name') or m.get('id')
        else:
            name = getattr(m, 'name', None) or getattr(m, 'id', None)
        if not name:
            # fallback to string representation
            try:
                name = str(m)
            except Exception:
                continue
        lname = name.lower()
        if 'gemini' in lname:
            gemini_candidates.append(name)

    # Prefer flash-tier
    for g in gemini_candidates:
        if 'flash' in g.lower():
            candidate = g
            break
    if not candidate and gemini_candidates:
        candidate = gemini_candidates[0]

    if candidate:
        logger.info('Selected model: %s', candidate)
        print(f"Selected model: {candidate}")
    else:
        logger.warning('No Gemini model found from list() — using provided model string fallback')
    return candidate


def generate_response(messages: List[Dict[str, str]]) -> str:
    last_user = None
    for m in reversed(messages):
        if m.get('role') == 'user':
            last_user = m.get('content')
            break

    if _HAS_GENAI and GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            selected = _select_model(client)
            model_to_use_raw = selected or GEMINI_MODEL_OVERRIDE or DEFAULT_MODEL
            # Strip redundant 'models/' prefix if present
            model_to_use = model_to_use_raw.split('/')[-1]
            logger.info("Using model (raw=%s, cleaned=%s)", model_to_use_raw, model_to_use)
            print(f"Model being passed to client.chats.create(): '{model_to_use}' (raw: '{model_to_use_raw}')")

            # Create chat with chosen model
            chat = client.chats.create(model=model_to_use)

            prompt = _build_prompt_from_messages(messages)
            resp = chat.send_message(prompt)

            # Expect .text per provided pattern
            if hasattr(resp, 'text') and isinstance(getattr(resp, 'text'), str):
                return getattr(resp, 'text').strip()
            if isinstance(resp, dict) and 'text' in resp:
                return resp['text'].strip()
            return str(resp).strip()
        except Exception as e:
            logger.exception('GenAI live call failed: %s', e)

    if last_user:
        return f"(local-echo) I received: {last_user}"
    return "(local-echo) Hello — no user message provided."
