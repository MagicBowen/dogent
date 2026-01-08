"""Dogent package initialization."""

from importlib.metadata import version

__all__ = [
    "agent",
    "cli",
    "config",
    "core",
    "features",
    "outline_edit",
    "prompts",
]

# Single source of truth comes from package metadata defined in pyproject.toml
__version__ = version("dogent")
