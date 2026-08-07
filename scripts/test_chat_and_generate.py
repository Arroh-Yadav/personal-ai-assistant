import os, sys, traceback
from dotenv import load_dotenv
load_dotenv()

model_env = os.environ.get('GEMINI_MODEL')
print(f"GEMINI_MODEL from env: {model_env}")

try:
    from google import genai
except Exception as e:
    print('Import genai failed:', repr(e))
    sys.exit(0)

try:
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
except Exception as e:
    print('Client init failed:', repr(e))
    sys.exit(0)

# Test chat.create + send_message
print('\n== chat.create() -> send_message() test ==')
chat_ok = False
try:
    model = model_env or 'gemini-flash-latest'
    print('Creating chat with model:', model)
    chat = client.chats.create(model=model)
    print('chat created; sending message...')
    resp = chat.send_message('Please say hello in one sentence.')
    print('chat.send_message repr:', repr(resp))
    text = getattr(resp, 'text', None)
    if text:
        print('chat.send_message.text:', text)
    chat_ok = True
except Exception as e:
    print('chat flow failed:')
    traceback.print_exc()

# If chat failed, test models.generate_content
if not chat_ok:
    print('\n== Falling back to client.models.generate_content() tests ==')
    tried = []
    for m in ('gemini-2.5-flash', 'models/gemini-2.5-flash', 'gemini-flash-latest'):
        try:
            print(f'Calling generate_content with model="{m}"')
            r = client.models.generate_content(model=m, contents=[{'type':'text','text':'hello'}])
            print('generate_content repr:', repr(r))
            # attempt to extract text
            t = None
            if hasattr(r, 'output'):
                t = getattr(r, 'output')
            if hasattr(r, 'candidates'):
                try:
                    c = getattr(r, 'candidates')[0]
                    if hasattr(c, 'content'):
                        pieces = [getattr(p, 'text', None) or (p.get('text') if isinstance(p, dict) else None) for p in getattr(c, 'content')]
                        t = ''.join([p for p in pieces if p])
                except Exception:
                    pass
            if t:
                print('Extracted text:', t)
            print('generate_content succeeded for', m)
            break
        except Exception:
            print('generate_content failed for', m)
            traceback.print_exc()

print('\nDone')
