from dotenv import load_dotenv
load_dotenv()
import inspect
from google import genai
print('genai version', getattr(genai, '__version__', 'unknown'))
print('models.generate_content exists?', hasattr(genai.Client, 'models') or hasattr(genai, 'models'))
try:
    client = genai.Client(api_key='dummy')
    func = client.models.generate_content
    print('signature:', inspect.signature(func))
    doc = (func.__doc__ or '')[:1000]
    print('doc snippet:', doc)
except Exception as e:
    print('error inspecting generate_content:', e)
