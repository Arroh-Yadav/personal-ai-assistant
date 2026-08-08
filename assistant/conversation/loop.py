"""Simple conversation loop for Phase 3 (text and voice modes).

Reads user input from the terminal (text mode) or via microphone (voice mode),
loads recent history from SQLite, calls the llm_client.generate_response,
persists turns, and handles tool dispatch.

run() — text mode: reads terminal input
run_voice() — voice mode: reads microphone input via push-to-talk, transcribes,
synthesizes replies
"""
from typing import List, Dict
import uuid
import logging
import json
import re

from assistant.conversation import llm_client
from assistant.memory import conversations as conv_store
from assistant.tools.registry import registry

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

    def process_message(self, user_input: str) -> str:
        """Process a user message through the LLM and tool dispatch loop.

        Handles all conversation logic: saving turns, tool calls, embedded JSON
        heuristic, and tool dispatch. Returns the final assistant text.

        Args:
            user_input: The user's message text.

        Returns:
            The final assistant text (or stringified response for unknown types).
        """
        # Save user turn
        conv_store.save_turn(self.session_id, 'user', user_input)

        # Build messages including history
        messages = self.build_messages()
        messages.append({'role': 'user', 'content': user_input})

        # Call the LLM wrapper with tool schemas
        tool_schemas = registry.get_schemas()

        # Conversation loop: handle tool_call cycles until a plain text reply
        # (max 10 iterations as a safety net against infinite loops)
        max_iterations = 10
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
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
                conv_store.save_turn(self.session_id, 'assistant', assistant_text)
                return assistant_text

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
                # Unknown response type or error — return stringified response
                conv_store.save_turn(self.session_id, 'assistant', str(resp))
                return str(resp)

        # Max iterations exceeded; return error message
        error_msg = "I'm having trouble completing this — the tool loop didn't resolve after multiple attempts."
        conv_store.save_turn(self.session_id, 'assistant', error_msg)
        return error_msg

    def run(self) -> None:
        """Text mode: read from terminal, print replies."""
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

            assistant_text = self.process_message(user_input)
            print('\nAssistant:', assistant_text, '\n')

    def run_voice(self) -> None:
        """Voice mode: read from microphone (push-to-talk), transcribe, speak replies.

        Imports audio dependencies lazily to keep text-mode independent.
        """
        # Lazy imports — keep audio dependencies out of text-mode run()
        try:
            from assistant.audio.capture import record_push_to_talk
            from assistant.audio.stt import transcribe
            from assistant.audio.tts import speak
        except ImportError as e:
            print(f"Error: audio dependencies not installed: {e}")
            print("Install with: pip install -r requirements.txt")
            return

        key = None
        try:
            from assistant import config
            key = getattr(config, "PUSH_TO_TALK_KEY", "right ctrl")
        except Exception:
            key = "right ctrl"

        print(f"Starting voice conversation loop. Hold '{key}' to speak, release to send.")
        print("Type 'exit' or 'quit' or press Ctrl-C to quit.\n")

        while True:
            try:
                # Capture audio
                try:
                    result = record_push_to_talk()
                except Exception as e:
                    print(f"Error recording audio: {e}")
                    continue

                if result is None:
                    print("No audio recorded, try again.")
                    continue

                audio, sr = result

                # Transcribe
                try:
                    user_text = transcribe(audio, sr)
                except Exception as e:
                    print(f"Error transcribing: {e}")
                    continue

                if not user_text or not user_text.strip():
                    print("Didn't catch that, try again.")
                    continue

                print(f"You said: {user_text}")

                # Check for exit words
                if user_text.lower().strip() in ('exit', 'quit'):
                    print("Goodbye.")
                    break

                # Process message (text-to-speech reply)
                try:
                    assistant_text = self.process_message(user_text)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    continue

                print('\nAssistant:', assistant_text, '\n')

                # Speak the reply
                try:
                    speak(assistant_text)
                except Exception as e:
                    print(f"Error speaking reply: {e}")
                    continue

            except KeyboardInterrupt:
                print('\nExiting voice conversation loop.')
                break
