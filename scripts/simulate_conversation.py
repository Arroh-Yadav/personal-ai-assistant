import sys
from pathlib import Path
# Ensure project root is on sys.path so `assistant` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant.conversation.loop import ConversationLoop
from assistant.memory import conversations as conv_store

s = ConversationLoop(session_id='sim-session')
user_msg = 'Hello, assistant. How are you?'
print('Simulating user message:', user_msg)
conv_store.save_turn(s.session_id, 'user', user_msg)
messages = s.build_messages()
print('Built messages for LLM:', messages)
from assistant.conversation import llm_client
resp = llm_client.generate_response(messages)
print('Assistant reply:', resp)
conv_store.save_turn(s.session_id, 'assistant', resp)
print('Saved assistant reply to DB.')
