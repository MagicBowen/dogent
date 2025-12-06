"""Temporary memory scratchpad management."""

from __future__ import annotations

from pathlib import Path

MEMORY_FILENAME = ".memory.md"


def memory_path(cwd: Path) -> Path:
    return cwd / MEMORY_FILENAME


def append_memory(cwd: Path, text: str) -> Path:
    path = memory_path(cwd)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
    return path


def clear_memory(cwd: Path) -> None:
    path = memory_path(cwd)
    if path.exists():
        path.unlink()
