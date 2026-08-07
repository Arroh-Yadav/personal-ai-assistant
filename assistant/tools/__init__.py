"""Tools subpackage.

Import tool modules here so decorators run and register tools on package import.
"""
# Ensure local tools are registered
from . import local_tools  # noqa: F401
# Other tool modules can be imported similarly when implemented
from . import browser_tools, telegram_tool, github_tool  # noqa: F401
