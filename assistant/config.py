"""Configuration and simple defaults for the assistant.

Only lightweight constants live here (e.g., default push-to-talk key). For
sensitive values or environment-specific overrides, use environment variables
and python-dotenv in higher-level startup code.
"""

import os

# Default push-to-talk key (keyboard library key name). Override by setting
# the PUSH_TO_TALK_KEY environment variable or editing this file.
PUSH_TO_TALK_KEY = os.getenv("PUSH_TO_TALK_KEY", "right ctrl")
