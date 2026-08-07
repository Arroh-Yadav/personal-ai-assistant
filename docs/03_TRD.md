# 03. Technical Requirements Document (TRD)

## 1. Language: Python

**Why:** Every major LLM SDK, STT/TTS library, and automation tool has
first-class Python support. It's the path of least friction for a learning
project focused on AI concepts rather than language mechanics.

**Alternatives considered:**
- Node.js/TypeScript — great tool-calling ecosystem too, slightly less mature
  for local STT/TTS and browser automation tooling.
- Go/Rust — excellent for production systems, but adds a learning curve
  unrelated to the actual goal (understanding AI agents).

**Pros:** huge ecosystem, readable, fast to prototype, every relevant library exists.
**Cons:** not the fastest language at runtime — irrelevant here since bottlenecks
are network calls (LLM/API), not CPU.

---

## 2. LLM: Google Gemini API (Flash / Flash-Lite)

**Why:** Genuine ongoing free tier (not a trial), native function/tool-calling
support, and a 1M token context window — everything the tool-calling loop
needs, at no cost during learning.

**Alternatives considered:**
- **Anthropic Claude API / OpenAI API** — arguably stronger reasoning and
  tool-use quality, but no meaningful ongoing free tier. Good upgrade path
  later — see "swap-ability" note below.
- **Local LLM via Ollama (Llama/Mistral)** — fully free forever and great for
  understanding inference itself, but noticeably weaker/less consistent at
  structured tool-calling. Listed as a Future Idea, not MVP.

**Pros:** free, real function-calling, generous rate limits for personal use.
**Cons:** occasional 429 rate-limit errors under heavy use (handled with
retry/backoff — see 07_ToolArchitecture.md); quality slightly behind top-tier
paid models for complex reasoning.

**Design note — keep it swappable:** wrap all LLM calls behind a small
`llm_client` interface (`generate(messages, tools) -> response`). This means
switching to Claude/OpenAI later is a one-file change, not a rewrite —
valuable both for learning multiple providers and as a portfolio detail.

---

## 3. Speech-to-Text: `faster-whisper` (local)

**Why:** Runs OpenAI's Whisper model fully locally and free, no API key or
network round-trip, and it's genuinely excellent quality even on CPU with
smaller model sizes (`base`/`small`).

**Alternatives considered:**
- Cloud STT (Google/Azure Speech) — good quality but adds cost and another
  API key to manage for something local inference handles well.

**Pros:** free, private, no rate limits, works offline.
**Cons:** first run downloads a model file (one-time); larger models need
decent CPU/RAM — `small` model is a good balance for a laptop.

---

## 4. Text-to-Speech: `edge-tts`

**Why:** Free, no API key, and produces natural-sounding neural voices
(uses Microsoft Edge's TTS service under the hood via an open-source client).
Much better quality than fully offline options like `pyttsx3` for very little
extra complexity.

**Alternatives considered:**
- `pyttsx3` — fully offline, zero network dependency, but robotic-sounding
  voices. Good fallback if you want zero network dependency for TTS too.
- Cloud TTS (Google/ElevenLabs) — higher quality voices but paid/rate-limited.

**Pros:** free, natural voices, simple API.
**Cons:** technically depends on an unofficial API surface, so treat it as
"good enough for learning," not something to depend on in production.

---

## 5. Audio I/O: `sounddevice` + `numpy`

**Why:** Simple, well-documented Python audio capture/playback library that
plays nicely with both `faster-whisper` and TTS output buffers.

**Pros:** minimal boilerplate, cross-platform.
**Cons:** push-to-talk key detection needs a small separate library
(`keyboard` or `pynput`) since audio libraries don't handle key listening.

---

## 6. Memory / Storage: SQLite

**Why:** Zero setup (built into Python's standard library), a real relational
database (good for learning schema design), and completely sufficient for
single-user, local data volumes.

**Alternatives considered:**
- Postgres/MySQL — real-world relevant, but requires running a server
  process for a single-user local tool. Unnecessary complexity per NFR-1.
- Flat JSON files — simpler still, but you lose the chance to learn basic
  schema design and SQL querying, which has genuine transferable value.

**Pros:** free, zero-config, real SQL practice, one file on disk.
**Cons:** not built for concurrent multi-process access — irrelevant for a
single-user local assistant.

---

## 7. Browser Automation: Playwright

**Why:** Actively maintained, reliable, and has a clean Python API. Handles
the limited scope defined in the PRD (open pages, fill forms, click, read
content) without fragile scraping hacks.

**Alternatives considered:**
- Selenium — older, clunkier API, more flaky waits/timing issues.

**Pros:** modern API, good docs, headless or visible browser both supported.
**Cons:** adds a browser binary dependency (`playwright install`), one-time
setup step.

---

## 8. External API Clients

| Service | Library | Auth |
|---|---|---|
| Telegram | `python-telegram-bot` | Bot token (from @BotFather) |
| GitHub | `requests` directly against REST API (or `PyGithub`) | Personal access token |

**Why start with these two:** both have simple, fast token-based auth
(no OAuth flow), so you can get to "it works" quickly and spend your learning
time on the tool-calling integration, not the auth handshake. Google
Calendar/Gmail use OAuth2 and are earmarked for Phase 2 for this reason.

---

## 9. Dependency Management: `venv` + `requirements.txt`

**Why:** Standard, zero-magic, and exactly as much tooling as a single-dev
learning project needs.

**Alternatives considered:** Poetry/PDM — nicer dependency resolution, but
adds a layer of tooling to learn that isn't the point of this project.

---

## 10. System Overview

```
Voice In (push-to-talk)
   → faster-whisper (STT)
   → Conversation Loop (Gemini API, tool-calling enabled)
        → Tool Registry (local tools + API clients)
        → SQLite (memory read/write)
   → Response text
   → edge-tts (TTS)
   → Voice Out
```

No web server, no background daemons for MVP — a single long-running Python
process, terminal-based, driven by push-to-talk input.

## 11. Full Dependency List (MVP)

```
google-genai          # Gemini API SDK
faster-whisper         # local speech-to-text
edge-tts               # text-to-speech
sounddevice, numpy     # audio capture/playback
keyboard               # push-to-talk key detection
playwright             # browser automation
python-telegram-bot    # Telegram integration
requests               # GitHub API + general HTTP
python-dotenv          # credential/config management
```
