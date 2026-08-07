# 08. Development Roadmap

## Philosophy

Each phase should end with something you can actually run — not just code
that compiles. Every milestone has a concrete "done" test. Build in this
order because each phase depends on the plumbing from the one before it.

---

## Phase 0 — Project Scaffolding
**Goal:** empty but correct skeleton, before any real logic.

- Create the folder structure from `05_FolderStructure.md`
- Set up `venv`, `requirements.txt`, `.env.example`
- Initialize git repo, push to GitHub, set up Issues for backlog tracking
- `main.py` runs and prints "Assistant started" — nothing else yet

**Done when:** `python main.py` runs with no errors, repo is on GitHub.

**Concepts learned:** project scaffolding, environment management, git hygiene.

---

## Phase 1 — Text-Only Conversation Loop
**Goal:** get the agent loop working before adding voice complexity on top.

- Implement `llm_client.py` (Gemini API wrapper)
- Implement `loop.py` with a basic text-in/text-out conversation (no tools yet)
- Type messages in the terminal, get LLM replies back
- Store each turn in the `conversations` table

**Done when:** you can have a multi-turn typed conversation that remembers
context within the session and persists to SQLite.

**Concepts learned:** LLM API basics, message history management, SQLite writes.

---

## Phase 2 — Tool Calling (text-only)
**Goal:** the actual core skill of this project — still no voice yet, to
isolate this concept from audio complexity.

- Build `registry.py` and 2–3 simple local tools (`create_file`, `read_file`, `open_url`)
- Wire tool schemas into the Gemini call
- Implement the full dispatch/execute/return-result loop from `07_ToolArchitecture.md`
- Type "create a file called notes.txt with 'hello world'" and watch it happen

**Done when:** the LLM correctly chooses to call a tool vs. reply directly,
and multi-step tool chains work (e.g. "read file X, then summarize it").

**Concepts learned:** function calling, the agent loop, structured error handling.

---

## Phase 3 — Voice In / Voice Out
**Goal:** bolt speech onto the already-working text loop — don't build voice
and tool-calling simultaneously, that's two hard problems at once.

- Implement `capture.py` (push-to-talk + `sounddevice` recording)
- Implement `stt.py` (`faster-whisper` transcription)
- Implement `tts.py` (`edge-tts` synthesis + playback)
- Swap the text input/output in the Phase 1–2 loop for voice I/O

**Done when:** you can hold a key, speak a command, and hear a spoken reply
— including tool-calling commands from Phase 2 working by voice.

**Concepts learned:** STT/TTS pipelines, audio I/O, latency tradeoffs.

---

## Phase 4 — Remaining Local + Browser Tools
**Goal:** round out the local automation tool set.

- Add `open_app`, `search_folder` local tools
- Add Playwright-based browser tools (`browser_open`, `browser_fill_form`, `browser_click`, `browser_read_content`)

**Done when:** you can say "search Google for X" or "open VS Code" and it works.

**Concepts learned:** subprocess/OS automation, browser automation basics.

---

## Phase 5 — External API Integrations
**Goal:** real third-party API practice.

- Add `telegram_tool.py` (send message)
- Add `github_tool.py` (list issues, create issue)
- Handle auth, rate limits, and structured errors per `07_ToolArchitecture.md`

**Done when:** "send myself a Telegram message saying X" and "list open
issues on my repo" both work end-to-end by voice.

**Concepts learned:** API auth patterns (bot tokens vs. PATs), rate limit handling.

---

## Phase 6 — Notes, Tasks & Preferences
**Goal:** complete the memory system beyond just conversation history.

- Implement `notes_tasks.py` (CRUD for `notes`, `tasks`, `preferences` tables)
- Add corresponding tools (`create_note`, `list_tasks`, `complete_task`, `set_preference`, etc.)
- Wire memory retrieval into the loop's context-building step

**Done when:** you can say "remember that I prefer metric units" in one
session, restart the assistant, and ask "what units do I prefer" in a new
session and get the right answer.

**Concepts learned:** persistent memory design, context window management.

---

## Phase 7 — Polish & Portfolio Readiness
**Goal:** make it presentable and robust, not add new features.

- Write a proper `README.md` (what it does, setup steps, demo GIF/clip)
- Add the `tests/` suite for tools + memory layer
- Clean up error messages and edge cases found during your own daily use
- Record a short demo video/GIF for the GitHub repo

**Done when:** a stranger could clone the repo, follow the README, and get
it running without asking you anything.

---

## Explicitly Post-MVP (Future Ideas — track as GitHub Issues, not here)

- Streaming voice responses
- Wake-word detection
- Google Calendar / Gmail (OAuth) integrations
- Weather / News API tools
- Minimal web or mobile UI
- Local LLM option (Ollama)
- Vector-search-based long-term memory
- Scheduled/autonomous background tasks (possible n8n territory — see earlier discussion)

## Suggested Pace

This is a learning project, not a sprint — resist rushing to Phase 5 before
Phase 2 is actually solid. The agent loop in Phase 2 is the concept
everything else depends on; time spent there pays off in every later phase.
