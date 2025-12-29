from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass
class FileAttachment:
    path: Path
    sheet: str | None = None
    kind: str | None = None
    vision: dict[str, object] | None = None


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
            path_token, sheet = self._split_token(token)
            resolved = Path(os.path.realpath(self.root / path_token))
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                continue
            if not resolved.exists() or not resolved.is_file():
                continue
            attachments.append(
                FileAttachment(
                    path=resolved.relative_to(root_resolved),
                    sheet=sheet,
                )
            )
        return message, attachments

    def _extract_tokens(self, message: str) -> Iterable[str]:
        pattern = r"@([^\s]+)"
        raw_tokens = set(re.findall(pattern, message))
        return {self._normalize_token(token) for token in raw_tokens if token}

    def _normalize_token(self, token: str) -> str:
        return token.rstrip(".,;:!?)]}")

    def _split_token(self, token: str) -> tuple[str, str | None]:
        if "#" not in token:
            return token, None
        path_part, sheet = token.split("#", 1)
        sheet = sheet.strip()
        return path_part, sheet or None
