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


def generate_response(messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict:
    """Call the GenAI chat and return either a text reply or a tool_call dict.

    Returns a dict with keys:
      - type: 'text' or 'tool_call' or 'error'
      - text: assistant text when type == 'text'
      - tool_name, arguments when type == 'tool_call'
      - raw: raw response object for debugging
    """
    last_user = None
    for m in reversed(messages):
        if m.get('role') == 'user':
            last_user = m.get('content')
            break

    if not (_HAS_GENAI and GEMINI_API_KEY):
        # local fallback
        if last_user:
            return {"type": "text", "text": f"(local-echo) I received: {last_user}", "raw": None}
        return {"type": "text", "text": "(local-echo) Hello — no user message provided.", "raw": None}

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        selected = _select_model(client)
        model_to_use_raw = selected or GEMINI_MODEL_OVERRIDE or DEFAULT_MODEL
        model_to_use = model_to_use_raw.split('/')[-1]
        logger.info("Using model (raw=%s, cleaned=%s)", model_to_use_raw, model_to_use)
        print(f"Model being passed to client.chats.create(): '{model_to_use}' (raw: '{model_to_use_raw}')")

        # Debug: print the tools object passed in
        print('tools parameter passed to generate_response is', type(tools), 'value:', (tools if isinstance(tools, list) else str(tools)))
        if isinstance(tools, list):
            try:
                print('Passing tool schemas to SDK:', [t.get('name') for t in tools])
            except Exception:
                pass

        # Try to create chat with tools attached (preferred). SDKs differ on kw name.
        chat = None
        try:
            if tools:
                # try common kw names on create()
                try:
                    chat = client.chats.create(model=model_to_use, tools=tools)
                except TypeError:
                    chat = client.chats.create(model=model_to_use, tool_definitions=tools)
            else:
                chat = client.chats.create(model=model_to_use)
        except TypeError:
            # fallback: create without tools
            chat = client.chats.create(model=model_to_use)

        prompt = _build_prompt_from_messages(messages)

        # Now send the message; some SDKs accept tools at send_message time
        try:
            if tools:
                try:
                    resp = chat.send_message(prompt, tools=tools)
                except TypeError:
                    resp = chat.send_message(prompt, tool_definitions=tools)
            else:
                resp = chat.send_message(prompt)
        except TypeError:
            # last resort: send without tools
            resp = chat.send_message(prompt)

        # Attach raw for debugging
        raw = resp

        # Check for structured automatic function/tool calling history
        try:
            afc = getattr(resp, 'automatic_function_calling_history', None)
            if afc:
                # Inspect last entry for tool name/args
                last = afc[-1]
                name = getattr(last, 'tool_name', None) or (last.get('tool_name') if isinstance(last, dict) else None)
                args = getattr(last, 'arguments', None) or (last.get('arguments') if isinstance(last, dict) else None)
                if name:
                    return {"type": "tool_call", "tool_name": name, "arguments": args, "raw": raw}
        except Exception:
            pass

        # Try to extract textual content
        text = None
        if hasattr(resp, 'text') and isinstance(getattr(resp, 'text'), str):
            text = getattr(resp, 'text')
        else:
            # try candidates -> content -> parts -> text
            try:
                cands = getattr(resp, 'candidates', None)
                if cands:
                    first = cands[0]
                    # candidate may have content attribute with parts
                    content = getattr(first, 'content', None)
                    if content and isinstance(content, list):
                        parts = []
                        for p in content:
                            t = getattr(p, 'text', None) or (p.get('text') if isinstance(p, dict) else None)
                            if t:
                                parts.append(t)
                        if parts:
                            text = ''.join(parts)
            except Exception:
                text = None

        if text:
            # attempt to parse JSON tool_call embedded in text
            stripped = text.strip()
            # look for JSON block inside the text (between first '{' and last '}')
            try:
                first = stripped.find('{')
                last = stripped.rfind('}')
                if first != -1 and last != -1 and last > first:
                    json_block = stripped[first:last+1]
                    parsed = json.loads(json_block)
                    # If parsed is a dict with path/content, guess tool may be create_file
                    if isinstance(parsed, dict):
                        # find tool name from text before JSON block (if present)
                        prefix = stripped[:first].strip()
                        # normalize potential prefixes like `write_file` or create_file:
                        tool_name = None
                        if prefix:
                            # take last token of prefix
                            tool_name = prefix.split()[-1].strip('`:\"').lower()
                        # heuristics: if parsed has path & content and tool name not provided, use create_file
                        if not tool_name:
                            if 'path' in parsed and 'content' in parsed:
                                tool_name = 'create_file'
                        # If parsed already contains tool_name/arguments
                        if 'tool_name' in parsed or 'name' in parsed:
                            tool_name = parsed.get('tool_name') or parsed.get('name')
                            args = parsed.get('arguments') or parsed.get('args') or parsed.get('parameters') or parsed.get('params') or {}
                        else:
                            args = parsed
                        if tool_name:
                            return {"type": "tool_call", "tool_name": tool_name, "arguments": args, "raw": raw}
            except Exception:
                pass

            return {"type": "text", "text": text.strip(), "raw": raw}

        # Fallback: stringified raw
        return {"type": "text", "text": str(raw), "raw": raw}

    except Exception as e:
        logger.exception('GenAI live call failed: %s', e)
        if last_user:
            return {"type": "text", "text": f"(local-echo) I received: {last_user}", "raw": None}
        return {"type": "text", "text": "(local-echo) Hello — no user message provided.", "raw": None}
