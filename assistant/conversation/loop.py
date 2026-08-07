"""Simple text-only conversation loop for Phase 1.

Reads user input from the terminal, loads recent history from SQLite,
calls the llm_client.generate_response, prints the assistant reply, and
persists both user and assistant turns.
"""
from typing import List, Dict
import uuid
import logging

from assistant.conversation import llm_client
from assistant.memory import conversations as conv_store

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a helpful assistant. Keep replies concise."


class ConversationLoop:
    def __init__(self, session_id: str = None, history_limit: int = 20):
        self.session_id = session_id or str(uuid.uuid4())
        self.history_limit = history_limit

    def build_messages(self) -> List[Dict[str, str]]:
        # Load recent history and convert to message list
        turns = conv_store.load_recent(self.session_id, limit=self.history_limit)
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for t in turns:
            messages.append({'role': t['role'], 'content': t['content']})
        return messages

    def run(self) -> None:
        print("Starting text conversation loop. Type 'exit' or Ctrl-C to quit.")
        while True:
            try:
                user_input = input('You: ').strip()
            except (KeyboardInterrupt, EOFError):
                print('\nExiting conversation loop.')
                break

            if not user_input:
                continue
            if user_input.lower() in ('exit', 'quit'):
                print('Goodbye.')
                break

            # Save user turn
            conv_store.save_turn(self.session_id, 'user', user_input)

            # Build messages including history
            messages = self.build_messages()
            messages.append({'role': 'user', 'content': user_input})

            # Call the LLM wrapper
            assistant_text = llm_client.generate_response(messages)

            # Print and save assistant turn
            print('\nAssistant:', assistant_text, '\n')
            conv_store.save_turn(self.session_id, 'assistant', assistant_text)
