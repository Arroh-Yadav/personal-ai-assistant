from dotenv import load_dotenv
load_dotenv()
import os
try:
    from google import genai
except Exception as e:
    print('genai import failed:', e)
    raise

key = os.environ.get('GEMINI_API_KEY')
print('GEMINI_API_KEY present:', bool(key))
client = genai.Client(api_key=key)
models = client.models.list()
print('Found', len(models), 'models')
for m in models:
    name = getattr(m, 'name', None) or (m.get('name') if isinstance(m, dict) else None) or str(m)
    supports = []
    # heuristics
    if hasattr(m, 'generate_content') or hasattr(m, 'generateContent'):
        supports.append('generateContent')
    if hasattr(m, 'supported_generation_methods'):
        supports.append('supported_generation_methods')
    if hasattr(m, 'capabilities'):
        supports.append('capabilities')
    print('-', name, 'supports:', supports)

found = False
for m in models:
    name = getattr(m, 'name', None) or (m.get('name') if isinstance(m, dict) else None) or str(m)
    if name and 'gemini-3.1-flash-lite' in name.lower():
        print('MATCH FOUND:', name)
        found = True
if not found:
    print('No exact gemini-3.1-flash-lite found')
