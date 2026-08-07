# 05. Folder Structure

## Proposed Layout

```
personal-ai-assistant/
├── .env                        # API keys, tokens (never committed)
├── .env.example                # template showing required vars, safe to commit
├── .gitignore
├── requirements.txt
├── README.md
├── main.py                     # entry point: starts the assistant loop
│
├── assistant/
│   ├── __init__.py
│   ├── config.py                # loads .env, holds constants/settings
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── capture.py            # push-to-talk + mic recording (sounddevice)
│   │   ├── stt.py                # faster-whisper wrapper
│   │   └── tts.py                # edge-tts wrapper
│   │
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── loop.py                # the core agent loop (section 4 of Architecture)
│   │   ├── llm_client.py          # thin wrapper around Gemini API (swappable)
│   │   └── prompts.py             # system prompt + prompt templates
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py            # tool registration + dispatch (Tool Exec Flow)
│   │   ├── local_tools.py         # open app, open URL, create/read file, search folder
│   │   ├── browser_tools.py       # Playwright-based tools
│   │   ├── telegram_tool.py       # Telegram send-message tool
│   │   └── github_tool.py         # GitHub API tool(s)
│   │
│   └── memory/
│       ├── __init__.py
│       ├── db.py                  # SQLite connection + schema setup
│       ├── conversations.py       # read/write conversation history
│       └── notes_tasks.py         # read/write notes and tasks
│
├── data/
│   └── assistant.db              # SQLite file (gitignored)
│
└── tests/
    ├── test_tools.py
    ├── test_memory.py
    └── test_conversation_loop.py
```

## Why This Structure

**`assistant/` as a package, not loose scripts at root** — even for a solo
project, treating this as an installable package (with `__init__.py` files)
means you can `import assistant.tools.registry` cleanly from tests or a
future UI, without path hacks.

**One subfolder per concern (`audio/`, `conversation/`, `tools/`, `memory/`)**
— this directly maps to the four architecture modules from
`04_SystemArchitecture.md`. If you're debugging TTS, you know exactly where
to look. If you're adding a tool, you know exactly which folder it lives in.

**`tools/` has one file per tool category, not one giant file** — this is
what makes NFR-6 real: adding a Weather API tool later means creating
`weather_tool.py` and registering it in `registry.py`. Nothing else changes.

**`llm_client.py` isolated from `loop.py`** — the loop shouldn't know or care
that you're using Gemini specifically. If you swap to Claude/OpenAI later
(as noted in the TRD), you edit this one file.

**`data/` separate from `assistant/`** — keeps generated/runtime data
(the SQLite file) clearly separate from source code, and easy to `.gitignore`
entirely.

**`tests/` mirrors the module structure** — even a lightweight test suite
(you don't need 100% coverage for a learning project) is worth having for
the tool registry and memory layer specifically, since those are the pieces
most likely to silently break as you add features.

## What's Deliberately NOT Here

- No `services/`, `controllers/`, `models/` MVC-style split — this isn't a
  web app, that structure doesn't map to anything real here.
- No `docker/`, `k8s/` — single local process, no containerization needed.
- No `migrations/` folder for the database — schema is small and stable
  enough to hand-manage via `db.py` for MVP (see `06_DatabaseSchema.md`).

## Where Things Go As the Project Grows

| If you add... | It goes in... |
|---|---|
| A new local tool | `tools/local_tools.py` (or a new file if it's a big category) |
| A new external API integration | New file in `tools/`, e.g. `weather_tool.py` |
| A new LLM provider | New `llm_client.py` implementation behind the same interface |
| A minimal UI (future idea) | New top-level `ui/` folder, imports from `assistant/` |
| Wake-word detection (future idea) | `audio/wake_word.py`, plugged in before `capture.py` |
