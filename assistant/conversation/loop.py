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
from assistant.tools.registry import registry
import json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant. Keep replies concise. "
    "When the user requests an action the program can perform (create/read files), you MUST call the registered tool via the function-calling interface using the provided tool schemas. "
    "Do NOT output shell commands or instructions. Use the exact tool name 'create_file' to write files and provide JSON arguments matching the schema."
)


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

            # Call the LLM wrapper with tool schemas
            tool_schemas = registry.get_schemas()

            # Conversation loop: handle tool_call cycles until a plain text reply
            while True:
                resp = llm_client.generate_response(messages, tools=tool_schemas)

                if resp.get('type') == 'text':
                    assistant_text = resp.get('text', '')

                    # Heuristic: detect JSON tool instructions embedded in assistant text
                    s = assistant_text.strip()
                    first = s.find('{')
                    last = s.rfind('}')
                    if first != -1 and last != -1 and last > first:
                        try:
                            json_block = s[first:last+1]
                            parsed = json.loads(json_block)
                            # attempt to extract tool name from prefix
                            prefix = s[:first]
                            tool_name = None
                            import re
                            m = re.search(r'`([^`]+)`', prefix)
                            if m:
                                tool_name = m.group(1).strip().lower()
                            else:
                                # fallback: last word before the JSON that isn't a code fence
                                cleaned = re.sub(r'```[a-zA-Z0-9]*', '', prefix)
                                tokens = cleaned.strip().split()
                                if tokens:
                                    tool_name = tokens[-1].strip('`:\"').lower()

                            if not tool_name:
                                if 'path' in parsed and 'content' in parsed:
                                    tool_name = 'create_file'

                            if tool_name:
                                print(f"Detected tool instruction in assistant text: {tool_name} {parsed}")
                                # Dispatch and continue the tool loop
                                result = registry.dispatch(tool_name, parsed)
                                tool_result_content = json.dumps(result)
                                conv_store.save_turn(self.session_id, 'tool', tool_result_content, tool_name=tool_name)
                                messages.append({'role': 'tool', 'content': tool_result_content})
                                # continue to ask the model with the tool result
                                continue
                        except Exception:
                            pass

                    # No embedded tool instruction; treat as final assistant reply
                    print('\nAssistant:', assistant_text, '\n')
                    conv_store.save_turn(self.session_id, 'assistant', assistant_text)
                    break

                elif resp.get('type') == 'tool_call':
                    tool_name = resp.get('tool_name')
                    arguments = resp.get('arguments') or {}
                    print(f"Tool call requested: {tool_name} with args: {arguments}")

                    # Safely dispatch the tool
                    result = registry.dispatch(tool_name, arguments or {})

                    # Save the tool call and result into the conversation as tool role
                    # Store the tool response as JSON to keep structure
                    tool_result_content = json.dumps(result)
                    conv_store.save_turn(self.session_id, 'tool', tool_result_content, tool_name=tool_name)

                    # Append the tool result to messages so the model can see it
                    messages.append({'role': 'tool', 'content': tool_result_content})

                    # Continue the loop to call the model again with the tool result
                    continue

                else:
                    # Unknown response type or error — print raw and break
                    print('\nAssistant (raw response):', resp)
                    conv_store.save_turn(self.session_id, 'assistant', str(resp))
                    break
