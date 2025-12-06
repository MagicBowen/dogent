"""Shared paths for Dogent workspace state."""

from __future__ import annotations

from pathlib import Path


DOGENT_DIR_NAME = ".dogent"


def ensure_dogent_dir(cwd: Path) -> Path:
    """Ensure the .dogent directory exists and return its path."""
    path = cwd / DOGENT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
