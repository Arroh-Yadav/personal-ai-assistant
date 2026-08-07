# 01. Project Vision

## Overview

A personal AI voice assistant — a "mini Jarvis" — built as a hands-on learning
project. It listens to spoken commands, reasons about them using an LLM, calls
tools to take real actions (opening apps, searching the web, managing files,
talking to APIs), speaks results back, and remembers useful context across
sessions.

This is a **single-user, local-first learning project**, not a commercial
product. The priority is understanding *how* modern AI assistants are built —
speech pipelines, tool-calling loops, memory systems, API integration — not
shipping something enterprise-grade.

## Learning Goals

These are the actual point of the project. Every architectural decision should
be judged against whether it helps you learn one of these:

- How LLM-based agents plan and call tools (the "agent loop")
- How to design a tool-calling / function-calling interface from scratch
- How speech-to-text and text-to-speech pipelines fit around an LLM
- How to integrate real third-party APIs (auth, rate limits, error handling)
- How to design a simple, sane backend architecture (not microservices)
- How to structure a memory/context system for a conversational agent
- How browser automation works and where it's appropriate vs. fragile
- How to structure a project so it's readable, debuggable, and portfolio-ready

## Product Goals (what it should DO)

- Hold natural, context-aware voice conversations
- Understand commands and decide when to call a tool vs. just respond
- Execute local actions (open apps, files, folders, VS Code, browser)
- Talk to a handful of real external APIs (Telegram, GitHub, Calendar, etc.)
- Remember conversation history, preferences, notes, and tasks
- Help with small coding tasks (explain code, generate snippets, summarize docs)

## Non-Goals (explicitly out of scope for MVP)

- Multi-user support / authentication systems
- High availability, horizontal scaling, or production infra
- Microservices, message queues, or event-driven architecture
- Full automation of arbitrary websites via browser scripting
- Mobile app or standalone hardware device
- Enterprise-grade security (this runs locally, for one user)

Explicitly naming non-goals matters as much as naming goals — it gives
permission to skip complexity later without second-guessing the decision.

## Future Ideas (parking lot, not MVP)

- Wake-word detection (instead of push-to-talk)
- Simple web or mobile UI as an alternative to voice
- Plugin-style tool system so new tools can be dropped in without touching core
- Local LLM option (for offline / privacy-focused mode)
- Long-term memory with embeddings/vector search instead of flat storage
- Scheduled/autonomous tasks (assistant acts without a live prompt)

## Success Criteria

By the end of this project you should be able to:

1. Speak a command and have the assistant correctly decide what tool to call
2. Point to your own code and explain *why* each architectural choice was made
3. Add a brand-new tool or API integration without restructuring the codebase
4. Show this project on GitHub as evidence of practical AI/backend skills
