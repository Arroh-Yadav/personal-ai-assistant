# 07. Tool Architecture

## 1. The Core Idea

A "tool" is just a Python function plus a description of itself that the LLM
can read. The LLM never calls Python directly — it outputs a structured
request ("call `create_file` with these arguments"), and your code is what
actually executes it. This separation is the entire safety/architecture
model: **the LLM proposes, your code decides whether and how to act.**

## 2. Tool Definition Format

Every tool has three parts:

```python
{
    "name": "create_file",
    "description": "Create a new text file at the given path with the given content.",
    "parameters": {              # JSON Schema — Gemini reads this to know how to call it
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to create"},
            "content": {"type": "string", "description": "Text content to write"}
        },
        "required": ["path", "content"]
    },
    "handler": create_file_fn    # the actual Python function that runs it
}
```

**Why JSON Schema for parameters:** it's what Gemini's function-calling API
expects natively, and writing schemas by hand (rather than auto-generating
them) forces you to think clearly about each tool's contract — genuinely
useful practice, not just boilerplate.

## 3. Registering Tools

Use a simple decorator-based registry — clean to read, and a good practical
use of Python decorators:

```python
# tools/registry.py
class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, description, parameters):
        def decorator(fn):
            self._tools[name] = {
                "name": name,
                "description": description,
                "parameters": parameters,
                "handler": fn,
            }
            return fn
        return decorator

    def get_schemas(self):
        """Returns the list Gemini needs to know what tools exist."""
        return [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in self._tools.values()
        ]

    def dispatch(self, name, arguments):
        ...  # see Execution Flow below

registry = ToolRegistry()
```

```python
# tools/local_tools.py
from .registry import registry

@registry.register(
    name="create_file",
    description="Create a new text file with given content.",
    parameters={...}
)
def create_file_fn(path: str, content: str) -> dict:
    with open(path, "w") as f:
        f.write(content)
    return {"status": "ok", "path": path}
```

**Why this earns its place (vs. just an if/elif chain):** adding a new tool
means writing a new function with a decorator in the right file — `loop.py`
and `registry.py` never change. This is NFR-6 made real.

## 4. Execution Flow (dispatch)

```python
def dispatch(self, name, arguments):
    tool = self._tools.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}

    try:
        # (optional) validate `arguments` against tool["parameters"] here
        result = tool["handler"](**arguments)
        return {"status": "ok", "result": result}
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}
```

This matches the Tool Execution Flow diagram in `04_SystemArchitecture.md`:
lookup → validate → execute → catch → always return something structured.
**Nothing a tool does should ever raise an uncaught exception up to the main
loop** — that's the one hard rule of this layer.

## 5. Returning Results to the LLM

Whatever `dispatch()` returns gets serialized (JSON) and appended to the
message list as a "tool result" message, then the loop calls Gemini again.
The model sees exactly what your code saw — including errors — so it can
explain failures back to the user in natural language ("I couldn't find that
file") instead of you hand-writing error messages for every case.

## 6. Local Tools (MVP set)

| Tool | What it does |
|---|---|
| `open_app` | Launches a named application (VS Code, Chrome, etc. via `subprocess`) |
| `open_url` | Opens a URL in the default browser |
| `create_file` | Writes a new file with given content |
| `read_file` | Returns a file's contents |
| `search_folder` | Lists/searches files in a directory matching a pattern |

**Note:** "Open VS Code," "Open YouTube," and "Launch Chrome" from the
original feature list are really just `open_app` / `open_url` with different
arguments — no need for a separate function per app. This is exactly the
kind of consolidation that keeps the tool count (and the LLM's tool-choice
decision) manageable.

## 7. Browser Tools (Playwright-based)

| Tool | What it does |
|---|---|
| `browser_open` | Opens a URL in a Playwright-controlled browser |
| `browser_fill_form` | Fills named form fields on the current page |
| `browser_click` | Clicks an element by selector/text |
| `browser_read_content` | Extracts visible text from the current page |

Kept deliberately narrow per the PRD — this demonstrates the concept, it
doesn't try to generically automate arbitrary sites.

## 8. External API Tools

### Telegram

| | |
|---|---|
| **Tool** | `telegram_send_message(chat_id, text)` |
| **Auth** | Bot token from [@BotFather](https://t.me/BotFather) |
| **Credential storage** | `TELEGRAM_BOT_TOKEN` in `.env` |
| **Rate limits** | ~30 messages/sec to different chats, ~1/sec to the same chat — a non-issue at personal-assistant scale |
| **Best practices** | Never hardcode the token; catch `telegram.error.TelegramError` specifically so failures surface as clean tool errors, not stack traces |

### GitHub

| | |
|---|---|
| **Tools** | `github_list_issues(repo)`, `github_create_issue(repo, title, body)` |
| **Auth** | Personal Access Token (fine-grained, scoped to only the repos you need) |
| **Credential storage** | `GITHUB_TOKEN` in `.env` |
| **Rate limits** | 5,000 requests/hour authenticated — effectively unlimited for personal use |
| **Best practices** | Use fine-grained tokens (not classic, all-repo tokens) so a leaked key has minimal blast radius; check `response.status_code` explicitly rather than assuming success |

**Adding a new API integration later (e.g. Weather) follows the exact same
shape:** one new file in `tools/`, one `.env` variable, one entry in this
table. Nothing else in the system needs to know it exists beyond the
registry.

## 9. Tool Selection: How the LLM Knows What's Available

At the start of every Conversation Loop call, `registry.get_schemas()` is
passed to the Gemini API alongside the messages. The model sees the full
list of available tools every turn and decides — based on the schema names
and descriptions — whether one applies. This is why clear, specific
`description` fields matter more than they might seem to: they're the only
information the model has to decide *when* to reach for a given tool.
