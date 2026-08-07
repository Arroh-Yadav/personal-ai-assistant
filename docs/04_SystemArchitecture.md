# 04. System Architecture

## 1. High-Level Architecture

A single long-running Python process, no servers or background daemons.
Everything lives in-process; SQLite is the only persistent store.

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Process                          │
│                                                                │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │  Audio   │───▶│ Conversation │───▶│  Tool Registry   │    │
│  │  I/O     │    │    Loop      │    │  (local + APIs)  │    │
│  │ (STT/TTS)│◀───│  (Gemini)    │◀───│                  │    │
│  └──────────┘    └──────┬───────┘    └────────┬─────────┘    │
│                         │                       │              │
│                         ▼                       ▼              │
│                  ┌─────────────┐      ┌──────────────────┐    │
│                  │   SQLite    │      │ External Services │    │
│                  │  (memory)   │      │ Telegram / GitHub │    │
│                  └─────────────┘      └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

Four modules, each independently testable:
1. **Audio I/O** — capture push-to-talk audio, run STT, run TTS on output
2. **Conversation Loop** — owns the LLM call + tool-calling cycle
3. **Tool Registry** — where local tools and API clients are registered and dispatched
4. **Memory (SQLite)** — reads/writes conversation history, notes, tasks

## 2. Request Flow (end-to-end, one turn)

```
1. User holds push-to-talk key, speaks
2. Audio I/O captures raw audio → faster-whisper transcribes → text
3. Conversation Loop:
   a. Load relevant memory (recent history + relevant notes/tasks)
   b. Build message list: [system prompt, memory context, history, new message]
   c. Call Gemini API with tool definitions attached
   d. Gemini responds with either:
        - plain text (no tool needed) → go to step 4
        - a tool_call request → go to Tool Execution Flow (below),
          then feed the tool result back to Gemini, repeat from (c)
          until Gemini returns plain text
4. Store the exchange (user msg + assistant reply) in SQLite
5. Audio I/O: edge-tts synthesizes the reply → played back to user
```

The loop in step 3 is the core "agent loop" — it can iterate multiple times
in a single turn if the model needs to chain several tool calls (e.g. "check
GitHub issues, then message me the summary on Telegram" = 2 tool calls before
a final text reply).

## 3. Tool Execution Flow

```
Conversation Loop receives tool_call(name, arguments) from Gemini
        │
        ▼
Tool Registry looks up "name" in its dict of registered tools
        │
   found?───No───▶ return error result: "unknown tool" → back to LLM
        │
       Yes
        │
        ▼
Validate arguments against the tool's expected schema
        │
   valid?───No───▶ return error result: "invalid arguments: ..." → back to LLM
        │
       Yes
        │
        ▼
Execute tool function (local action OR API call)
        │
   success?───No───▶ catch exception → return error result (never crash) → back to LLM
        │
       Yes
        │
        ▼
Return structured result → Conversation Loop feeds it back to Gemini
as a tool result message → Gemini continues reasoning
```

Key principle (from NFR-7): **a tool failure is data, not a crash.** Every
tool function returns either a result or a caught, structured error — the
conversation loop always gets something to hand back to the model.

## 4. AI Interaction Flow (what happens inside the "Conversation Loop" box)

```
                 ┌───────────────────────┐
                 │  New user message in   │
                 └───────────┬────────────┘
                             ▼
                 ┌───────────────────────┐
                 │ Retrieve memory: last  │
                 │ N turns + relevant     │
                 │ notes/tasks from SQLite│
                 └───────────┬────────────┘
                             ▼
                 ┌───────────────────────┐
                 │ Call Gemini API with:  │
                 │ - system prompt        │
                 │ - context/history      │
                 │ - tool definitions     │
                 └───────────┬────────────┘
                             ▼
                    ┌────────────────┐
                    │ Response type?  │
                    └───┬────────┬────┘
                  text  │        │  tool_call
                        ▼        ▼
              ┌─────────────┐  ┌─────────────────┐
              │ Return reply │  │ Run Tool Exec    │
              │ to user      │  │ Flow (section 3) │
              └─────────────┘  └────────┬─────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │ Append tool result│
                                 │ to messages, call  │
                                 │ Gemini again        │
                                 │ (loop back up)      │
                                 └──────────────────┘
```

This loop is exactly what makes it an "agent" rather than a chatbot: the
model can decide, mid-conversation, that it needs more information or needs
to take an action before it can answer — and the code just keeps feeding
results back until the model is satisfied it has a final answer.

## 5. Where State Lives

| State | Location | Lifetime |
|---|---|---|
| Current turn's messages | In-memory list | One conversation session |
| Conversation history | SQLite `conversations` table | Persistent |
| Notes / Tasks | SQLite `notes`, `tasks` tables | Persistent |
| API credentials | `.env` file, loaded via `python-dotenv` | Persistent, never in code |
| Tool registry | In-memory dict, built at startup | One process lifetime |

## 6. Error Handling Philosophy

- Tool errors → caught, returned as structured results, never crash the process (NFR-7)
- LLM API errors (429, timeouts) → retry with exponential backoff, then surface
  a spoken "I'm having trouble reaching the AI service right now" rather than
  a stack trace
- STT/TTS errors → log and skip that turn gracefully rather than crashing the
  whole session
