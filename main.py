import argparse
from assistant.conversation.loop import ConversationLoop


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Assistant — conversational tool-calling agent with optional voice input/output."
    )
    parser.add_argument(
        '--voice',
        action='store_true',
        help="Enable voice mode (push-to-talk microphone input, TTS output). Default: text mode (terminal input/output)."
    )
    args = parser.parse_args()

    loop = ConversationLoop()
    if args.voice:
        loop.run_voice()
    else:
        loop.run()


if __name__ == '__main__':
    main()
