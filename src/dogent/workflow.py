"""High-level workflow helpers (lightweight scaffolding)."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .context import Reference
from .guidelines import Guidelines
from .todo import TodoManager


def prepare_context_summary(refs: List[Reference]) -> str:
    return "\n\n".join(f"{ref.path}:\n{ref.content}" for ref in refs)


def bootstrap_todo(todo: TodoManager) -> None:
    """Seed baseline steps if empty."""
    if todo.list():
        return
    todo.add("规划大纲与 todo")
    todo.add("研究资料并收集引用")
    todo.add("分节写作草稿")
    todo.add("验证事实与引用")
    todo.add("润色并输出最终稿")
