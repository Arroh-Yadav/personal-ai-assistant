import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assistant.tools.registry import registry

args = {"path": "test_output/test-tool.txt", "content": "hello world"}
print('Dispatching create_file with args:', args)
res = registry.dispatch('create_file', args)
print('Result:', res)
if res.get('status')=='ok':
    p = Path(res.get('result', {}).get('path') if isinstance(res.get('result'), dict) else args['path'])
    if p.exists():
        print('File created. Contents:')
        print(p.read_text())
    else:
        print('File not found at expected path:', p)
else:
    print('Dispatch did not return ok; listing directory:')
    print([str(x) for x in Path('.').glob('test_output/**')])
