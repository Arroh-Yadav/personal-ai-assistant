from dotenv import load_dotenv
load_dotenv()
import json
import os, sys

# Ensure project root is on sys.path so 'assistant' package imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the registry
from assistant.tools import registry as tools_registry

# Try to import genai types if available
try:
    from google import genai
    _HAS_GENAI = True
except Exception:
    genai = None
    _HAS_GENAI = False

schemas = tools_registry.registry.get_schemas()
output = []

if _HAS_GENAI and hasattr(genai, 'types'):
    FD = genai.types.FunctionDeclaration
    ToolType = genai.types.Tool
    for s in schemas:
        name = s.get('name')
        desc = s.get('description')
        params = s.get('parameters')
        try:
            fd_inst = FD(name=name, description=desc, parametersJsonSchema=params)
            tool_inst = ToolType(functionDeclarations=[fd_inst])
            # build JSON-friendly dict
            fds = []
            f_decls = getattr(tool_inst, 'functionDeclarations', None) or getattr(tool_inst, 'function_declarations', None) or []
            for fd in f_decls:
                params_js = getattr(fd, 'parameters_json_schema', None) or getattr(fd, 'parametersJsonSchema', None) or getattr(fd, 'parameters', None)
                fds.append({
                    'name': getattr(fd, 'name', None),
                    'description': getattr(fd, 'description', None),
                    'parametersJsonSchema': params_js
                })
            output.append({'type': 'Tool', 'function_declarations': fds})
        except Exception as e:
            output.append({'error': f'failed to construct for {name}: {e}', 'schema': s})
else:
    # Fallback: just output the raw schemas
    for s in schemas:
        output.append({'type': 'dict_tool', 'schema': s})

# Print to stdout
print(json.dumps(output, indent=2))

# Save to file for reference
with open('scripts/tools_payload.json', 'w', encoding='utf-8') as fh:
    json.dump(output, fh, indent=2)

print('\nSaved to scripts/tools_payload.json')
