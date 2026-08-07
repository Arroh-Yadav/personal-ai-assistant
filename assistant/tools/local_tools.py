"""Local utility tools: create_file and read_file implemented and registered."""
from .registry import registry
from typing import Dict, Any
import os


@registry.register(
    name="create_file",
    description="Create a new text file at the given path with the given content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to create"},
            "content": {"type": "string", "description": "Text content to write"}
        },
        "required": ["path", "content"]
    }
)
def create_file(path: str, content: str) -> Dict[str, Any]:
    # Ensure parent directories exist
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "ok", "path": path}


@registry.register(
    name="read_file",
    description="Read a text file and return its contents.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"}
        },
        "required": ["path"]
    }
)
def read_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    return {"status": "ok", "path": path, "content": data}

# Alias: sometimes the model suggests `write_file` instead of `create_file`.
@registry.register(
    name="write_file",
    description="Alias for create_file - write content to a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to create"},
            "content": {"type": "string", "description": "Text content to write"}
        },
        "required": ["path", "content"]
    }
)
def write_file(path: str, content: str) -> Dict[str, Any]:
    return create_file(path=path, content=content)
