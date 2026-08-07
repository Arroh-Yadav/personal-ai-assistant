# 06. Database Schema

## Overview

SQLite, single file (`data/assistant.db`). Four tables, no `Users` table
(single-user by design — see `02_PRD.md` scope trims). Every table exists to
back a specific requirement from the PRD's Memory user stories.

## Tables

### `conversations`

Stores every turn of every conversation, so the assistant can recall recent
context across sessions, not just within one.

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,       -- groups turns from one run of the app
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    tool_name TEXT,                 -- populated only when role = 'tool'
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_conversations_session ON conversations(session_id, created_at);
```

**Why `session_id` instead of just a timestamp order:** lets you later answer
"what did we talk about last Tuesday" distinctly from "what did we talk about
just now," without needing a separate sessions table for MVP.

**Why store `role = 'tool'` rows too:** this gives you a full audit trail of
what the assistant actually did (not just what it said) — genuinely useful
for debugging the agent loop, and it's realistic to how production systems
log agent behavior.

---

### `notes`

Free-form notes the user asks the assistant to remember.

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Deliberately minimal — no tags, no categories, no folders. If you find
yourself wanting to organize notes later, that's a good, well-scoped Phase 2
addition rather than upfront speculation.

---

### `tasks`

Simple to-dos the assistant can create, list, and mark done.

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    due_date TEXT,                  -- nullable, ISO date string
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
```

**Why `status` as a constrained string instead of a boolean `is_done`:**
costs nothing extra now, and leaves room to add `'in_progress'` or
`'cancelled'` later without a schema migration.

---

### `preferences`

Simple key-value store for things the assistant should just know about you
("I prefer metric units," "my timezone is IST").

```sql
CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Why key-value instead of fixed columns:** preferences are open-ended and
user-driven ("remember that I like X") — a fixed-column table would mean a
migration every time you want to remember a new kind of preference. A KV
table sidesteps that entirely, and it's a legitimately common real-world
pattern worth learning.

## What's Deliberately NOT Here

- **No `users` table** — single-user app, see PRD scope trims.
- **No foreign keys between tables** — notes/tasks/preferences aren't linked
  to specific conversations for MVP. If you later want "show me the
  conversation where I created this task," that's a good Phase 2 addition
  (add a nullable `conversation_id` FK to `tasks`/`notes` at that point).
- **No full-text search / embeddings table** — relevant memory retrieval for
  MVP can just be "last N conversation turns + all notes/tasks" (small data
  volumes for a single user). Vector search for smarter retrieval is
  already flagged as a Future Idea in the Vision doc — right place for it.

## How This Maps to Memory Retrieval (Architecture doc, section 4)

When the Conversation Loop retrieves memory before calling the LLM:

```
1. Query conversations WHERE session_id = current, ORDER BY created_at DESC LIMIT N
2. Query all rows from notes and tasks (small tables, just load them)
3. Query all rows from preferences
4. Format all of this into a compact context block prepended to the LLM call
```

Simple, no ranking or relevance scoring needed at this data scale — that
complexity only earns its place once you have hundreds of notes, which is a
real "future idea" trigger, not a day-one concern.
