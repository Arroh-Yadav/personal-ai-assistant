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
DEFAULT_MODEL = 'gemini-3.1-flash-lite'
logger = logging.getLogger(__name__)

# Warn loudly if GEMINI_MODEL isn't set so it's not a silent fallback
if not GEMINI_MODEL_OVERRIDE:
    logger.warning('GEMINI_MODEL not set; falling back to DEFAULT_MODEL=%s. Set GEMINI_MODEL in .env to avoid silent fallback.', DEFAULT_MODEL)
    try:
        # also print to console for immediate visibility
        print(f"WARNING: GEMINI_MODEL not set; falling back to default model {DEFAULT_MODEL}")
    except Exception:
        pass


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

        import json as _json
        # Normalize tools into the exact payload the SDK expects. Prefer the
        # simpler parametersJsonSchema path: pass registry JSON Schema dicts
        # directly via FunctionDeclaration.parametersJsonSchema, then wrap each
        # declaration into a genai.types.Tool(functionDeclarations=[...]).
        tools_payload = None
        if tools:
            try:
                normalized = []
                for t in tools:
                    normalized.append({
                        'name': t.get('name'),
                        'description': t.get('description'),
                        'parameters': t.get('parameters')
                    })

                log_payload = normalized

                if hasattr(genai, 'types') and hasattr(genai.types, 'FunctionDeclaration') and hasattr(genai.types, 'Tool') and hasattr(genai.types, 'Schema'):
                    FD = genai.types.FunctionDeclaration
                    ToolType = genai.types.Tool
                    SchemaType = genai.types.Schema

                    def _build_schema(jschema):
                        # recursively convert a JSON Schema dict into genai.types.Schema
                        if jschema is None:
                            return None
                        if isinstance(jschema, genai.types.Schema):
                            return jschema
                        if not isinstance(jschema, dict):
                            return jschema
                        kw = {}
                        # copy simple fields
                        for f in ('title','description','default','required','type','format','enum','minItems','maxItems','minLength','maxLength','minimum','maximum'):
                            if f in jschema:
                                kw[f] = jschema[f]
                        # properties
                        if 'properties' in jschema and isinstance(jschema['properties'], dict):
                            props = {}
                            for k,v in jschema['properties'].items():
                                props[k] = _build_schema(v)
                            kw['properties'] = props
                        # items
                        if 'items' in jschema:
                            kw['items'] = _build_schema(jschema['items'])
                        try:
                            return SchemaType(**kw)
                        except Exception:
                            # fallback: return original dict
                            return jschema

                    built = []
                    for n in normalized:
                        try:
                            params = n.get('parameters')
                            schema_obj = _build_schema(params)
                            fd_inst = FD(name=n.get('name'), description=n.get('description'), parameters=schema_obj)
                            # Some SDK variants use function_declarations vs functionDeclarations attr
                            try:
                                tool_inst = ToolType(functionDeclarations=[fd_inst])
                            except TypeError:
                                tool_inst = ToolType(function_declarations=[fd_inst])
                            built.append(tool_inst)
                        except Exception:
                            # fallback to dict if construction fails for a particular tool
                            built.append({'name': n.get('name'), 'description': n.get('description'), 'parameters': n.get('parameters')})
                    tools_payload = built
                else:
                    # SDK types not available; pass plain dicts
                    tools_payload = normalized
            except Exception as e:
                logger.exception('Failed to build tools payload: %s', e)
                tools_payload = tools
                log_payload = tools
        else:
            tools_payload = []
            log_payload = []

        # Log the tools payload JSON before calling the API for easy debugging
        try:
            import json as _json
            # Build a debug-friendly view of the actual SDK objects we'll send
            debug_payload = []
            try:
                for t in (tools_payload or []):
                    if hasattr(t, 'functionDeclarations'):
                        fds = []
                        for fd in getattr(t, 'functionDeclarations') or []:
                            fd_repr = {
                                'name': getattr(fd, 'name', None),
                                'description': getattr(fd, 'description', None),
                                'parametersJsonSchema': getattr(fd, 'parametersJsonSchema', None) or getattr(fd, 'parameters', None)
                            }
                            fds.append(fd_repr)
                        debug_payload.append({'type': 'Tool', 'functionDeclarations': fds})
                    else:
                        debug_payload.append(t)
            except Exception:
                debug_payload = log_payload

            print('Final tools payload (JSON):')
            print(_json.dumps(debug_payload, default=str, indent=2))
        except Exception:
            print('Final tools payload (non-serializable) ->', str(log_payload))

        # If tools are provided, prefer the lower-level generate_content path
        # which accepts tools/config directly and is stateless. Build the full
        # conversation history into the 'contents' parameter each call.
        raw = None
        if tools_payload:
            try:
                # Build contents list from messages so the model sees full history
                contents = []
                for m in messages:
                    role = m.get('role')
                    content = m.get('content', '')
                    if role == 'system':
                        # as a standalone system instruction
                        contents.append(content)
                    elif role == 'user':
                        contents.append(f"User: {content}")
                    elif role == 'assistant':
                        contents.append(f"Assistant: {content}")

                # Also include a final assistant instruction to answer concisely
                contents.append('\nAssistant, please reply concisely to the latest user message above.')

                # Build GenerateContentConfig with tools and automatic function calling
                try:
                    cfg = genai.types.GenerateContentConfig(tools=tools_payload, automaticFunctionCalling=genai.types.AutomaticFunctionCallingConfig())
                except Exception:
                    # fallback: try without explicit AutomaticFunctionCalling
                    try:
                        cfg = genai.types.GenerateContentConfig(tools=tools_payload)
                    except Exception:
                        cfg = None

                # Call generate_content directly
                if cfg is not None:
                    resp = client.models.generate_content(model=model_to_use, contents=contents, config=cfg)
                else:
                    resp = client.models.generate_content(model=model_to_use, contents=contents)

                raw = resp

                # Inspect candidates content parts for a FunctionCall
                try:
                    cands = getattr(resp, 'candidates', None)
                    if cands:
                        first = cands[0]
                        content = getattr(first, 'content', None)
                        if content and isinstance(content, list):
                            for part in content:
                                fc = getattr(part, 'function_call', None) or (part.get('function_call') if isinstance(part, dict) else None)
                                if fc:
                                    # fc may be a genai.types.FunctionCall or dict
                                    name = getattr(fc, 'name', None) or (fc.get('name') if isinstance(fc, dict) else None)
                                    args = getattr(fc, 'args', None) or (fc.get('args') if isinstance(fc, dict) else None) or getattr(fc, 'arguments', None) or (fc.get('arguments') if isinstance(fc, dict) else None)
                                    # args may be a dict already
                                    return {"type": "tool_call", "tool_name": name, "arguments": args, "raw": raw}
                except Exception:
                    pass

            except Exception as e:
                logger.exception('GenAI generate_content call failed: %s', e)
                # Fall through to text fallback below
        else:
            # No tools: try chat session approach as before
            try:
                chat = client.chats.create(model=model_to_use)
                prompt = _build_prompt_from_messages(messages)
                resp = chat.send_message(prompt)
                raw = resp
            except Exception as e:
                logger.exception('Chat-based call failed: %s', e)
                # Fall through to fallback

        # Attach raw for debugging if not already set
        if raw is None:
            raw = None

        # Check for structured automatic function/tool calling history
        try:
            afc = getattr(raw, 'automatic_function_calling_history', None)
            if afc:
                last = afc[-1]
                name = getattr(last, 'tool_name', None) or (last.get('tool_name') if isinstance(last, dict) else None)
                args = getattr(last, 'arguments', None) or (last.get('arguments') if isinstance(last, dict) else None)
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
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
