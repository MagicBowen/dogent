"""Citation tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class Citations:
    items: Set[str] = field(default_factory=set)

    def add(self, url: str) -> None:
        if url:
            self.items.add(url.strip())

    def render(self) -> str:
        if not self.items:
            return ""
        lines = ["\n## 参考资料"]
        for idx, url in enumerate(sorted(self.items), 1):
            lines.append(f"{idx}. {url}")
        return "\n".join(lines)
