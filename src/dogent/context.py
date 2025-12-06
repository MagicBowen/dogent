"""Context loading for @file references and completions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


REFERENCE_PATTERN = re.compile(r"@([\w\-/\.\d]+)")


@dataclass
class Reference:
    path: str
    content: str


def list_reference_candidates(cwd: Path, max_files: int = 200) -> List[str]:
    """List relative file paths for completion within the workspace."""
    candidates: List[str] = []
    for path in cwd.rglob("*"):
        if len(candidates) >= max_files:
            break
        if path.is_file():
            rel = path.relative_to(cwd)
            # skip virtual envs/builds/git
            if any(
                part.startswith(".venv")
                or part in {"dist", "build", "__pycache__", ".git"}
                for part in rel.parts
            ):
                continue
            candidates.append(str(rel))
    return candidates


def resolve_references(text: str, cwd: Path, size_limit: int = 32_000) -> List[Reference]:
    """Resolve @file references to content with a safety size cap."""
    refs: List[Reference] = []
    for match in REFERENCE_PATTERN.finditer(text):
        rel = match.group(1)
        path = cwd / rel
        if not path.exists() or not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if len(content) > size_limit:
            content = content[:size_limit] + "\n...[truncated]..."
        refs.append(Reference(path=rel, content=content))
    return refs
