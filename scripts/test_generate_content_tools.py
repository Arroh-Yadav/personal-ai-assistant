from dotenv import load_dotenv
load_dotenv()
import os
from google import genai
import json

key = os.environ.get('GEMINI_API_KEY')
model = os.environ.get('GEMINI_MODEL') or 'gemini-3.1-flash-lite'
client = genai.Client(api_key=key)

# Load registry
import sys, os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from assistant.tools import registry as tools_registry

schemas = tools_registry.registry.get_schemas()
FD = genai.types.FunctionDeclaration
ToolType = genai.types.Tool
SchemaType = genai.types.Schema

def _build_schema(jschema):
    if jschema is None:
        return None
    if isinstance(jschema, genai.types.Schema):
        return jschema
    if not isinstance(jschema, dict):
        return jschema
    kw = {}
    for f in ('title','description','default','required','type','format','enum','minItems','maxItems','minLength','maxLength','minimum','maximum'):
        if f in jschema:
            kw[f] = jschema[f]
    if 'properties' in jschema and isinstance(jschema['properties'], dict):
        props = {}
        for k,v in jschema['properties'].items():
            props[k] = _build_schema(v)
        kw['properties'] = props
    if 'items' in jschema:
        kw['items'] = _build_schema(jschema['items'])
    try:
        return SchemaType(**kw)
    except Exception:
        return jschema

built_tools = []
for s in schemas:
    name = s.get('name')
    desc = s.get('description')
    params = s.get('parameters')
    schema_obj = _build_schema(params)
    fd = FD(name=name, description=desc, parameters=schema_obj)
    try:
        tool = ToolType(functionDeclarations=[fd])
    except TypeError:
        tool = ToolType(function_declarations=[fd])
    built_tools.append(tool)

print('Built tools count:', len(built_tools))
print('Preview of first tool:', json.dumps({'name': built_tools[0].function_declarations[0].name, 'params': str(built_tools[0].function_declarations[0].parameters)}, indent=2, default=str))

prompt = 'Create a file called demo.txt with content hello world'

config = genai.types.GenerateContentConfig(tools=built_tools, automaticFunctionCalling=genai.types.AutomaticFunctionCallingConfig())

print('Calling generate_content with model=', model)
resp = client.models.generate_content(model=model, contents=prompt, config=config)
print('Response finish_reason and candidates:')
print(resp)
# try to inspect automatic_function_calling_history or function calls
try:
    afc = getattr(resp, 'automatic_function_calling_history', None)
    print('automatic_function_calling_history:', afc)
except Exception as e:
    print('no afc:', e)

# print candidates' finish_reason
try:
    cands = getattr(resp, 'candidates', None)
    if cands:
        for i,c in enumerate(cands):
            fr = getattr(c, 'finish_reason', None)
            print('candidate', i, 'finish_reason:', fr)
except Exception as e:
    print('failed to read candidates:', e)

print('Done')
