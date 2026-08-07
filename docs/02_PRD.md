# 02. Product Requirements Document (PRD)

## 1. Purpose

Define concrete, testable requirements for the MVP of the personal AI voice
assistant, so "done" has a clear meaning at every stage.

## 2. User Stories

### Voice Interaction
- As a user, I want to press a key and speak so the assistant transcribes what I said.
- As a user, I want the assistant to speak its responses back to me.

> *Streaming responses (hearing audio before the full reply is generated) is
> deferred post-MVP — it adds real synthesis-pipeline complexity for a feature
> that isn't core to the learning goals. MVP speaks the full response once
> generated.*

### Conversation
- As a user, I want the assistant to remember what I said earlier in the same session.
- As a user, I want the assistant to ask a follow-up question if my request is ambiguous.
- As a user, I want the assistant to explain what it's about to do before doing anything irreversible (e.g. sending a message).

### Tool Use / Local Automation
- As a user, I want to say "open VS Code" and have it open.
- As a user, I want to say "search Google for X" and have a browser open with results.
- As a user, I want to create, read, or search local files by voice command.

### External Integrations
- As a user, I want to say "send a Telegram message to X" and have it sent.
- As a user, I want to ask "what's on my calendar today" and get a real answer from Google Calendar.
- As a user, I want to ask about the weather or recent news and get live data.

### Memory
- As a user, I want the assistant to remember notes and tasks across sessions, not just within one conversation.
- As a user, I want to ask "what did I ask you to remember about X" and get an accurate answer.

### Coding Helper
- As a user, I want to ask the assistant to explain a piece of code.
- As a user, I want to ask it to generate a small snippet or summarize documentation.

## 3. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | System shall convert spoken audio to text (STT) on push-to-talk |
| FR-2 | System shall convert text responses to spoken audio (TTS) |
| FR-3 | System shall maintain conversation context within a session |
| FR-4 | System shall support an LLM-driven tool-calling loop (decide tool → call → return result → continue) |
| FR-5 | System shall support at least these local tools: open app, open URL, create file, read file, search folder |
| FR-6 | System shall support at least 3 external API integrations (e.g. Telegram, GitHub, Google Calendar) |
| FR-7 | System shall persist conversation history, notes, and tasks in a local database |
| FR-8 | System shall retrieve relevant memory (preferences, notes, tasks) and inject it into context when relevant |
| FR-9 | System shall handle tool execution errors gracefully and report them back to the user in natural language |
| FR-10 | System shall support basic code-related Q&A without needing a tool call |

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Codebase should be understandable by the developer (you) without external docs after a 1-week break — this is the actual test of "simple enough" |
| NFR-2 | Single-user only; no auth/session-isolation complexity needed |
| NFR-3 | Should run entirely on local hardware (laptop/desktop), no cloud infra required except third-party APIs and the LLM API itself |
| NFR-4 | Voice response latency should feel conversational (rough target: first audio within ~2–3s of command end, not a hard SLA) |
| NFR-5 | All API credentials stored in local config/env files, never hardcoded |
| NFR-6 | Adding a new tool should require touching only one file/module, not the core loop (validates modular design) |
| NFR-7 | Failure in one integration (e.g. GitHub API down) must not crash the whole assistant |

## 5. MVP Scope

**In scope for MVP:**
- Push-to-talk voice in, voice out
- Single LLM conversation loop with tool-calling
- 5 local tools (open app/URL, create/read file, search folder)
- 2–3 external APIs (pick the ones you're most excited to learn — suggest starting with Telegram + GitHub, both have simple auth)
- Local SQLite-based memory (conversation log, notes, tasks)
- Basic coding-helper Q&A (no tool needed — just LLM reasoning)

**Explicitly out of scope for MVP (later phases):**
- Wake-word detection
- Browser automation beyond opening pages
- Google Calendar/Gmail (OAuth is heavier — good Phase 2 candidate)
- Multi-integration orchestration (e.g. "check my calendar and message me on Telegram if I'm free")
- Any UI beyond terminal/CLI output

## 6. Scope Trims (post-review)

- **No `Users` table.** Given NFR-2 (single-user, local-only, no auth), a
  Users table would be an unused stub. Memory/notes/tasks are scoped to
  "the one user" implicitly — no user_id foreign keys needed.
- **Streaming voice responses** moved out of MVP (see above) — full-response
  TTS is simpler and sufficient for a conversational feel at this scale.
- **API integration docs folded into `07_ToolArchitecture.md`** rather than a
  standalone `08_APIIntegrations.md` — with only 2 simple token-auth
  integrations, a dedicated doc was more structure than the content needed.
- **Backlog tracked via GitHub Issues**, not a `10_Backlog.md` file — avoids
  duplicating the "Future Ideas" section in `01_ProjectVision.md`, and gives
  real practice with GitHub's project tooling.

## 7. Open Questions to Resolve Before Coding

- Which 2–3 external APIs do you want to start with? (affects 08_APIIntegrations.md)
- Local-only LLM, hosted API (Anthropic/OpenAI), or both? (affects 03_TRD.md)
- OK with a terminal-based MVP, or do you want a minimal UI from day one?
