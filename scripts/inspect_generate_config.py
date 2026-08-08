from dotenv import load_dotenv
load_dotenv()
from google import genai
import inspect

G = genai.types.GenerateContentConfig
print('GenerateContentConfig exists:', bool(G))
print('signature:', inspect.signature(G))
print('doc:', (G.__doc__ or '')[:400])
print('attrs:')
print([n for n in dir(G) if not n.startswith('_')][:200])

# print the names of types that seem relevant
candidates = [n for n in dir(genai.types) if 'Function' in n or 'Tool' in n or 'Generate' in n or 'FunctionDeclaration' in n]
print('\nRelevant genai.types names sample:', candidates[:200])
