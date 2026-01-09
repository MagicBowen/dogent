"""Configuration package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .manager import ConfigManager, DogentSettings
    from .paths import DogentPaths

__all__ = ["ConfigManager", "DogentSettings", "DogentPaths"]


def __getattr__(name: str) -> Any:
    if name in {"ConfigManager", "DogentSettings"}:
        from .manager import ConfigManager, DogentSettings

        return {"ConfigManager": ConfigManager, "DogentSettings": DogentSettings}[name]
    if name == "DogentPaths":
        from .paths import DogentPaths

        return DogentPaths
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
