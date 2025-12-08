"""Dogent package initialization."""

from importlib.metadata import version

__all__ = [
    "cli",
    "agent",
    "config",
    "prompts",
    "todo",
    "file_refs",
    "history",
]

# Single source of truth comes from package metadata defined in pyproject.toml
__version__ = version("dogent")
