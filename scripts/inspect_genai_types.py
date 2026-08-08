from dotenv import load_dotenv
load_dotenv()
from google import genai
import inspect, json, sys

print('genai module:', genai)
print('genai version:', getattr(genai, '__version__', 'unknown'))
print('has genai.types?', hasattr(genai, 'types'))
if hasattr(genai, 'types'):
    types = genai.types
    names = dir(types)
    interesting = [n for n in names if any(s in n.lower() for s in ['function','tool','declaration','schema','functioncall','function_call'])]
    print('Interesting type names:', interesting)
    for n in interesting:
        obj = getattr(types, n)
        print('\n----', n, '----')
        try:
            print('repr:', obj)
        except Exception:
            pass
        try:
            sig = inspect.signature(obj)
            print('signature:', sig)
        except Exception as e:
            print('no callable signature or not a constructor:', e)
        try:
            doc = (obj.__doc__ or '')[:400]
            if doc:
                print('doc snippet:', doc.replace('\n',' ')[:400])
        except Exception:
            pass
    # Try constructing a FunctionDeclaration if present
    if hasattr(types, 'FunctionDeclaration'):
        FD = types.FunctionDeclaration
        print('\nAttempting to construct FunctionDeclaration...')
        try:
            inst = FD(name='test_fn', description='desc', parameters={'type':'object'})
            print('Constructed FD:', inst)
            try:
                print('FD attr dict:', getattr(inst, '__dict__', 'no __dict__'))
            except Exception:
                pass
        except Exception as e:
            print('Construction failed:', type(e), e)
    else:
        print('No FunctionDeclaration in genai.types')
else:
    print('genai.types not available')
