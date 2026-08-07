import os, sys, json
from dotenv import load_dotenv
load_dotenv()

env_info = {
    'GOOGLE_GENAI_USE_VERTEXAI': os.environ.get('GOOGLE_GENAI_USE_VERTEXAI'),
    'GOOGLE_CLOUD_PROJECT': os.environ.get('GOOGLE_CLOUD_PROJECT'),
    'GEMINI_MODEL_OVERRIDE': os.environ.get('GEMINI_MODEL'),
}
print('ENV:', json.dumps(env_info))

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

try:
    models = client.models.list()
except Exception as e:
    print('models.list() failed:', repr(e))
    sys.exit(0)

print('models.list() returned. Iterating:')
count = 0
for m in models:
    count += 1
    print('\n--- MODEL %d ---' % count)
    try:
        print('repr:', repr(m))
    except Exception as e:
        print('repr failed:', e)
    try:
        if isinstance(m, dict):
            print('dict:', json.dumps(m, default=str))
        else:
            attrs = {}
            for a in ('name','id','display_name','metadata','supported_generation_methods','capabilities'):
                if hasattr(m, a):
                    try:
                        attrs[a] = getattr(m, a)
                    except Exception as e:
                        attrs[a] = repr(e)
            print('attrs:', json.dumps(attrs, default=str))
    except Exception as e:
        print('attrs extraction failed:', repr(e))
    try:
        d = [a for a in dir(m) if not a.startswith('_')]
        print('dir (public):', d)
    except Exception as e:
        print('dir failed:', repr(e))

print('\nTotal models:', count)
