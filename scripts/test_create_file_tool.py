import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant.conversation.loop import ConversationLoop
from assistant.memory import conversations as conv_store
from assistant.tools.registry import registry
from assistant.conversation import llm_client
import json

# Use a fixed session
session = 'tool-test-session'
loop = ConversationLoop(session_id=session)

# Simulate user request to create a file
user_input = 'Create a file at test_output/test-tool.txt with the content hello world'
print('User input:', user_input)
conv_store.save_turn(session, 'user', user_input)
messages = loop.build_messages()
messages.append({'role':'user','content':user_input})

# Get tool schemas
tools = registry.get_schemas()

# Run the tool calling loop once
while True:
    resp = llm_client.generate_response(messages, tools=tools)
    print('LLM response type:', resp.get('type'))
    if resp.get('type') == 'text':
        print('Assistant text:', resp.get('text'))
        conv_store.save_turn(session, 'assistant', resp.get('text'))
        break
    elif resp.get('type') == 'tool_call':
        name = resp.get('tool_name')
        args = resp.get('arguments') or {}
        print('Dispatching tool:', name, args)
        res = registry.dispatch(name, args)
        print('Tool result:', res)
        conv_store.save_turn(session, 'tool', json.dumps(res), tool_name=name)
        messages.append({'role':'tool','content': json.dumps(res)})
        continue
    else:
        print('Unknown response:', resp)
        break

print('Done')
