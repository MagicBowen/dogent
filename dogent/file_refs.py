from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass
class FileAttachment:
    path: Path
    content: str
    truncated: bool = False


class FileReferenceResolver:
    """Resolves @file references within user prompts."""

    def __init__(self, root: Path, size_limit: int = 15000) -> None:
        self.root = root
        self.size_limit = size_limit

    def extract(self, message: str) -> Tuple[str, List[FileAttachment]]:
        """Return message plus resolved file attachments."""
        tokens = self._extract_tokens(message)
        root_resolved = Path(os.path.realpath(self.root))
        attachments: List[FileAttachment] = []
        for token in tokens:
            resolved = Path(os.path.realpath(self.root / token))
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                continue
            if not resolved.exists() or not resolved.is_file():
                continue
            text = resolved.read_text(encoding="utf-8", errors="replace")
            truncated = False
            if len(text) > self.size_limit:
                truncated = True
                text = text[: self.size_limit] + "\n...[truncated]..."
            attachments.append(
                FileAttachment(
                    path=resolved.relative_to(root_resolved),
                    content=text,
                    truncated=truncated,
                )
            )
        return message, attachments

    def _extract_tokens(self, message: str) -> Iterable[str]:
        pattern = r"@([\w\./\-]+)"
        return set(re.findall(pattern, message))
