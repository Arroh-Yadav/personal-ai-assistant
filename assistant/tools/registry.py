"""Tool registry with decorator-based registration and safe dispatch.

Implements register(), get_schemas(), and dispatch() per docs/07_ToolArchitecture.md.
"""
from typing import Callable, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        def decorator(fn: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "parameters": parameters,
                "handler": fn,
            }
            return fn
        return decorator

    def get_schemas(self):
        """Return list of tool schemas for Gemini (name, description, parameters)."""
        return [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}

        try:
            # Arguments may come as JSON strings for some SDKs; if so, attempt to parse
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    # leave as-is
                    pass

            # Call the handler with the arguments dict (expand)
            result = tool["handler"](**arguments)
            return {"status": "ok", "result": result}
        except TypeError as e:
            logger.exception('Invalid arguments for %s: %s', name, e)
            return {"error": f"Invalid arguments for {name}: {e}"}
        except Exception as e:
            logger.exception('%s failed: %s', name, e)
            return {"error": f"{name} failed: {e}"}


# Single registry instance to import from other modules
registry = ToolRegistry()
