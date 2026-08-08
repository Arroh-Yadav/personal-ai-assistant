LESSONS LEARNED

1) Use generate_content() for tool-calling, not chats.create()
- Prefer client.models.generate_content(...) (GenerateContent API) when using native function/tool-calling with the google.genai SDK.
- chats.create() / chat.send_message() in the installed SDK + model combo produced MALFORMED_FUNCTION_CALL responses and failed to surface structured function_call output reliably.
- generate_content() is stateless but accepts typed tools/config and returns structured function_call parts; include full conversation history in the `contents` list each call.

2) Construct SDK-typed FunctionDeclaration / Tool objects
- Build genai.types.FunctionDeclaration and genai.types.Tool objects (or use genai.types.Schema for parameters) instead of passing raw dicts.
- The SDK expects typed objects (or specific json-schema wrappers) — passing plain dicts caused validation failures or the model to reject the function declarations.
- Two workable approaches: (a) parametersJsonSchema on FunctionDeclaration (pass raw JSON Schema), or (b) build genai.types.Schema objects and pass as parameters. Both were supported; choose parametersJsonSchema to keep registry schemas portable.

3) Model choice and quota considerations
- gemini-flash-latest is convenient but the free-tier RPD (requests-per-day) is very low (~20) and can exhaust quickly during development.
- gemini-3.1-flash-lite exposed in the account had greater headroom and worked reliably for tool-calling in tests; set as the default model in .env.example and DEFAULT_MODEL.

Notes
- The codebase now prefers generate_content() when tools are provided and falls back to chat-based flow for plain-text-only exchanges.
- Keep tool JSON Schemas in the registry as plain JSON Schema; convert to SDK types at the last moment when constructing FunctionDeclaration objects.
